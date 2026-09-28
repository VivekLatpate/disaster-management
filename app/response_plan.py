import json
import httpx
from google import genai
from google.genai import types
from .config import settings

def generate_response_plan(description: str, latitude: float, longitude: float, place: str | None, context: dict, help_resources: list) -> dict:
    area = place or f"{latitude:.5f}, {longitude:.5f}"
    guidance = []
    if settings.firecrawl_api_key:
        query = f"site:gov.in OR site:nic.in {area} flood disaster response guidelines evacuation shelter emergency operations"
        try:
            response = httpx.post("https://api.firecrawl.dev/v2/search", headers={"Authorization": f"Bearer {settings.firecrawl_api_key}", "Content-Type": "application/json"}, json={"query": query, "limit": 5, "sources": [{"type": "web"}]}, timeout=30)
            response.raise_for_status(); payload = response.json(); data = payload.get("data", {})
            items = payload.get("web") or payload.get("results") or (data.get("web") if isinstance(data, dict) else []) or []
            guidance = [{"title": x.get("title"), "url": x.get("url"), "description": (x.get("description") or x.get("snippet") or "")[:400]} for x in items[:5]]
        except Exception:
            guidance = []
    if not settings.gemini_api_key:
        return {"status": "unavailable", "guidance": guidance, "error": "GEMINI_API_KEY is not configured"}
    prompt = f'''Create an English emergency-response planning aid for an administrator reviewing a resident incident.
Incident description: {description}
Location: {area} ({latitude}, {longitude})
Weather context: {json.dumps(context.get("weather"))}
Local guidance sources: {json.dumps(guidance)}
Nearby help leads: {json.dumps(help_resources)}

Return JSON with exactly these keys:
criticality (one of low, moderate, high, critical), criticality_reason (short), immediate_tasks (array of 5 or 6 short actionable tasks), resource_needs (array of objects with resource, quantity_or_scale, reason), safe_place_leads (array of at most 4 leads from provided resources), escalation_notes (short).
Do not invent phone numbers, shelters, capacities, road conditions, casualties, or official orders. Mark unknown quantities as "to be assessed". Treat coordinates, weather, AI observations, search results, and safe-place leads as unverified context. Do not say an area is safe. Recommend contacting official emergency services for critical situations.'''
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(model=settings.gemini_model, contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json"))
    plan = json.loads(response.text)
    plan["guidance"] = guidance
    plan["status"] = "unverified_planning_aid"
    return plan
