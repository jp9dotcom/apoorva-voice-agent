from urllib.parse import quote_plus, urlparse

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


# =========================================================
# BROWSER MANAGER
# =========================================================

class BrowserManager:

    def __init__(self):

        self.playwright = None
        self.browser = None
        self.page = None

    # =====================================================
    # START BROWSER
    # =====================================================

    def start(self):

        if self.page is not None:

            return self.page

        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch(
            headless=False
        )

        self.page = self.browser.new_page()

        return self.page

    # =====================================================
    # CLOSE BROWSER
    # =====================================================

    def close(self):

        try:

            if self.browser:
                self.browser.close()

        finally:

            if self.playwright:
                self.playwright.stop()

            self.page = None
            self.browser = None
            self.playwright = None

    # =====================================================
    # OPEN URL
    # =====================================================

    def open_url(self, url: str):

        page = self.start()

        if not url.startswith(
            ("http://", "https://")
        ):

            url = "https://" + url

        try:

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000,
            )

            return {
                "success": True,
                "url": page.url,
                "title": page.title(),
            }

        except Exception as exc:

            return {
                "success": False,
                "error": str(exc),
                "url": page.url,
            }

    # =====================================================
    # GET CURRENT PAGE
    # =====================================================

    def get_page_state(self):

        if self.page is None:

            return {
                "success": False,
                "error": "Browser is not open.",
            }

        try:

            text = self.page.locator(
                "body"
            ).inner_text(
                timeout=10000
            )

            # Keep the context manageable.
            text = text[:12000]

            return {
                "success": True,
                "url": self.page.url,
                "title": self.page.title(),
                "text": text,
            }

        except Exception as exc:

            return {
                "success": False,
                "error": str(exc),
            }

    # =====================================================
    # CLICK
    # =====================================================

    def click(
        self,
        target: str,
    ):

        if self.page is None:

            return {
                "success": False,
                "error": "Browser is not open.",
            }

        try:

            # First prefer user-visible text.
            locator = self.page.get_by_text(
                target,
                exact=True,
            )

            if locator.count() == 0:

                locator = self.page.get_by_role(
                    "button",
                    name=target,
                )

            locator.first.click(
                timeout=10000
            )

            return {
                "success": True,
                "clicked": target,
                "url": self.page.url,
            }

        except PlaywrightTimeoutError:

            return {
                "success": False,
                "error": (
                    f"Could not find or click "
                    f"'{target}'."
                ),
            }

        except Exception as exc:

            return {
                "success": False,
                "error": str(exc),
            }

    # =====================================================
    # FILL INPUT
    # =====================================================

    def fill(
        self,
        field: str,
        value: str,
    ):

        if self.page is None:

            return {
                "success": False,
                "error": "Browser is not open.",
            }

        try:

            locator = self.page.get_by_label(
                field,
                exact=True,
            )

            if locator.count() == 0:

                locator = self.page.get_by_placeholder(
                    field,
                    exact=True,
                )

            if locator.count() == 0:

                return {
                    "success": False,
                    "error": (
                        f"Could not find input "
                        f"'{field}'."
                    ),
                }

            locator.first.fill(
                value
            )

            return {
                "success": True,
                "field": field,
            }

        except Exception as exc:

            return {
                "success": False,
                "error": str(exc),
            }

    # =====================================================
    # PRESS KEY
    # =====================================================

    def press(
        self,
        key: str,
    ):

        if self.page is None:

            return {
                "success": False,
                "error": "Browser is not open.",
            }

        try:

            self.page.keyboard.press(
                key
            )

            return {
                "success": True,
                "key": key,
            }

        except Exception as exc:

            return {
                "success": False,
                "error": str(exc),
            }


    def youtube_search(self, query: str, limit: int = 5):
        if not query.strip() or len(query) > 300 or not 1 <= limit <= 8:
            return {"success": False, "error": "Provide a 1–300 character query and limit from 1 to 8."}
        page = self.start()
        url = "https://www.youtube.com/results?search_query=" + quote_plus(query)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.locator("ytd-video-renderer a#video-title").first.wait_for(timeout=15000)
            results = page.locator("ytd-video-renderer a#video-title").evaluate_all(
                "els => els.slice(0, 8).map(a => ({title: (a.getAttribute('title') || a.innerText || '').trim(), url: a.href}))"
            )
            results = [r for r in results if r.get("title") and urlparse(r.get("url", "")).hostname in {"www.youtube.com", "youtube.com"}][:limit]
            return {"success": bool(results), "query": query, "results": results, "url": page.url,
                    "message": "Choose a result by title or URL. Nothing has been played yet."}
        except Exception as exc:
            return {"success": False, "error": f"Could not retrieve YouTube results: {type(exc).__name__}", "url": page.url}

    def youtube_play(self, video_url: str):
        parsed = urlparse(video_url)
        if parsed.scheme != "https" or parsed.hostname not in {"www.youtube.com", "youtube.com"} or parsed.path != "/watch" or not parsed.query:
            return {"success": False, "error": "Use a YouTube watch URL returned by youtube_search."}
        page = self.start()
        try:
            page.goto(video_url, wait_until="domcontentloaded", timeout=30000)
            video = page.locator("video.html5-main-video").first
            video.wait_for(state="attached", timeout=20000)
            button = page.locator("button.ytp-large-play-button")
            if button.count():
                try:
                    button.click(timeout=5000)
                except Exception:
                    video.evaluate("el => el.play()")
            else:
                video.evaluate("el => el.play()")
            page.wait_for_timeout(1200)
            state = video.evaluate("el => ({paused: el.paused, current_time: el.currentTime})")
            return {"success": not state["paused"], "url": page.url, "title": page.title(), **state,
                    "message": "Playback started." if not state["paused"] else "Video opened, but playback is paused or blocked by the site."}
        except Exception as exc:
            return {"success": False, "error": f"Could not start playback: {type(exc).__name__}", "url": page.url}

# =========================================================
# GLOBAL BROWSER INSTANCE
# =========================================================

_browser = BrowserManager()


# =========================================================
# TOOL FUNCTIONS
# =========================================================

def browser_open(url: str):

    return _browser.open_url(
        url
    )


def browser_state():

    return _browser.get_page_state()


def browser_click(target: str):

    return _browser.click(
        target
    )


def browser_fill(
    field: str,
    value: str,
):

    return _browser.fill(
        field,
        value,
    )


def browser_press(key: str):

    return _browser.press(
        key
    )


def browser_close():

    _browser.close()

    return {
        "success": True,
        "message": "Browser closed.",
    }

def youtube_search(query: str, limit: int = 5):
    return _browser.youtube_search(query, limit)


def youtube_play(video_url: str):
    return _browser.youtube_play(video_url)

