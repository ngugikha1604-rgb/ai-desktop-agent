"""Tool web_read -- doc noi dung van ban tu mot URL cu the.

Strategy hai tang:
1. Direct request + BeautifulSoup (nhanh, du cho trang tinh)
2. Jina AI Reader fallback (xu ly JS-rendered sites nhu AccuWeather, React apps...)
   Jina mien phi, khong can API key, render JS phia server -> tra clean text.

Yeu cau: pip install requests beautifulsoup4
"""
from __future__ import annotations

from tools.result import fail, ok

_MAX_CHARS        = 1800   # gioi han ky tu tra ve
_MIN_CONTENT_LEN  = 200    # nguong noi dung toi thieu -- duoi nay coi la "trang rong/JS"
_JINA_BASE        = "https://r.jina.ai/"
_HEADERS_BROWSER  = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
_HEADERS_JINA = {
    "User-Agent": "curl/7.68.0",
    "Accept": "text/plain, text/markdown",
    "X-Timeout": "10",
}


def web_read(url: str) -> dict:
    """Doc noi dung text tu mot URL.

    Thu direct request truoc (nhanh). Neu content qua ngan hoac trong
    (dau hieu trang JS-heavy), fallback sang Jina AI Reader.

    Args:
        url: URL can doc (lay tu ket qua web_search).

    Returns:
        dict voi message la noi dung text da lam sach.
    """
    url = url.strip()
    if not url:
        return fail("URL khong duoc de trong.", retryable=False)

    try:
        import requests
    except ImportError:
        return fail("Thu vien 'requests' chua cai. Chay: pip install requests", retryable=False)

    # ── Tang 1: Direct request ────────────────────────────────────────────────
    content, err = _fetch_direct(url, requests)

    # ── Tang 2: Jina fallback neu content qua ngan ───────────────────────────
    if content is not None and len(content) < _MIN_CONTENT_LEN:
        jina_content, jina_err = _fetch_jina(url, requests)
        if jina_content and len(jina_content) >= _MIN_CONTENT_LEN:
            content = jina_content
        # Neu Jina cung that bai, giu content cu (du ngan) hoac bao loi Jina
        elif jina_content is None and content is None:
            err = jina_err  # ca hai deu het -- dung loi Jina (ro hon)

    if content is None:
        return fail(err or "Khong doc duoc noi dung.", retryable=True)

    if not content.strip():
        return fail(f"Khong trich xuat duoc noi dung tu: {url}", retryable=False)

    # Truncate theo dong de khong cat giua cau
    if len(content) > _MAX_CHARS:
        content = content[:_MAX_CHARS].rsplit("\n", 1)[0] + "\n...(con tiep)"

    return ok(f"Noi dung tu {url}:\n\n{content}", data={"url": url, "content": content})


# ── Tang 1: Direct request + BeautifulSoup ────────────────────────────────────

def _fetch_direct(url: str, requests) -> tuple[str | None, str | None]:
    """Tra ve (content, error). Content=None neu that bai."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return None, "Thu vien 'beautifulsoup4' chua cai. Chay: pip install beautifulsoup4"

    try:
        resp = requests.get(url, headers=_HEADERS_BROWSER, timeout=10)
        if 400 <= resp.status_code < 500:
            return None, f"HTTP {resp.status_code}: trang khong ton tai hoac bi chan."
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        return None, "Timeout khi tai trang."
    except requests.exceptions.ConnectionError:
        return None, "Khong ket noi duoc."
    except requests.exceptions.HTTPError as exc:
        return None, f"Loi HTTP: {exc}"
    except Exception as exc:
        return None, f"Loi: {exc}"

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    # Uu tien content tags -- tranh lay menu/sidebar
    node = (
        soup.find("article")
        or soup.find("main")
        or soup.find(id="content")
        or soup.find(class_="content")
        or soup.find(class_="post-content")
        or soup.body
        or soup
    )
    raw = node.get_text(separator="\n")
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    return "\n".join(lines), None


# ── Tang 2: Jina AI Reader (xu ly JS-rendered sites) ─────────────────────────

def _fetch_jina(url: str, requests) -> tuple[str | None, str | None]:
    """Fallback qua r.jina.ai -- render JS phia server, tra clean markdown."""
    jina_url = f"{_JINA_BASE}{url}"
    try:
        resp = requests.get(jina_url, headers=_HEADERS_JINA, timeout=20)
        if resp.status_code == 429:
            return None, "Jina Reader qua tai (rate limit). Thu lai sau."
        if 400 <= resp.status_code < 500:
            return None, f"Jina Reader: HTTP {resp.status_code}."
        resp.raise_for_status()
        content = resp.text.strip()
        return content if content else None, None
    except requests.exceptions.Timeout:
        return None, "Timeout khi goi Jina Reader."
    except Exception as exc:
        return None, f"Jina Reader loi: {exc}"
