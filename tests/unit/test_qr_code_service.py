import pytest
from app.core.errors import InfrastructureError
from app.services.qr_code_service import QrCodeService

pytestmark = pytest.mark.unit

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def test_generate_returns_png_bytes():
    png = QrCodeService().generate_png("M00001")
    assert png[:8] == _PNG_SIGNATURE
    assert len(png) > 100


def test_generate_rejects_empty_data():
    with pytest.raises(InfrastructureError):
        QrCodeService().generate_png("")


def test_save_png_writes_a_file(tmp_path):
    path = QrCodeService().save_png("M00002", tmp_path / "qr.png")
    assert path.exists()
    assert path.read_bytes()[:8] == _PNG_SIGNATURE
