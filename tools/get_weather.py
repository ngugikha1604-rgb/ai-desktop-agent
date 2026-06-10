"""Tool get_weather — lay thoi tiet hien tai cua mot thanh pho.

Dung wttr.in JSON API: mien phi, khong can API key, khong can JS.
Nhanh hon va dang tin hon web_search -> web_read chain cho thoi tiet.

Yeu cau: pip install requests  (thuong da cai san)
"""
from __future__ import annotations

from tools.result import fail, ok


def get_weather(city: str) -> dict:
    """Lay thoi tiet hien tai cua mot thanh pho qua wttr.in.

    Args:
        city: Ten thanh pho bang tieng Anh (vd: "Hanoi", "Ho Chi Minh City").

    Returns:
        dict voi message la thong tin thoi tiet dang text.
    """
    city = city.strip()
    if not city:
        return fail("Ten thanh pho khong duoc de trong.", retryable=False)

    try:
        import requests
    except ImportError:
        return fail("Thu vien 'requests' chua cai. Chay: pip install requests", retryable=False)

    try:
        url = f"https://wttr.in/{requests.utils.quote(city)}?format=j1"
        resp = requests.get(
            url,
            headers={"User-Agent": "curl/7.68.0"},
            timeout=10,
        )
        if resp.status_code == 404:
            return fail(f"Khong tim thay thanh pho: '{city}'", retryable=False)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        return fail("Timeout khi lay thoi tiet.", retryable=True)
    except requests.exceptions.ConnectionError:
        return fail("Khong ket noi duoc den wttr.in.", retryable=True)
    except (ValueError, KeyError) as exc:
        return fail(f"Khong doc duoc du lieu thoi tiet: {exc}", retryable=False)
    except Exception as exc:
        return fail(f"Loi khong xac dinh: {exc}", retryable=True)

    try:
        cur  = data["current_condition"][0]
        area = data.get("nearest_area", [{}])[0]

        temp_c     = cur["temp_C"]
        feels_like = cur["FeelsLikeC"]
        humidity   = cur["humidity"]
        wind_kmph  = cur["windspeedKmph"]
        visibility = cur["visibility"]
        desc       = cur["weatherDesc"][0]["value"]

        area_name = area.get("areaName",  [{}])[0].get("value", city)
        country   = area.get("country",   [{}])[0].get("value", "")
        location  = f"{area_name}, {country}" if country else area_name

        msg = (
            f"Thoi tiet hien tai tai {location}:\n"
            f"  Nhiet do: {temp_c}C (cam giac nhu {feels_like}C)\n"
            f"  Thoi tiet: {desc}\n"
            f"  Do am: {humidity}%\n"
            f"  Gio: {wind_kmph} km/h\n"
            f"  Tam nhin: {visibility} km\n"
            f"  Nguon: wttr.in"
        )
        return ok(msg, data={
            "city": location,
            "temp_c": temp_c,
            "feels_like_c": feels_like,
            "humidity": humidity,
            "wind_kmph": wind_kmph,
            "description": desc,
        })
    except (KeyError, IndexError) as exc:
        return fail(f"Du lieu thoi tiet khong dung dinh dang: {exc}", retryable=False)
