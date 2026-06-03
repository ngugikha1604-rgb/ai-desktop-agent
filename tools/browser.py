"""Tool open_url / search_web — mở URL và tìm kiếm Google."""
import webbrowser
from urllib.parse import quote

from tools.result import fail, ok


def open_url(url: str) -> dict:
    """Mở URL trong trình duyệt mặc định của hệ thống.

    - Tự động thêm https:// nếu không có scheme.
    - Giữ nguyên các scheme khác: ftp://, mailto:, ...
    """
    url = url.strip()
    if not url:
        return fail("URL không được để trống.")

    # Thêm https:// nếu chưa có scheme
    if "://" not in url and not url.startswith("mailto:"):
        url = "https://" + url

    try:
        webbrowser.open(url)
        return ok(f"Đã mở: {url}", {"url": url})
    except OSError as e:
        return fail(f"Không thể mở trình duyệt: {e}", None)
    except Exception as e:
        return fail(f"Không thể mở trình duyệt: {e}", None)


def build_search_url(query: str) -> str:
    """Tạo URL tìm kiếm Google với query được URL-encode (RFC 3986)."""
    return f"https://www.google.com/search?q={quote(query, safe='')}"


def search_web(query: str) -> dict:
    """Tìm kiếm Google với từ khoá đã nhập (hỗ trợ Unicode / tiếng Việt)."""
    query = query.strip()
    if not query:
        return fail("Từ khoá tìm kiếm không được để trống.")
    return open_url(build_search_url(query))
