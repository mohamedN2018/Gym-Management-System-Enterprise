#!/usr/bin/env python
"""Build a standalone native executable with Nuitka (the locked packaging tool).

Produces a per-OS application directory containing ``GymERP[.exe]``. Run from the project's
virtual environment:

    python scripts/build.py                # standalone, windowed (no console)
    python scripts/build.py --console      # keep a console window (for debugging)
    python scripts/build.py --onefile      # single-file executable (slower build/startup)

Nuitka downloads its own C toolchain on first run (``--assume-yes-for-downloads``), so no
preinstalled compiler is required.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOGS = ROOT / "app" / "localization" / "catalogs"


def build(*, onefile: bool, console: bool, output_dir: str) -> int:
    command = [
        sys.executable,
        "-m",
        "nuitka",
        str(ROOT / "launcher.py"),
        "--standalone",
        "--assume-yes-for-downloads",
        "--enable-plugin=pyside6",
        "--include-package=app",
        # These are imported lazily inside services, so force Nuitka to bundle them.
        "--include-package=qrcode",
        "--include-package=openpyxl",
        "--include-package=reportlab",
        # reportlab ships fonts/data needed for PDF export; bundle them.
        "--include-package-data=reportlab",
        # Bundle the translation catalogs (loaded from disk at runtime).
        f"--include-data-dir={CATALOGS}=app/localization/catalogs",
        # Bundle assets (window icon) next to the executable.
        f"--include-data-dir={ROOT / 'assets'}=assets",
        f"--output-dir={output_dir}",
        "--output-filename=GymERP",
        "--company-name=Gym ERP",
        "--product-name=Gym ERP",
        "--file-version=0.1.0",
        "--product-version=0.1.0",
        "--remove-output",
    ]
    if onefile:
        command.append("--onefile")
    if sys.platform.startswith("win") and not console:
        command.append("--windows-console-mode=disable")

    icon = ROOT / "assets" / "icon.ico"
    if sys.platform.startswith("win") and icon.exists():
        command.append(f"--windows-icon-from-ico={icon}")

    print("Running:", " ".join(command))
    return subprocess.call(command, cwd=str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Gym ERP executable with Nuitka.")
    parser.add_argument("--onefile", action="store_true", help="single-file executable")
    parser.add_argument("--console", action="store_true", help="keep the console window")
    parser.add_argument("--output-dir", default=str(ROOT / "build" / "nuitka"))
    args = parser.parse_args()
    return build(onefile=args.onefile, console=args.console, output_dir=args.output_dir)


if __name__ == "__main__":
    sys.exit(main())
