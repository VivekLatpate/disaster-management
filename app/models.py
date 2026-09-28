import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
class Base(DeclarativeBase): pass
class Report(Base):
    __tablename__ = "reports"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    original_description: Mapped[str] = mapped_column(String(1000))
    latitude: Mapped[float] = mapped_column(Float); longitude: Mapped[float] = mapped_column(Float)
    location_accuracy_m: Mapped[float | None] = mapped_column(Float)
    photo_path: Mapped[str] = mapped_column(String(500)); created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    review_status: Mapped[str] = mapped_column(String(30), default="unverified")
    ai_processing_status: Mapped[str] = mapped_column(String(30), default="pending")
    ai_category: Mapped[str | None] = mapped_column(String(50)); ai_visible_evidence_summary: Mapped[str | None] = mapped_column(String(1000)); ai_error: Mapped[str | None] = mapped_column(String(1000))

