"""QR code generation (local, offline).

Generates QR PNGs for arbitrary payloads (e.g. a member's membership number). Since hardware
scanners and phone cameras emit the decoded text as keyboard input, encoding the membership
number makes the existing check-in flow scan-ready with no extra integration.
"""

from __future__ import annotations

import io
from pathlib import Path

import qrcode

from app.core.errors import InfrastructureError


class QrCodeService:
    """Stateless QR code generator."""

    def generate_png(self, data: str, *, box_size: int = 8, border: int = 2) -> bytes:
        """Return PNG bytes encoding ``data``. Raises :class:`InfrastructureError` on failure."""
        if not data:
            raise InfrastructureError("Cannot generate a QR code for empty data.")
        try:
            qr = qrcode.QRCode(box_size=box_size, border=border)
            qr.add_data(data)
            qr.make(fit=True)
            image = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return buffer.getvalue()
        except Exception as exc:
            raise InfrastructureError("Failed to generate QR code.", cause=exc) from exc

    def save_png(self, data: str, path: str | Path, *, box_size: int = 8, border: int = 2) -> Path:
        """Generate a QR PNG for ``data`` and write it to ``path``; returns the path."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.generate_png(data, box_size=box_size, border=border))
        return target
