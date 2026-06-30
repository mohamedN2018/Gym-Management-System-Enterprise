"""Global application services (business-agnostic, reusable across modules).

These services depend only on the foundation/infrastructure, never on business modules
(Part 2: *global services must never depend on business modules*).
"""

from app.services.backup_service import BackupService
from app.services.qr_code_service import QrCodeService

__all__ = ["BackupService", "QrCodeService"]
