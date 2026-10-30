"""Keyless web search with bounded results for agent research."""
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote_plus, urlparse
from urllib.request import Request, urlopen


class _ResultsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self._current = None
        self._capture = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()
        if tag == "a" and "result__a" in classes:
            raw_url = attrs.get("href", "")
            query = parse_qs(urlparse(raw_url).query)
            url = query.get("uddg", [raw_url])[0]
            parsed = urlparse(url)
            if parsed.scheme in {"http", "https"} and parsed.netloc:
                self._current = {"title": "", "url": url, "snippet": ""}
                self.results.append(self._current)
                self._capture = "title"
        elif self._current and "result__snippet" in classes:
            self._capture = "snippet"

    def handle_endtag(self, tag):
        if tag == "a" and self._capture == "title":
            self._capture = None
        if tag in {"div", "td"} and self._capture == "snippet":
            self._capture = None
            self._current = None

    def handle_data(self, data):
        if self._current and self._capture in {"title", "snippet"}:
            key = self._capture
            self._current[key] = (self._current[key] + data).strip()


def web_search(query: str, max_results: int = 5) -> dict:
    query = query.strip()
    if not query or len(query) > 500:
        return {"success": False, "error": "query must contain 1–500 characters"}
    if not 1 <= max_results <= 8:
        return {"success": False, "error": "max_results must be between 1 and 8"}
    request = Request(
        "https://html.duckduckgo.com/html/?q=" + quote_plus(query),
        headers={"User-Agent": "Apoorva/1.0 (personal research assistant)"},
    )
    try:
        with urlopen(request, timeout=12) as response:
            html = response.read(1_000_000).decode("utf-8", errors="replace")
        parser = _ResultsParser()
        parser.feed(html)
        results = [r for r in parser.results if r["title"]][:max_results]
        return {"success": True, "query": query, "source": "DuckDuckGo HTML search", "results": results,
                "message": "Search snippets are leads, not verified page contents. Open primary sources before making detailed claims."}
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        return {"success": False, "query": query, "error": f"Search request failed: {type(exc).__name__}"}
