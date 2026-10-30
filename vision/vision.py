"""Visual intelligence and screen analysis for J.A.R.V.I.S."""
import base64
import io
import os
from pathlib import Path
from PIL import Image, ImageGrab
from openai import OpenAI


def capture_desktop_screenshot() -> bytes | None:
    """Capture a screenshot of the current active desktop display."""
    try:
        # Primary method: PIL ImageGrab
        screenshot = ImageGrab.grab()
    except Exception:
        try:
            # Fallback method: pyautogui
            import pyautogui
            screenshot = pyautogui.screenshot()
        except Exception:
            return None

    # Optimize resolution: max 1920x1080 to keep token footprint and latency optimal
    max_w, max_h = 1920, 1080
    if screenshot.width > max_w or screenshot.height > max_h:
        screenshot.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)

    # Encode to JPEG
    buffer = io.BytesIO()
    screenshot.convert("RGB").save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def analyze_screen(query: str = "Describe what is on screen and any relevant details or issues.") -> dict:
    """
    Capture the current desktop screen and analyze it with visual intelligence.
    Use when the user asks 'what's on my screen', 'take a look at this',
    'read this error', or asks a question about the active application.
    """
    image_bytes = capture_desktop_screenshot()
    if not image_bytes:
        return {
            "success": False,
            "error": "Unable to capture desktop display. Ensure the terminal is running in your active user desktop session.",
        }

    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{base64_image}"

    # Determine vision client & model
    # Priority: Gemini -> OpenRouter -> Groq
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()

    client = None
    model = os.getenv("APOORVA_VISION_MODEL", "").strip()

    if gemini_key:
        client = OpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=gemini_key,
            timeout=45.0,
        )
        if not model:
            model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    elif openrouter_key:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_key,
            timeout=45.0,
        )
        if not model:
            model = "qwen/qwen-2.5-vl-72b-instruct"
    elif groq_key:
        client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=groq_key,
            timeout=45.0,
        )
        if not model:
            model = "llama-3.2-11b-vision-preview"

    if client is None:
        return {
            "success": False,
            "error": "No visual-capable API key (GEMINI_API_KEY, OPENROUTER_API_KEY, or GROQ_API_KEY) found in .env.",
        }

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are J.A.R.V.I.S.'s visual perception engine. Analyze the screenshot accurately and concisely. Focus on the main windows, active code, error messages, or whatever the user requested. Address the user as 'sir'.",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": query},
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url, "detail": "high"},
                        },
                    ],
                },
            ],
            max_tokens=600,
        )
        analysis = response.choices[0].message.content or "No visual details could be parsed."
        return {
            "success": True,
            "analysis": analysis,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Visual analysis failed: {type(exc).__name__}: {str(exc)}",
        }
