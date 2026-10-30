"""J.A.R.V.I.S. Command Terminal — Stark Industries Protocol.
Interactive AI console with real-time telemetry, British neural voice,
hands-free wake-word detection, and concurrent execution.
"""
from concurrent.futures import ThreadPoolExecutor
from itertools import count
from queue import Empty, Queue
import os
import threading
import time
import msvcrt

from agent.core import JarvisAgent
from audio import speech_to_text, text_to_speech
from audio.sound_effects import play_wake_chime, play_confirm_chime, play_standby_chime
from tools.diagnostics import get_system_diagnostics

# ANSI Color & Style Formatting
CYAN = "\033[96m"
BRIGHT_BLUE = "\033[94m"
GOLD = "\033[93m"
GREEN = "\033[92m"
RED = "\033[91m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


class ApprovalBroker:
    """Route sensitive action authorizations through the J.A.R.V.I.S. console."""

    def __init__(self, output_queue: Queue):
        self.output_queue = output_queue
        self.lock = threading.Lock()
        self.ids = count(1)
        self.requests = {}

    def __call__(self, tool_name: str, arguments: dict) -> bool:
        request_id = next(self.ids)
        event = threading.Event()
        request = {"event": event, "approved": False, "tool": tool_name, "arguments": arguments}
        with self.lock:
            self.requests[request_id] = request

        if tool_name == "write_project_files":
            files = arguments.get("files", [])
            paths = [str(item.get("path", "?")) for item in files if isinstance(item, dict)]
            names = ", ".join(paths[:6])
            if len(paths) > 6:
                names += f", and {len(paths) - 6} more"
            summary = f"modify {len(paths)} project file(s): {names}"
        elif tool_name == "run_project_check":
            summary = f"execute the '{arguments.get('check', 'system')}' check"
        elif tool_name == "browser_click":
            summary = f"click sensitive element '{arguments.get('target', '')}'"
        elif tool_name == "browser_fill":
            summary = f"enter sensitive data into '{arguments.get('field', '')}'"
        elif tool_name == "browser_open":
            summary = f"navigate to internal address '{arguments.get('url', '')}'"
        else:
            summary = f"authorize {tool_name.replace('_', ' ')}"

        self.output_queue.put(
            f"\n{GOLD}[AUTHORIZATION REQUIRED]{RESET} Sir, your permission is requested to {summary}.\n"
            f"Reply with: {CYAN}/approve {request_id} yes{RESET} or {RED}/approve {request_id} no{RESET}"
        )
        event.wait()
        with self.lock:
            self.requests.pop(request_id, None)
        return request["approved"]

    def resolve(self, request_id: int, approved: bool) -> bool:
        with self.lock:
            request = self.requests.get(request_id)
            if request is None:
                return False
            request["approved"] = approved
            request["event"].set()
            return True

    def pending(self) -> list[tuple[int, str]]:
        with self.lock:
            return [(request_id, request["tool"]) for request_id, request in self.requests.items()]

    def deny_all(self) -> None:
        with self.lock:
            for request in self.requests.values():
                request["approved"] = False
                request["event"].set()


def render_banner(diag: dict):
    """Render the Stark Industries J.A.R.V.I.S. holographic terminal HUD."""
    banner = f"""{CYAN}{BOLD}
      ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
      ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
      ██║███████║██████╔╝██║   ██║██║███████╗
 ██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
 ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
  ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝{RESET}
  {DIM}[ JUST A RATHER VERY INTELLIGENT SYSTEM ]{RESET}
  {BRIGHT_BLUE}STARK INDUSTRIES PROTOCOL — SYSTEM INITIALIZED{RESET}
"""
    print(banner)

    # Telemetry HUD Pill
    if diag.get("success"):
        cpu_load = diag["cpu"]["load_percent"]
        ram_used = diag["memory"]["used_gb"]
        ram_total = diag["memory"]["total_gb"]
        ram_pct = diag["memory"]["used_percent"]
        battery = diag["battery"]
        bat_str = f"{battery.get('percent', 0)}%" if battery.get("available") else "AC Power"
        if battery.get("power_plugged"):
            bat_str += " ⚡"

        hud = (
            f"┌{'─'*68}┐\n"
            f"│  {CYAN}CPU:{RESET} {cpu_load:>4}%  │  {CYAN}RAM:{RESET} {ram_used}G/{ram_total}G ({ram_pct}%)  │  "
            f"{CYAN}POWER:{RESET} {bat_str:<8}  │  {GREEN}STATUS: ONLINE{RESET}  │\n"
            f"└{'─'*68}┘"
        )
        print(hud)


def main():
    # Retrieve startup diagnostics
    initial_diag = get_system_diagnostics()
    render_banner(initial_diag)

    output_queue = Queue()
    approval_broker = ApprovalBroker(output_queue)

    try:
        agent = JarvisAgent(approval_callback=approval_broker)
    except Exception as exc:
        print(f"{RED}Configuration error: {exc}{RESET}")
        return

    tts_enabled = threading.Event()
    if os.getenv("APOORVA_TTS_ENABLED", "true").lower() in {"1", "true", "yes", "on"}:
        tts_enabled.set()

    voice_ready = text_to_speech.available()
    stt_ready = speech_to_text.available()

    print(f"\n{BOLD}Audio Systems:{RESET}")
    if voice_ready:
        print(f"  • Voice Synthesis: {GREEN}Active (British Neural Voice: en-GB-RyanNeural){RESET}")
    else:
        print(f"  • Voice Synthesis: {RED}Unavailable (Run: python -m audio.download_models){RESET}")

    if stt_ready:
        print(f"  • Speech Recognition: {GREEN}Active (Offline Transducer){RESET}")
    else:
        print(f"  • Speech Recognition: {RED}Unavailable{RESET}")

    print(f"\n{BOLD}Commands & Protocols:{RESET}")
    print(f"  {CYAN}/voice{RESET}      - Push-to-talk single command")
    print(f"  {CYAN}/wake{RESET}       - Toggle continuous hands-free wake word ('Jarvis...')")
    print(f"  {CYAN}/diag{RESET}       - Full Stark Industries hardware telemetry report")
    print(f"  {CYAN}/stop{RESET}       - Immediately silence audio playback")
    print(f"  {CYAN}/tasks{RESET}      - Display active background operations")
    print(f"  {CYAN}/tts on|off{RESET} - Enable or mute vocal responses")
    print(f"  {CYAN}exit{RESET}        - Shut down J.A.R.V.I.S.\n")

    # Wake up chime and greeting
    play_wake_chime()
    if tts_enabled.is_set() and voice_ready:
        threading.Thread(
            target=lambda: text_to_speech.speak("All systems online, sir. At your service.", enabled=tts_enabled),
            daemon=True,
        ).start()

    shutdown = threading.Event()
    voice_active = threading.Event()
    wake_active = threading.Event()
    tasks_lock = threading.Lock()
    tasks = {}
    task_ids = count(1)

    # Multi-worker thread pool: allows parallel execution of multiple tasks simultaneously
    max_workers = int(os.getenv("JARVIS_WORKERS", "4"))
    executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="jarvis-worker")

    # Speech Queue for thread-safe sequential vocal output across concurrent tasks
    speech_queue = Queue()

    def speech_dispatcher():
        while not shutdown.is_set():
            try:
                task_id, spoken_text = speech_queue.get(timeout=0.1)
            except Empty:
                continue
            if shutdown.is_set():
                break
            if tts_enabled.is_set() and voice_ready and not voice_active.is_set():
                with tasks_lock:
                    if task_id in tasks:
                        tasks[task_id]["status"] = "speaking"
                try:
                    with tasks_lock:
                        concurrent_count = sum(1 for t in tasks.values() if t.get("status") in {"executing", "speaking"})
                    # If multiple tasks are active, state which task is being reported
                    prefix = f"Regarding task {task_id}: " if concurrent_count > 1 else ""
                    text_to_speech.speak(f"{prefix}{spoken_text}", enabled=tts_enabled)
                except Exception as exc:
                    print_safe(f"[TTS Error] {type(exc).__name__}: {exc}")
                finally:
                    with tasks_lock:
                        if task_id in tasks and tasks[task_id]["status"] == "speaking":
                            tasks[task_id]["status"] = "done"

    threading.Thread(target=speech_dispatcher, daemon=True, name="jarvis-speech-dispatcher").start()

    def print_safe(*args, **kwargs):
        output_queue.put(" ".join(str(arg) for arg in args))

    def run_task(task_id: int, request: str):
        start_time = time.time()
        with tasks_lock:
            tasks[task_id]["status"] = "executing"
            tasks[task_id]["start_time"] = start_time

        progress_timer = threading.Timer(
            2.0, lambda: print_safe(f"{CYAN}J.A.R.V.I.S. (Task {task_id}): Working on it, sir…{RESET}")
        )
        progress_timer.daemon = True
        progress_timer.start()

        def show_progress(message: str):
            progress_timer.cancel()
            print_safe(f"{CYAN}J.A.R.V.I.S. (Task {task_id}): {message}{RESET}")

        try:
            answer = agent.ask(request, on_status=show_progress)
            elapsed = round(time.time() - start_time, 2)
            if shutdown.is_set():
                return None
            play_confirm_chime()
            print_safe(f"\n{CYAN}{BOLD}[Task {task_id} Completed in {elapsed}s] J.A.R.V.I.S.:{RESET} {answer}")

            # Non-blocking enqueue to vocal playback queue
            if tts_enabled.is_set() and not shutdown.is_set() and voice_ready:
                speech_queue.put((task_id, answer))
            return answer
        except Exception as exc:
            print_safe(f"\n{RED}[J.A.R.V.I.S. Error on task {task_id}]{RESET} {type(exc).__name__}: {exc}")
            return None
        finally:
            progress_timer.cancel()
            with tasks_lock:
                tasks[task_id]["status"] = "done"
                tasks[task_id]["elapsed"] = round(time.time() - start_time, 2)

    def submit_task(request: str):
        request = request.strip()
        if not request:
            return
        with tasks_lock:
            unfinished = sum(t["status"] != "done" for t in tasks.values())
            if unfinished >= 20:
                print_safe(f"{GOLD}J.A.R.V.I.S.: Task buffer full (20 active). Review /tasks for status, sir.{RESET}")
                return
            task_id = next(task_ids)
            tasks[task_id] = {"request": request, "status": "queued", "start_time": time.time()}
        play_confirm_chime()
        print_safe(f"{CYAN}J.A.R.V.I.S.: Task {task_id} initiated, sir.{RESET}")
        executor.submit(run_task, task_id, request)


    def capture_push_to_talk():
        restore_tts = tts_enabled.is_set()
        tts_enabled.clear()
        try:
            play_wake_chime()
            print_safe(f"\n{GREEN}[Listening] Speak your command, sir...{RESET}")
            recognized = speech_to_text.listen_once()
            print_safe(f"{GOLD}You (voice):{RESET} {recognized}")
            voice_active.clear()
            if restore_tts:
                tts_enabled.set()
            submit_task(recognized)
        except Exception as exc:
            print_safe(f"\n[Voice Input Notice] {exc}")
        finally:
            if restore_tts:
                tts_enabled.set()
            voice_active.clear()

    def continuous_wake_loop():
        """Hands-free background listener for 'Jarvis' wake phrase."""
        while wake_active.is_set() and not shutdown.is_set():
            if voice_active.is_set():
                time.sleep(0.5)
                continue
            try:
                detected, command = speech_to_text.detect_wake_word_and_command()
                if detected and wake_active.is_set() and not shutdown.is_set():
                    text_to_speech.stop()
                    play_wake_chime()
                    if command:
                        print_safe(f"\n{GOLD}You (wake command):{RESET} Jarvis {command}")
                        submit_task(command)
                    else:
                        print_safe(f"\n{CYAN}J.A.R.V.I.S.: At your service, sir.{RESET}")
                        if tts_enabled.is_set() and voice_ready:
                            text_to_speech.speak("At your service, sir.", enabled=tts_enabled)
                        # Listen for follow-up command
                        try:
                            recognized = speech_to_text.listen_once(timeout_seconds=10)
                            if recognized:
                                print_safe(f"{GOLD}You (voice):{RESET} {recognized}")
                                submit_task(recognized)
                        except Exception:
                            pass
            except Exception:
                time.sleep(0.5)

    line_buffer = ""
    print(f"\n{GOLD}You:{RESET} ", end="", flush=True)

    try:
        while not shutdown.is_set():
            # Flush queued messages to console
            while True:
                try:
                    message = output_queue.get_nowait()
                except Empty:
                    break
                print("\r\033[2K" + message, flush=True)
                print(f"{GOLD}You:{RESET} " + line_buffer, end="", flush=True)

            if not msvcrt.kbhit():
                time.sleep(0.02)
                continue

            char = msvcrt.getwch()
            if char in {"\x00", "\xe0"}:
                msvcrt.getwch()
                continue
            if char == "\x03":  # Ctrl+C
                shutdown.set()
                break
            if char in {"\r", "\n"}:
                user_input = line_buffer.strip()
                line_buffer = ""
                print()
                command = user_input.lower()
            elif char == "\b":
                if line_buffer:
                    line_buffer = line_buffer[:-1]
                    print("\b \b", end="", flush=True)
                continue
            else:
                line_buffer += char
                print(char, end="", flush=True)
                continue

            if command in {"exit", "quit", "shutdown"}:
                shutdown.set()
                break

            if command == "/stop":
                while not speech_queue.empty():
                    try:
                        speech_queue.get_nowait()
                    except Empty:
                        break
                text_to_speech.stop()
                print_safe(f"{CYAN}J.A.R.V.I.S.: Audio output silenced and speech queue cleared, sir.{RESET}")
                continue


            if command == "/tts off":
                tts_enabled.clear()
                text_to_speech.stop()
                print_safe(f"{CYAN}J.A.R.V.I.S.: Vocalization muted, sir.{RESET}")
                continue

            if command == "/tts on":
                if voice_ready:
                    tts_enabled.set()
                    print_safe(f"{CYAN}J.A.R.V.I.S.: Vocalization active, sir.{RESET}")
                    text_to_speech.speak("Voice output enabled, sir.", enabled=tts_enabled)
                else:
                    print_safe(f"{RED}Voice models not found. Run: python -m audio.download_models{RESET}")
                continue

            if command in {"/wake", "/wake on", "/handsfree"}:
                if not stt_ready:
                    print_safe(f"{RED}Speech recognition models required for hands-free mode.{RESET}")
                    continue
                if wake_active.is_set():
                    wake_active.clear()
                    play_standby_chime()
                    print_safe(f"{GOLD}J.A.R.V.I.S.: Hands-free wake mode deactivated. Standby mode.{RESET}")
                else:
                    wake_active.set()
                    play_wake_chime()
                    threading.Thread(target=continuous_wake_loop, daemon=True, name="jarvis-wake").start()
                    print_safe(f"{GREEN}J.A.R.V.I.S.: Hands-free wake detection online. Say 'Jarvis' anytime, sir.{RESET}")
                continue

            if command in {"/wake off", "stand down"}:
                wake_active.clear()
                play_standby_chime()
                print_safe(f"{GOLD}J.A.R.V.I.S.: Hands-free wake mode deactivated.{RESET}")
                continue

            if command == "/diag":
                diag = get_system_diagnostics()
                if diag.get("success"):
                    cpu = diag["cpu"]
                    mem = diag["memory"]
                    bat = diag["battery"]
                    sys_info = diag["system"]
                    report = (
                        f"\n{CYAN}{BOLD}=== STARK INDUSTRIES SYSTEM TELEMETRY ==={RESET}\n"
                        f"  • CPU Load: {cpu['load_percent']}% ({cpu['physical_cores']} Cores / {cpu['logical_cores']} Threads @ {cpu.get('frequency_ghz', '?')} GHz)\n"
                        f"  • Memory: {mem['used_gb']} GB / {mem['total_gb']} GB ({mem['used_percent']}% used)\n"
                        f"  • Battery: {bat.get('percent', '?')}% ({bat.get('status', 'AC')}, Remaining: {bat.get('time_remaining', 'N/A')})\n"
                        f"  • Primary Storage: {diag['storage'].get('free_gb', '?')} GB free of {diag['storage'].get('total_gb', '?')} GB\n"
                        f"  • Host / OS: {sys_info['hostname']} ({sys_info['os']})\n"
                        f"  • System Uptime: {sys_info['uptime']}\n"
                        f"{CYAN}=========================================={RESET}"
                    )
                    print_safe(report)
                    if tts_enabled.is_set() and voice_ready:
                        speech_summary = f"All systems nominal, sir. CPU load at {cpu['load_percent']}%, memory usage at {mem['used_percent']}%. Power levels at {bat.get('percent', '100')}%."
                        text_to_speech.speak(speech_summary, enabled=tts_enabled)
                continue

            if command == "/tasks":
                with tasks_lock:
                    current = [
                        (
                            task_id,
                            task["status"],
                            task.get("elapsed") or round(time.time() - task.get("start_time", time.time()), 1),
                            task["request"],
                        )
                        for task_id, task in tasks.items()
                    ]
                if not current:
                    print_safe(f"{CYAN}J.A.R.V.I.S.: No active operations in the pipeline, sir.{RESET}")
                else:
                    print_safe(f"\n{CYAN}{BOLD}=== ACTIVE STARK INDUSTRIES PROTOCOLS ==={RESET}")
                    for task_id, status, dur, request in current[-15:]:
                        color = GREEN if status == "done" else (GOLD if status == "executing" else CYAN)
                        print_safe(f"  • Task {task_id:>2} [{color}{status.upper():<9}{RESET}] ({dur:>4}s): {request[:65]}")
                    print_safe(f"{CYAN}=========================================={RESET}")
                continue


            if command.startswith("/approve "):
                parts = command.split()
                if len(parts) != 3 or parts[2] not in {"yes", "no"}:
                    print_safe("Format: /approve ID yes  or  /approve ID no")
                    continue
                try:
                    request_id = int(parts[1])
                except ValueError:
                    print_safe("Approval ID must be numeric.")
                    continue
                if approval_broker.resolve(request_id, parts[2] == "yes"):
                    print_safe(f"{GREEN}Authorization for task {request_id} recorded: {parts[2].upper()}.{RESET}")
                else:
                    print_safe(f"{RED}No pending request found with ID {request_id}.{RESET}")
                continue

            if command == "/voice":
                text_to_speech.stop()
                if not stt_ready:
                    print_safe(f"{RED}Voice input models are not installed. Run: python -m audio.download_models{RESET}")
                elif voice_active.is_set():
                    print_safe(f"{GOLD}J.A.R.V.I.S.: Microphone is already active, sir.{RESET}")
                else:
                    voice_active.set()
                    threading.Thread(target=capture_push_to_talk, name="jarvis-voice", daemon=True).start()
                continue

            if not user_input:
                continue

            # Any incoming manual command interrupts current speech playback
            text_to_speech.stop()
            submit_task(user_input)

    except KeyboardInterrupt:
        shutdown.set()
    finally:
        shutdown.set()
        wake_active.clear()
        tts_enabled.clear()
        approval_broker.deny_all()
        text_to_speech.stop()
        play_standby_chime()
        executor.shutdown(wait=False, cancel_futures=True)
        print(f"\n{CYAN}J.A.R.V.I.S.: Powering down. Have a pleasant day, sir.{RESET}")


if __name__ == "__main__":
    main()
