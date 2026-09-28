import json
from google import genai
from google.genai import types
from .config import settings
def analyze_image(path: str) -> dict:
    if not settings.gemini_api_key: raise RuntimeError("GEMINI_API_KEY is not configured")
    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = ('Analyze only visible evidence in this disaster photo. Return JSON with category (one of flooding, fallen_tree, fire, road_damage, building_damage, other) and visible_evidence_summary (short English sentence). Do not infer exact location, water depth, casualties, authenticity, or safety. This is an unverified suggestion.')
    mime_type = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(__import__("pathlib").Path(path).suffix.lower(), "image/jpeg")
    with open(path, "rb") as image_file:
        image_bytes = image_file.read()
    response = client.models.generate_content(model=settings.gemini_model, contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type=mime_type)], config=types.GenerateContentConfig(response_mime_type="application/json"))
    data = json.loads(response.text); return {"category": data.get("category", "other"), "summary": data.get("visible_evidence_summary", "")[:1000]}

