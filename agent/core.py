import ipaddress
import json
import os
import re
import threading
from types import SimpleNamespace
from typing import Callable
from urllib.parse import urlparse

from dotenv import load_dotenv

from agent.providers import create_client
from memory.memory import MemoryStore
from tools.registry import TOOLS, TOOL_DEFINITIONS

load_dotenv()

# Routine desktop, browser, research, and media actions run directly. Keep the
# approval gate for commands that execute inside the configured project.
CONFIRMATION_TOOLS = {"run_project_check", "write_project_files"}
SENSITIVE_ACTION = re.compile(r"\b(buy|purchase|pay|checkout|transfer|delete|remove|send|submit|publish|post|unsubscribe|cancel subscription)\b", re.IGNORECASE)
SENSITIVE_FIELD = re.compile(r"password|passcode|secret|api.?key|token|credential|payment|card number|cvv|bank|routing|social security|\bssn\b", re.IGNORECASE)
BROWSER_TOOL_NAMES = {"browser_open", "browser_state", "browser_click", "browser_fill", "browser_press", "browser_close", "youtube_search", "youtube_play"}
BROWSER_TOOL_LOCK = threading.Lock()


def requires_approval(tool_name: str, arguments: dict) -> bool:
    if tool_name in CONFIRMATION_TOOLS:
        return True
    if tool_name == "browser_click":
        return bool(SENSITIVE_ACTION.search(str(arguments.get("target", ""))))
    if tool_name == "browser_fill":
        return bool(SENSITIVE_FIELD.search(str(arguments.get("field", ""))))
    if tool_name == "browser_press":
        return str(arguments.get("key", "")).lower() in {"ctrl+enter", "control+enter"}
    if tool_name == "browser_open":
        host = (urlparse(str(arguments.get("url", ""))).hostname or "").lower()
        try:
            is_private_ip = ipaddress.ip_address(host).is_private
        except ValueError:
            is_private_ip = False
        return is_private_ip or host == "localhost" or host.endswith((".localhost", ".local", ".internal")) or (host and "." not in host)
    return False

SYSTEM_PROMPT = """You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), the sophisticated, loyal, and highly capable artificial intelligence assistant inspired by Tony Stark's iconic AI.

Key Persona & Communication Guidelines:
1. Cadence & Tone: Speak with a refined, articulate British demeanor. Address the user respectfully as 'sir' (or by their preferred name/title if saved in memory). Maintain calm composure, effortless intelligence, and subtle dry wit.
2. Conciseness & Precision: Never be verbose, bureaucratic, or robotic. Deliver clear, crisp briefings. Do not narrate internal planning, function calling mechanics, raw JSON payloads, or task IDs.
3. System Diagnostics: When asked for a status or diagnostics report, summarize the CPU, memory, power/battery, storage, and uptime telemetry clearly, highlighting anything notable (e.g., 'All systems nominal, sir. Power levels at 51%, discharging on battery, approximately 50 minutes remaining. CPU load is calm at 12%.').
4. Action & Proactivity: When commanded to open applications, adjust system volume, control media, or search YouTube/web, execute immediately and confirm with poised efficiency ('Right away, sir.', 'Commencing playback now, sir.').
5. Visual Intelligence: When the user asks what is on screen or asks for help with an open window or code, utilize analyze_screen and summarize what you observe accurately.
6. Context & Continuity: Seamlessly maintain context across turns. Understand references like 'that', 'play it', 'pause it', 'mute that', and 'look at this'.
7. Safety: Ask for user confirmation only for high-risk actions (modifying sensitive project files or running internal test suites). Routine telemetry, volume/media adjustments, browser research, and app launches require no bureaucratic hesitation.

You are at the user's service. Excel in every task with supreme competence."""

TOOL_PROGRESS = {
    "get_system_diagnostics": "Running system diagnostics, sir…",
    "control_system": "Executing system command, sir…",
    "analyze_screen": "Scanning your display, sir…",
    "open_application": "Launching application, sir…",
    "web_search": "Querying global intelligence feeds, sir…",
    "youtube_search": "Searching media archives, sir…",
    "youtube_play": "Commencing audio playback, sir…",
    "browser_open": "Navigating to address, sir…",
    "browser_state": "Inspecting webpage data, sir…",
    "browser_click": "Interacting with page element, sir…",
    "browser_fill": "Entering requested data, sir…",
    "read_project_file": "Accessing project records, sir…",
    "search_project": "Searching project files, sir…",
    "write_project_files": "Updating project files, sir…",
    "run_project_check": "Executing project check, sir…",
}


class JarvisAgent:
    def __init__(self, approval_callback: Callable[[str, dict], bool] | None = None):
        self.provider = os.getenv("APOORVA_PROVIDER", "ollama").strip().lower()
        self.client, self.model = create_client(self.provider)
        self.approval_callback = approval_callback
        self._conversation_lock = threading.Lock()
        self.memory = MemoryStore(os.getenv("APOORVA_MEMORY_PATH", "memory/apoorva.sqlite3"))
        self.max_iterations = int(os.getenv("APOORVA_MAX_ITERATIONS", "12"))
        if not 1 <= self.max_iterations <= 40:
            raise ValueError("APOORVA_MAX_ITERATIONS must be between 1 and 40")

    def ask(
        self,
        user_input: str,
        on_token: Callable[[str], None] | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> str:
        # Concurrent execution: each thread runs its own reasoning loop sharing the same memory store
        return self._ask(user_input, on_token, on_status)

    def _ask(
        self,
        user_input: str,
        on_token: Callable[[str], None] | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> str:
        if not user_input.strip():
            raise ValueError("Request cannot be empty")
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        memories = self.memory.recent_memories()
        if memories:
            memory_context = "User-approved saved memories (local):\n" + "\n".join(f"- {fact}" for fact in memories)
            messages.append({"role": "system", "content": memory_context})
        messages.extend(self.memory.recent_messages(limit=12))
        messages.append({"role": "user", "content": user_input.strip()})

        for _ in range(self.max_iterations):
            # Universal streaming for ultra-low latency (TTFT < 400ms on Groq)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                parallel_tool_calls=False,
                stream=True,
                **({"extra_body": {"think": False}} if self.provider == "ollama" else {}),
            )

            content_parts = []
            call_parts = {}
            for chunk in response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    content_parts.append(delta.content)
                    if on_token:
                        on_token(delta.content)
                for partial in delta.tool_calls or []:
                    call = call_parts.setdefault(partial.index, {"id": "", "name": "", "arguments": ""})
                    if partial.id:
                        call["id"] = partial.id
                    if partial.function:
                        if partial.function.name:
                            call["name"] += partial.function.name
                        if partial.function.arguments:
                            call["arguments"] += partial.function.arguments

            content = "".join(content_parts)
            calls = [
                SimpleNamespace(
                    id=call["id"],
                    function=SimpleNamespace(name=call["name"], arguments=call["arguments"]),
                )
                for _, call in sorted(call_parts.items())
            ]

            if not calls:
                answer = content or "I could not produce a response."
                messages.append({"role": "assistant", "content": answer})
                self.memory.save_turn(user_input.strip(), answer)
                return answer


            assistant_calls = [{
                "id": c.id,
                "type": "function",
                "function": {"name": c.function.name, "arguments": c.function.arguments or "{}"},
            } for c in calls]
            messages.append({"role": "assistant", "content": content or None, "tool_calls": assistant_calls})
            for call in calls:
                name = call.function.name
                try:
                    args = json.loads(call.function.arguments or "{}")
                    if not isinstance(args, dict):
                        raise ValueError("Tool arguments must be a JSON object")
                    if name not in TOOLS:
                        result = {"success": False, "error": "Unknown tool"}
                    elif requires_approval(name, args) and not (self.approval_callback and self.approval_callback(name, args)):
                        result = {"success": False, "error": "User approval was not granted; action was not performed."}
                    else:
                        if on_status:
                            status = TOOL_PROGRESS.get(name)
                            if name == "open_application":
                                status = f"Opening {args.get('application', 'the app')}…"
                            elif name == "write_text":
                                status = f"Writing in {args.get('application', 'the app')}…"
                            if status:
                                on_status(status)
                        if name in BROWSER_TOOL_NAMES:
                            with BROWSER_TOOL_LOCK:
                                result = TOOLS[name](**args)
                        else:
                            result = TOOLS[name](**args)
                        if result is None:
                            result = {"success": True, "result": None}
                except Exception as exc:
                    result = {"success": False, "error": f"{type(exc).__name__}: {exc}"}
                content = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": content})
        raise RuntimeError(f"Agent reached its {self.max_iterations}-step limit before completing the request")


# Backward compatibility alias
ApoorvaAgent = JarvisAgent








