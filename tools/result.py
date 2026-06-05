from typing import Any


def ok(message: str, data: Any = None) -> dict:
    """Trả về kết quả thành công. retryable luôn là False khi thành công."""
    return {"success": True, "retryable": False, "message": message, "data": data}


def fail(message: str, data: Any = None, retryable: bool = True) -> dict:
    """Trả về kết quả thất bại.

    Args:
        message:   Mô tả lỗi.
        data:      Dữ liệu bổ sung (tuỳ chọn).
        retryable: True  → lỗi tạm thời, agent có thể thử lại.
                   False → lỗi vĩnh viễn (app không tồn tại, path sai...).
    """
    return {"success": False, "retryable": retryable, "message": message, "data": data}
