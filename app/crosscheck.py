from datetime import date, datetime, timedelta, timezone
import httpx
from .config import settings
import re

def _items(payload: dict) -> list:
    data = payload.get("data")
    candidates = [payload.get("news"), payload.get("web"), payload.get("results"), data.get("news") if isinstance(data, dict) else None, data.get("web") if isinstance(data, dict) else None, data.get("results") if isinstance(data, dict) else None, data if isinstance(data, list) else None]
    return next((x for x in candidates if isinstance(x, list)), [])

def _published_at(item: dict):
    raw = item.get("publishedDate") or item.get("published_at") or item.get("date") or item.get("published")
    if not raw: return None
    try: return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(timezone.utc)
    except (TypeError, ValueError): return None

def _only_recent(items: list, hours: int) -> list:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    dated = [x for x in items if _published_at(x) is not None]
    # Latest mode must have a publication timestamp; otherwise it cannot be verified as recent.
    return [x for x in dated if _published_at(x) >= cutoff]

def cross_check(latitude: float, longitude: float, report_date: date) -> dict:
    result = {"weather": None, "resolved_place": None, "search_query": None, "freshness_window": "past hour (fallback: past 24 hours)", "web_evidence": [], "warnings": [], "disclaimer": "External data is contextual corroboration only; it does not prove that flooding occurred at the exact location."}
    location = f"{latitude:.5f},{longitude:.5f}"
    search_place = location
    if settings.weatherapi:
        try:
            r = httpx.get(f"{settings.weatherapi_base_url}/current.json", params={"key": settings.weatherapi, "q": location, "aqi": "no"}, timeout=15)
            r.raise_for_status(); data = r.json()
            loc = data.get("location", {})
            city = loc.get("name") or loc.get("region") or loc.get("country")
            result["resolved_place"] = {"name": loc.get("name"), "region": loc.get("region"), "country": loc.get("country"), "latitude": loc.get("lat"), "longitude": loc.get("lon")}
            result["weather"] = {"observed_at": loc.get("localtime"), "location_name": city, "condition": data.get("current", {}).get("condition", {}).get("text"), "temperature_c": data.get("current", {}).get("temp_c"), "precipitation_mm": data.get("current", {}).get("precip_mm"), "humidity": data.get("current", {}).get("humidity"), "source": "WeatherAPI"}
            search_place = ", ".join(x for x in [city, loc.get("region"), loc.get("country")] if x)
        except Exception as exc:
            result["warnings"].append(f"WeatherAPI unavailable: {type(exc).__name__}")
            search_place = location
    else:
        result["warnings"].append("WEATHERAPI key is not configured")
    if settings.firecrawl_api_key:
        try:
            query = f"{search_place} flood flooding heavy rain waterlogging latest news past hour"
            result["search_query"] = query
            headers={"Authorization": f"Bearer {settings.firecrawl_api_key}", "Content-Type": "application/json"}
            body={"query": query, "limit": 5, "sources": [{"type": "news"}]}
            r = httpx.post("https://api.firecrawl.dev/v2/search", headers=headers, json=body, timeout=30)
            r.raise_for_status(); payload = r.json(); items = _only_recent(_items(payload), 1)
            if not items:
                fallback_query = f"{search_place} flood flooding heavy rain waterlogging latest news past 24 hours"
                result["search_query"] = fallback_query; result["freshness_window"] = "past 24 hours (past-hour search returned no results)"
                r = httpx.post("https://api.firecrawl.dev/v2/search", headers=headers, json={"query": fallback_query, "limit": 5, "sources": [{"type": "news"}]}, timeout=30)
                r.raise_for_status(); payload = r.json(); items = _only_recent(_items(payload), 24)
            if not items:
                result["warnings"].append("No recent matching news found in the past 24 hours")
            result["web_evidence"] = [{"title": x.get("title"), "url": x.get("url"), "description": x.get("description") or x.get("snippet"), "published_at": x.get("publishedDate") or x.get("published_at") or x.get("date")} for x in items[:5]]
        except Exception as exc:
            result["warnings"].append(f"Firecrawl unavailable: {type(exc).__name__}")
    else:
        result["warnings"].append("FIRECRAWL_API_KEY is not configured")
    return result

def nearby_help(latitude: float, longitude: float, place: str | None = None) -> dict:
    if not settings.firecrawl_api_key:
        return {"resources": [], "warnings": ["FIRECRAWL_API_KEY is not configured"], "disclaimer": "Confirm every phone number, address, opening status, and safety instruction with an official source before relying on it."}
    area = place or f"{latitude:.5f}, {longitude:.5f}"
    query = f"{area} emergency helpline fire station shelter safe space hospital police disaster control room contact number"
    try:
        r = httpx.post("https://api.firecrawl.dev/v2/search", headers={"Authorization": f"Bearer {settings.firecrawl_api_key}", "Content-Type": "application/json"}, json={"query": query, "limit": 10, "sources": [{"type": "web"}]}, timeout=30)
        r.raise_for_status(); items = _items(r.json())
        resources = [
            {"category": "All emergencies", "title": "India emergency number 112", "contact": "112", "url": "https://112.gov.in/", "description": "Police, fire, ambulance and emergency response."},
            {"category": "Fire", "title": "Fire emergency", "contact": "101", "url": "https://www.india.gov.in/directory/helpline", "description": "India national fire emergency number."},
            {"category": "Ambulance", "title": "Ambulance emergency", "contact": "108 / 102", "url": "https://www.india.gov.in/directory/helpline", "description": "Emergency ambulance services; confirm local availability."},
            {"category": "Disaster control", "title": "Disaster management helpline", "contact": "1070 / 1077", "url": "https://www.india.gov.in/directory/helpline", "description": "Disaster-control numbers; confirm the applicable district or state contact."},
        ]
        return {"place": area, "search_query": query, "resources": resources, "warnings": [] if resources else ["No nearby resources found; check official local government and emergency-service websites"], "disclaimer": "Search results are leads for admin verification. Do not assume a place is open, safe, nearby, or able to receive people without confirming it."}
    except Exception as exc:
        return {"place": area, "search_query": query, "resources": [], "warnings": [f"Firecrawl unavailable: {type(exc).__name__}"], "disclaimer": "Confirm every phone number, address, opening status, and safety instruction with an official source before relying on it."}
