from alembic import op
import sqlalchemy as sa
revision = "001_create_reports"
down_revision = None
def upgrade():
    op.create_table("reports",
        sa.Column("id", sa.UUID(), primary_key=True), sa.Column("original_description", sa.String(1000), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False), sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("location_accuracy_m", sa.Float()), sa.Column("photo_path", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("review_status", sa.String(30), nullable=False),
        sa.Column("ai_processing_status", sa.String(30), nullable=False), sa.Column("ai_category", sa.String(50)),
        sa.Column("ai_visible_evidence_summary", sa.String(1000)), sa.Column("ai_error", sa.String(1000)))
def downgrade(): op.drop_table("reports")

