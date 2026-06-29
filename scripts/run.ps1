# Run Gym ERP from source using the project virtual environment.
$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $root ".venv\Scripts\python.exe") (Join-Path $root "launcher.py") @args
