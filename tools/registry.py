from tools.system import (
    get_current_time,
    get_current_date,
    open_application,
)

from tools.computer import (
    get_application_state,
    focus_application,
    write_text,
)

from tools.browser import (
    browser_open,
    browser_state,
    browser_click,
    browser_fill,
    browser_press,
    browser_close,
)

# =========================================================
# TOOL HANDLERS
# =========================================================

TOOLS = {
    "get_current_time": get_current_time,
    "get_current_date": get_current_date,
    "open_application": open_application,

    "get_application_state": get_application_state,
    "focus_application": focus_application,
    "write_text": write_text,

    "browser_open": browser_open,
    "browser_state": browser_state,
    "browser_click": browser_click,
    "browser_fill": browser_fill,
    "browser_press": browser_press,
    "browser_close": browser_close,
}


# =========================================================
# ACTION TOOLS
# =========================================================

ACTION_TOOLS = {
    "open_application",
    "focus_application",
    "write_text",
}


# =========================================================
# TOOL DEFINITIONS
# =========================================================

TOOL_DEFINITIONS = [

    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current local time.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "get_current_date",
            "description": "Get today's current local date.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": (
                "Open a supported Windows application."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "application": {
                        "type": "string",
                        "description": (
                            "Application to open."
                        ),
                    },
                },
                "required": ["application"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "get_application_state",
            "description": (
                "Check whether a Windows application is "
                "currently open and visible."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "application": {
                        "type": "string",
                        "description": (
                            "Application to inspect."
                        ),
                    },
                },
                "required": ["application"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "focus_application",
            "description": (
                "Bring an already-open Windows application "
                "to the foreground."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "application": {
                        "type": "string",
                        "description": (
                            "Application to focus."
                        ),
                    },
                },
                "required": ["application"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "write_text",
            "description": (
                "Write exact text into an already-open application. "
                "For programming tasks, generate the complete code and "
                "pass the entire program in the text argument."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "application": {
                        "type": "string",
                        "description": (
                            "Application containing the editor."
                        ),
                    },
                    "text": {
                        "type": "string",
                        "description": (
                            "Exact text that should be written."
                        ),
                    },
                },
                "required": [
                    "application",
                    "text",
                ],
            },
        },
    },
    {
    "type": "function",
    "function": {
        "name": "browser_open",
        "description": (
            "Open a URL in Apoorva's controlled browser."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to open.",
                },
            },
            "required": ["url"],
        },
    },
},

{
    "type": "function",
    "function": {
        "name": "browser_state",
        "description": (
            "Read the current browser page URL, title, "
            "and visible text."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
},

{
    "type": "function",
    "function": {
        "name": "browser_click",
        "description": (
            "Click a visible webpage element using its "
            "user-visible text."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": (
                        "Visible text of the element "
                        "to click."
                    ),
                },
            },
            "required": ["target"],
        },
    },
},

{
    "type": "function",
    "function": {
        "name": "browser_fill",
        "description": (
            "Fill a webpage input field using its "
            "visible label or placeholder."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "field": {
                    "type": "string",
                    "description": (
                        "Visible field label or placeholder."
                    ),
                },
                "value": {
                    "type": "string",
                    "description": (
                        "Value to enter."
                    ),
                },
            },
            "required": [
                "field",
                "value",
            ],
        },
    },
},

{
    "type": "function",
    "function": {
        "name": "browser_press",
        "description": (
            "Press a keyboard key in the current browser page."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": (
                        "Keyboard key such as Enter, Tab, "
                        "Escape, or ArrowDown."
                    ),
                },
            },
            "required": ["key"],
        },
    },
},

{
    "type": "function",
    "function": {
        "name": "browser_close",
        "description": (
            "Close Apoorva's controlled browser."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
},

]
from tools.project import list_project_files, read_project_file, search_project, write_project_files, run_project_check
from memory.memory import MemoryStore
import os

def _memory():
    return MemoryStore(os.getenv("APOORVA_MEMORY_PATH", "memory/apoorva.sqlite3"))

# Register tool handlers and provider-compatible JSON schemas.
TOOLS.update({
    "list_project_files": list_project_files,
    "read_project_file": read_project_file,
    "search_project": search_project,
    "write_project_files": write_project_files,
    "run_project_check": run_project_check,
    "list_tasks": lambda status="open": _memory().list_tasks(status),
    "create_task": lambda title, due_date=None: _memory().create_task(title, due_date),
    "complete_task": lambda task_id: _memory().complete_task(task_id),
    "remember_fact": lambda fact: _memory().remember_fact(fact),
    "list_memories": lambda limit=30: _memory().list_memories(limit),
    "forget_memory": lambda memory_id: _memory().forget_memory(memory_id),
})

for _name, _description, _properties, _required in [
    ("list_project_files", "List bounded, non-hidden files in the configured project workspace.", {"limit": {"type": "integer"}}, []),
    ("read_project_file", "Read a UTF-8 text file inside the configured project workspace (maximum 200 KB).", {"path": {"type": "string"}}, ["path"]),
    ("search_project", "Search project text files using a regular expression.", {"pattern": {"type": "string"}, "limit": {"type": "integer"}}, ["pattern"]),
    ("write_project_files", "Create or update a batch of text files inside the configured project workspace. Requires user approval. Do not overwrite existing files unless the user requested edits.", {"files": {"type": "array", "items": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"], "additionalProperties": False}}, "overwrite": {"type": "boolean"}}, ["files"]),
    ("run_project_check", "Run one allowlisted project check. Requires user approval.", {"check": {"type": "string", "enum": ["pytest", "unittest", "ruff"]}, "timeout_seconds": {"type": "integer"}}, ["check"]),
    ("list_tasks", "List personal tasks stored locally.", {"status": {"type": "string", "enum": ["open", "done", "all"]}}, []),
    ("create_task", "Create a task in the local personal task list.", {"title": {"type": "string"}, "due_date": {"type": "string", "description": "Optional date in YYYY-MM-DD format"}}, ["title"]),
    ("complete_task", "Mark a local task complete by its id.", {"task_id": {"type": "integer"}}, ["task_id"]),
    ("remember_fact", "Save a useful personal preference or fact locally when the user explicitly asks Apoorva to remember it. Never save passwords, API keys, or secrets.", {"fact": {"type": "string", "maxLength": 1000}}, ["fact"]),
    ("list_memories", "List facts the user explicitly asked Apoorva to remember.", {"limit": {"type": "integer", "minimum": 1, "maximum": 100}}, []),
    ("forget_memory", "Delete a saved memory by its memory id.", {"memory_id": {"type": "integer", "minimum": 1}}, ["memory_id"]),
]:
    TOOL_DEFINITIONS.append({"type": "function", "function": {"name": _name, "description": _description, "parameters": {"type": "object", "properties": _properties, "required": _required}}})



from tools.research import web_search
from tools.browser import youtube_search, youtube_play
from tools.diagnostics import get_system_diagnostics
from tools.system import control_system
from vision.vision import analyze_screen

TOOLS.update({
    "web_search": web_search,
    "youtube_search": youtube_search,
    "youtube_play": youtube_play,
    "get_system_diagnostics": get_system_diagnostics,
    "control_system": control_system,
    "analyze_screen": analyze_screen,
})

TOOL_DEFINITIONS.extend([
    {"type": "function", "function": {"name": "web_search", "description": "Search public web results. Returns titles, URLs, and snippets; verify claims against pages before relying on snippets.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "max_results": {"type": "integer", "minimum": 1, "maximum": 8}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "youtube_search", "description": "Search YouTube for videos matching the user's music or video request. Opens the controlled browser without asking approval.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 8}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "youtube_play", "description": "Play a matching YouTube result when the user asks for music or a video. Use the best matching URL from youtube_search; do not ask the user to choose unless the request is ambiguous. No approval is needed for playback.", "parameters": {"type": "object", "properties": {"video_url": {"type": "string"}}, "required": ["video_url"]}}},
    {"type": "function", "function": {"name": "get_system_diagnostics", "description": "Retrieve comprehensive real-time Stark Industries telemetry: CPU load and frequency, RAM usage, battery percentage and charging time, disk space, network hostname, IP, and system uptime.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "control_system", "description": "Execute hardware and system commands: volume_up, volume_down, mute, unmute, play_pause, next_track, prev_track, stop_media, or lock_workstation.", "parameters": {"type": "object", "properties": {"action": {"type": "string", "enum": ["volume_up", "volume_down", "mute", "unmute", "play_pause", "next_track", "prev_track", "stop_media", "lock_workstation"], "description": "Action to perform"}, "value": {"type": "integer", "description": "Optional step value for volume adjustment"}}, "required": ["action"]}}},
    {"type": "function", "function": {"name": "analyze_screen", "description": "Capture the user's screen display and perform visual analysis. Use when the user asks what is on screen, to inspect an open application, diagnose an error message, or view code or an image.", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Specific question or focus area for visual analysis"}}, "required": []}}},
])

