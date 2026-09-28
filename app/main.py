import uuid
from datetime import timezone
from pydantic import BaseModel
from pathlib import Path
from fastapi import FastAPI, Depends, File, Form, UploadFile, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session
from .config import settings
from .db import get_db
from .models import Report
from .ai import analyze_image
from .crosscheck import cross_check, nearby_help
from fastapi.concurrency import run_in_threadpool
from .speech import transcribe_audio
from .response_plan import generate_response_plan
app = FastAPI(title="Disaster Incident Reports")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
class ReviewUpdate(BaseModel):
    review_status: str
Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)
ALLOWED={"image/jpeg":"jpg","image/png":"png","image/webp":"webp"}
def run_ai(report_id, path):
    db=next(get_db()); report=db.get(Report, report_id)
    try:
        report.ai_processing_status="processing"; db.commit(); result=analyze_image(path); report.ai_category=result["category"]; report.ai_visible_evidence_summary=result["summary"]; report.ai_processing_status="completed"
    except Exception as e: report.ai_processing_status="failed"; report.ai_error=str(e)[:1000]
    db.commit(); db.close()
@app.get("/", response_class=HTMLResponse)
def page(): return FileResponse(Path(__file__).parent / "static" / "index.html")
@app.get("/admin", response_class=HTMLResponse)
def admin_page(): return FileResponse(Path(__file__).parent / "static" / "admin.html", headers={"Cache-Control": "no-store"})
@app.get("/media/{filename}")
def media(filename: str):
    p=Path(settings.storage_dir)/filename
    if not p.is_file(): raise HTTPException(404)
    return FileResponse(p)
@app.get("/api/health")
def health(): return {"status":"ok"}
@app.post("/api/transcribe")
async def transcribe(request: Request, audio: UploadFile|None=File(None)):
    if not settings.assemblyai_api_key: raise HTTPException(503, "Speech transcription is not configured")
    if audio is not None:
        allowed_audio = ("audio/webm", "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp4", "audio/ogg")
        if not audio.content_type or not any(audio.content_type.lower().startswith(mime) for mime in allowed_audio): raise HTTPException(415, "Unsupported audio format")
        data = await audio.read()
    else:
        data = await request.body()
        if not data: raise HTTPException(400, "Audio is required")
    if len(data) > 10 * 1024 * 1024: raise HTTPException(413, "Audio exceeds 10 MB limit")
    try: return {"text": await run_in_threadpool(transcribe_audio, data)}
    except Exception as exc: raise HTTPException(502, f"Transcription failed: {type(exc).__name__}")
@app.post("/api/reports", status_code=202)
def create_report(background_tasks: BackgroundTasks, description: str=Form(...), latitude: float=Form(...), longitude: float=Form(...), location_accuracy_m: float|None=Form(None), photo: UploadFile=File(...), db: Session=Depends(get_db)):
    if not (-90<=latitude<=90 and -180<=longitude<=180): raise HTTPException(422,"Coordinates out of range")
    if not 5<=len(description.strip())<=1000: raise HTTPException(422,"Description must be 5-1000 characters")
    if photo.content_type not in ALLOWED: raise HTTPException(415,"Only JPEG, PNG, and WebP images are accepted")
    data=photo.file.read()
    if len(data)>settings.max_image_size_bytes: raise HTTPException(413,"Image exceeds 10 MB limit")
    filename=f"{uuid.uuid4()}.{ALLOWED[photo.content_type]}"; path=Path(settings.storage_dir)/filename; path.write_bytes(data)
    r=Report(original_description=description.strip(), latitude=latitude, longitude=longitude, location_accuracy_m=location_accuracy_m, photo_path=filename, review_status="unverified", ai_processing_status="pending")
    db.add(r); db.commit(); db.refresh(r); background_tasks.add_task(run_ai, r.id, str(path))
    return {"report_id":str(r.id),"status":"pending_review"}
@app.get("/api/reports/{report_id}")
def get_report(report_id: uuid.UUID, db: Session=Depends(get_db)):
    r=db.get(Report,report_id)
    if not r: raise HTTPException(404,"Report not found")
    return {"report_id":str(r.id),"original_description":r.original_description,"latitude":r.latitude,"longitude":r.longitude,"location_accuracy_m":r.location_accuracy_m,"photo_url":f"/media/{r.photo_path}","created_at":r.created_at,"review_status":r.review_status,"ai_processing_status":r.ai_processing_status,"ai_category":r.ai_category,"ai_visible_evidence_summary":r.ai_visible_evidence_summary,"ai_error":r.ai_error}
@app.get("/api/admin/reports/{report_id}/cross-check")
def admin_cross_check(report_id: uuid.UUID, db: Session=Depends(get_db)):
    r = db.get(Report, report_id)
    if not r: raise HTTPException(404, "Report not found")
    created = r.created_at
    if created.tzinfo is None: created = created.replace(tzinfo=timezone.utc)
    result = cross_check(r.latitude, r.longitude, created.date())
    return {"report_id": str(r.id), "checked_coordinates": {"latitude": r.latitude, "longitude": r.longitude}, "report_date": created.date().isoformat(), **result}
@app.get("/api/admin/reports/{report_id}/nearby-help")
def admin_nearby_help(report_id: uuid.UUID, db: Session=Depends(get_db)):
    r = db.get(Report, report_id)
    if not r: raise HTTPException(404, "Report not found")
    place = None
    if settings.weatherapi:
        try:
            import httpx
            w = httpx.get(f"{settings.weatherapi_base_url}/current.json", params={"key": settings.weatherapi, "q": f"{r.latitude},{r.longitude}", "aqi": "no"}, timeout=15).json()
            loc = w.get("location", {}); place = ", ".join(x for x in [loc.get("name"), loc.get("region"), loc.get("country")] if x)
        except Exception: pass
    return {"report_id": str(r.id), "coordinates": {"latitude": r.latitude, "longitude": r.longitude}, **nearby_help(r.latitude, r.longitude, place, r.original_description)}
@app.get("/api/admin/reports/{report_id}/context")
def admin_context(report_id: uuid.UUID, db: Session=Depends(get_db)):
    r = db.get(Report, report_id)
    if not r: raise HTTPException(404, "Report not found")
    created = r.created_at if r.created_at.tzinfo else r.created_at.replace(tzinfo=timezone.utc)
    return {"report_id": str(r.id), **cross_check(r.latitude, r.longitude, created.date()), **nearby_help(r.latitude, r.longitude, None, r.original_description)}
@app.get("/api/admin/reports/{report_id}/response-plan")
def admin_response_plan(report_id: uuid.UUID, db: Session=Depends(get_db)):
    r = db.get(Report, report_id)
    if not r: raise HTTPException(404, "Report not found")
    created = r.created_at if r.created_at.tzinfo else r.created_at.replace(tzinfo=timezone.utc)
    context = cross_check(r.latitude, r.longitude, created.date())
    help_data = nearby_help(r.latitude, r.longitude)
    try:
        plan = generate_response_plan(r.original_description, r.latitude, r.longitude, (context.get("resolved_place") or {}).get("name"), context, help_data.get("resources", []))
    except Exception as exc:
        raise HTTPException(502, f"Response plan generation failed: {type(exc).__name__}")
    return {"report_id": str(r.id), "review_status": r.review_status, "ai_category": r.ai_category, **plan}
@app.get("/api/admin/reports")
def admin_reports(db: Session=Depends(get_db)):
    reports = db.query(Report).filter(Report.review_status != "rejected").order_by(Report.created_at.desc()).all()
    return [{"report_id": str(r.id), "description": r.original_description, "latitude": r.latitude, "longitude": r.longitude, "accuracy_m": r.location_accuracy_m, "created_at": r.created_at, "review_status": r.review_status, "ai_processing_status": r.ai_processing_status, "ai_category": r.ai_category} for r in reports]
@app.patch("/api/admin/reports/{report_id}/review")
def update_review(report_id: uuid.UUID, update: ReviewUpdate, db: Session=Depends(get_db)):
    if update.review_status not in {"verified", "rejected", "needs_more_information"}: raise HTTPException(422, "Invalid review status")
    r = db.get(Report, report_id)
    if not r: raise HTTPException(404, "Report not found")
    r.review_status = update.review_status; db.commit(); db.refresh(r)
    return {"report_id": str(r.id), "review_status": r.review_status, "ai_processing_status": r.ai_processing_status}

