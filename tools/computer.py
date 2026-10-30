import time

import pyautogui

from pywinauto import Desktop


# =========================================================
# WINDOW SEARCH
# =========================================================

def _find_window(application: str):

    application = application.strip()

    desktop = Desktop(
        backend="uia"
    )

    windows = desktop.windows(
        visible_only=True
    )

    for window in windows:

        try:

            title = window.window_text()

            if not title:
                continue

            if application.lower() in title.lower():

                return window

        except Exception:
            continue

    return None


# =========================================================
# APPLICATION STATE
# =========================================================

def get_application_state(application: str):

    window = _find_window(
        application
    )

    if window is None:

        return {
            "success": True,
            "application": application,
            "open": False,
        }

    try:

        return {
            "success": True,
            "application": application,
            "open": True,
            "window_title": window.window_text(),
        }

    except Exception as exc:

        return {
            "success": False,
            "application": application,
            "error": str(exc),
        }


# =========================================================
# FOCUS APPLICATION
# =========================================================

def focus_application(application: str):

    window = _find_window(
        application
    )

    if window is None:

        return {
            "success": False,
            "application": application,
            "error": (
                f"Could not find open application "
                f"'{application}'."
            ),
        }

    try:

        window.set_focus()

        time.sleep(0.3)

        return {
            "success": True,
            "application": application,
            "window_title": window.window_text(),
            "message": (
                f"{application} is now focused."
            ),
        }

    except Exception as exc:

        return {
            "success": False,
            "application": application,
            "error": str(exc),
        }


# =========================================================
# WRITE TEXT
# =========================================================

def write_text(
    application: str,
    text: str,
):

    window = _find_window(
        application
    )

    if window is None:

        return {
            "success": False,
            "application": application,
            "error": (
                f"Could not find open application "
                f"'{application}'."
            ),
        }

    try:

        # ---------------------------------------------
        # FOCUS WINDOW
        # ---------------------------------------------

        window.set_focus()

        time.sleep(0.4)

        # ---------------------------------------------
        # TRY UI AUTOMATION FIRST
        # ---------------------------------------------

        edit_controls = window.descendants(
            control_type="Edit"
        )

        if edit_controls:

            editor = edit_controls[0]

            try:

                editor.set_focus()

                editor.set_edit_text(
                    text
                )

                return {
                    "success": True,
                    "application": application,
                    "method": "ui_automation",
                    "message": (
                        f"Text was written into "
                        f"{application}."
                    ),
                }

            except Exception:
                pass

        # ---------------------------------------------
        # FALLBACK: KEYBOARD INPUT
        # ---------------------------------------------

        pyautogui.write(
            text,
            interval=0.002
        )

        return {
            "success": True,
            "application": application,
            "method": "pyautogui_fallback",
            "message": (
                f"Text was written into "
                f"{application}."
            ),
        }

    except Exception as exc:

        return {
            "success": False,
            "application": application,
            "error": str(exc),
        }