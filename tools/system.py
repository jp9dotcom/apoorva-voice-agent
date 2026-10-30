"""System control and application launcher for J.A.R.V.I.S."""
import ctypes
import os
import shutil
import subprocess
from datetime import datetime
import pyautogui


# =========================================================
# SYSTEM INFORMATION
# =========================================================

def get_current_time():
    """Return the current local time."""
    return {
        "success": True,
        "time": datetime.now().strftime("%I:%M:%S %p"),
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }


def get_current_date():
    """Return today's local date."""
    return {
        "success": True,
        "date": datetime.now().strftime("%A, %d %B %Y"),
    }


# =========================================================
# UNIVERSAL APPLICATION LAUNCHER
# =========================================================

COMMON_APP_MAP = {
    # Text / Editors
    "notepad": "notepad.exe",
    "wordpad": "write.exe",
    "vs code": "code",
    "vscode": "code",
    "code": "code",
    "visual studio code": "code",
    "sublime": "subl",
    "pycharm": "pycharm",

    # Utilities
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "settings": "start ms-settings:",
    "control panel": "control.exe",

    # Terminals
    "command prompt": "cmd.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "terminal": "wt.exe",
    "windows terminal": "wt.exe",

    # Browsers
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "firefox": "firefox.exe",
    "brave": "brave.exe",

    # Media & Social
    "spotify": "start spotify:",
    "discord": "discord",
    "slack": "slack",
    "teams": "teams",
    "steam": "steam",
}


def open_application(application: str) -> dict:
    """
    Open any Windows application, protocol, or path.
    Recognizes common names (Spotify, VS Code, Chrome, Terminal, etc.)
    and dynamically resolves other installed software or system commands.
    """
    app_query = application.strip()
    normalized = app_query.lower()

    # Check common mapped applications
    target = COMMON_APP_MAP.get(normalized)
    if target:
        try:
            if target.startswith("start "):
                subprocess.Popen(target, shell=True)
            else:
                # If command exists on PATH or direct executable
                subprocess.Popen(target, shell=True)
            return {
                "success": True,
                "application": app_query,
                "message": f"Successfully launched {app_query}, sir.",
            }
        except Exception as exc:
            pass

    # Dynamic resolution: try os.startfile or shell start
    try:
        # Check if direct executable or registered application
        os.startfile(app_query)
        return {
            "success": True,
            "application": app_query,
            "message": f"Initiated {app_query}, sir.",
        }
    except Exception:
        pass

    try:
        # Fallback to Windows shell launcher
        subprocess.Popen(f'start "" "{app_query}"', shell=True)
        return {
            "success": True,
            "application": app_query,
            "message": f"Dispatched launch command for {app_query}, sir.",
        }
    except Exception as exc:
        return {
            "success": False,
            "application": app_query,
            "error": f"Unable to locate or launch '{app_query}': {str(exc)}",
        }


# =========================================================
# HARDWARE & MEDIA CONTROL
# =========================================================

def control_system(action: str, value: int | None = None) -> dict:
    """
    Execute hardware and OS control actions:
    - Volume: 'volume_up', 'volume_down', 'mute', 'unmute'
    - Media: 'play_pause', 'next_track', 'prev_track', 'stop_media'
    - Security: 'lock_workstation'
    """
    act = action.strip().lower()

    try:
        if act == "volume_up":
            # Press volume up key (steps up by 2%)
            steps = value if (value and 1 <= value <= 25) else 5
            for _ in range(steps):
                pyautogui.press("volumeup")
            return {"success": True, "action": act, "message": "Volume increased, sir."}

        elif act == "volume_down":
            steps = value if (value and 1 <= value <= 25) else 5
            for _ in range(steps):
                pyautogui.press("volumedown")
            return {"success": True, "action": act, "message": "Volume decreased, sir."}

        elif act in {"mute", "unmute", "toggle_mute"}:
            pyautogui.press("volumemute")
            return {"success": True, "action": act, "message": "Audio mute toggled, sir."}

        elif act in {"play_pause", "pause", "play", "toggle_playback"}:
            pyautogui.press("playpause")
            return {"success": True, "action": act, "message": "Media playback toggled, sir."}

        elif act in {"next_track", "next"}:
            pyautogui.press("nexttrack")
            return {"success": True, "action": act, "message": "Skipped to next track, sir."}

        elif act in {"prev_track", "previous", "previous_track"}:
            pyautogui.press("prevtrack")
            return {"success": True, "action": act, "message": "Reverting to previous track, sir."}

        elif act in {"stop_media", "stop"}:
            pyautogui.press("stop")
            return {"success": True, "action": act, "message": "Media stopped, sir."}

        elif act in {"lock", "lock_pc", "lock_workstation"}:
            # Immediately lock workstation
            ctypes.windll.user32.LockWorkStation()
            return {"success": True, "action": act, "message": "Workstation locked, sir."}

        else:
            return {
                "success": False,
                "error": f"Unknown action '{action}'. Supported: volume_up, volume_down, mute, play_pause, next_track, prev_track, lock_workstation",
            }
    except Exception as exc:
        return {"success": False, "error": str(exc)}