# Disaster incident reporting

This is an English-only FastAPI service for submitting one incident photo with a resident's description and coordinates. The original description is never changed. `review_status` is independent from `ai_processing_status`; Gemini output is only an unverified suggestion.

## Run locally

1. Copy `.env.example` to `.env` and set `GEMINI_API_KEY` (the existing `.env` may be used; do not commit it).
2. Start PostgreSQL: `docker compose up -d db`
3. Create an environment and install packages: `py -m venv .venv; .venv\Scripts\Activate.ps1; pip install -r requirements.txt`
4. Apply migrations: `alembic upgrade head`
5. Run: `uvicorn app.main:app --reload`
6. Open http://127.0.0.1:8000. GPS requires HTTPS in a deployed environment.

Uploaded images are stored in `STORAGE_DIR` (default `./uploads`) outside the Python source package and receive generated names. JPEG, PNG, and WebP are accepted up to 10 MB. The local background task starts Gemini after the database commit; failures set `ai_processing_status=failed` and preserve the report. A production deployment should replace this with a durable queue and retry policy.

## API example

`curl -X POST http://127.0.0.1:8000/api/reports -F description="Water covering the road" -F latitude=12.9716 -F longitude=77.5946 -F location_accuracy_m=15 -F photo=@incident.jpg`

Then check with `curl http://127.0.0.1:8000/api/reports/<report-id>`.

## Admin cross-check

Open `http://127.0.0.1:8000/admin` to view reports on a map. Marker colors represent the Gemini-suggested category and circles represent submitted GPS accuracy. Admins can mark each report `verified`, `rejected`, or `needs_more_information`; this human review value is separate from Gemini's suggestion. The page also supports the WeatherAPI/Firecrawl cross-check endpoint. This is a local-development admin page and currently has no authentication; add authentication before deployment. External weather, web results, GPS, and AI output are contextual evidence only and never prove an incident occurred.

The nearby-help endpoint is `GET /api/admin/reports/<report-id>/nearby-help`. It searches for nearby emergency helplines, fire stations, shelters/safe spaces, hospitals, police, and disaster-control contacts. Results are leads for admin verification, not guaranteed live services or safe locations.

## Tests

`pytest -q`

