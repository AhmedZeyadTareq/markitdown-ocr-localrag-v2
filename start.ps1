# Starts the API server and the web UI, then opens the app in your browser.
# Run from PowerShell:  .\start.ps1   (close both windows to stop)
$root = $PSScriptRoot

if (-not (Test-Path "$root\web\node_modules")) {
    Write-Host "Installing web UI packages (first run only)..."
    npm --prefix "$root\web" install
}

# The API runs in its own window so its logs stay visible
Start-Process "$root\.venv\Scripts\python.exe" -ArgumentList "-m backend.api" -WorkingDirectory $root

# Open the browser once the web server has had a moment to start
Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoProfile -Command Start-Sleep 6; Start-Process http://localhost:3000"

npm --prefix "$root\web" run dev
