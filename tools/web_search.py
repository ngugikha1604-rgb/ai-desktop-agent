"""Tool web_search — tìm kiếm thông tin thực sự từ DuckDuckGo và trả về text.

Khác với search_web (chỉ mở browser), tool này trả về nội dung kết quả
để model có thể đọc và trả lời câu hỏi của người dùng.

Yêu cầu: pip install duckduckgo-search
"""
from __future__ import annotations

from tools.result import fail, ok

_MAX_SNIPPET = 220   # ký tự tối đa cho mỗi snippet — cân bằng thông tin/token
_DEFAULT_N   = 5     # số kết quả mặc định


def web_search(query: str, max_results: int = _DEFAULT_N) -> dict:
    """Tìm kiếm DuckDuckGo, trả về danh sách kết quả dạng text.

    Args:
        query:       Câu truy vấn tìm kiếm.
        max_results: Số kết quả tối đa trả về (mặc định 5).

    Returns:
        dict với data = danh sách {"title", "url", "snippet"} và
        message là summary dạng text để model đọc trực tiếp.
    """
    query = query.strip()
    if not query:
        return fail("Câu truy vấn không được để trống.", retryable=False)

    max_results = max(1, min(int(max_results), 10))  # clamp 1–10

    try:
        from ddgs import DDGS
    except ImportError:
        return fail(
            "Thư viện 'ddgs' chưa được cài. Chạy: pip install ddgs",
            retryable=False,
        )

    try:
        raw = list(DDGS().text(query, max_results=max_results))
    except Exception as exc:
        return fail(f"Lỗi khi tìm kiếm: {exc}", retryable=True)

    if not raw:
        return fail(
            f"Không tìm thấy kết quả nào cho: '{query}'",
            retryable=False,
        )

    results = []
    lines: list[str] = [f"Kết quả tìm kiếm cho: \"{query}\"\n"]

    for i, item in enumerate(raw, 1):
        title   = (item.get("title")   or "").strip()
        url     = (item.get("href")    or "").strip()
        snippet = (item.get("body")    or "").strip()

        # Truncate snippet để tiết kiệm token
        if len(snippet) > _MAX_SNIPPET:
            snippet = snippet[:_MAX_SNIPPET].rsplit(" ", 1)[0] + "…"

        results.append({"title": title, "url": url, "snippet": snippet})
        lines.append(f"[{i}] {title}")
        lines.append(f"    {url}")
        lines.append(f"    {snippet}")
        lines.append("")

    message = "\n".join(lines).strip()
    return ok(message, data=results)
