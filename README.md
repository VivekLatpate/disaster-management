# Disaster incident reporting

## Clone and run for teammates

```powershell
git clone https://github.com/VivekLatpate/disaster-management.git
cd disaster-management
```

Create the local environment file. Never commit `.env`:

```powershell
Copy-Item .env.example .env
```

Open `.env` and add the provider keys your local machine needs: `GEMINI_API_KEY`, `ASSEMBLYAI_API_KEY`, `firecrawl_api_key`, and `weatherapi`. Provider keys are used only by the backend and must not be placed in React code.

### Backend

Install Python 3.11+ and Docker Desktop, then run:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
docker compose up -d db
alembic upgrade head
uvicorn app.main:app --reload
```

The API and the original server-rendered page are available at http://127.0.0.1:8000. API documentation is at http://127.0.0.1:8000/docs.

### React frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The React app uses `http://127.0.0.1:8000` by default. To use another backend URL, create `frontend/.env` with:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Run tests from the repository root:

```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests
```

If the browser shows CORS errors, confirm that FastAPI is running on port 8000 and that the React app is running on port 5173. If GPS or microphone access is denied, use manual coordinates or typed description; deployed GPS/microphone access requires HTTPS.

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

## React frontend

The separate React frontend is in `frontend/`. Run `cd frontend; npm install; npm run dev`, then open http://localhost:5173. It connects to the FastAPI backend at `http://127.0.0.1:8000`; set `VITE_API_URL` if the backend is hosted elsewhere.

## Tests

`pytest -q`

