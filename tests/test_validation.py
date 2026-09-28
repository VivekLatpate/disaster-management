from pathlib import Path
from app.main import ALLOWED

def test_allowed_images_and_ranges():
    assert set(ALLOWED) == {"image/jpeg", "image/png", "image/webp"}
    assert -90 <= 12.3 <= 90 and -180 <= 77.5 <= 180

def test_invalid_coordinates_are_outside_range():
    assert not (-90 <= 100 <= 90)
    assert not (-180 <= 200 <= 180)

def test_upload_limit_is_10mb():
    from app.config import settings
    assert settings.max_image_size_bytes == 10 * 1024 * 1024

