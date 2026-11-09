# Khởi động giao diện web: backend FastAPI (cổng 8000) + frontend Next.js (cổng 3000), mỗi cái một
# cửa sổ PowerShell, rồi mở trình duyệt vào tab Suy luận.
# Dùng: powershell -ExecutionPolicy Bypass -File start_ui.ps1
# Yêu cầu: đã chạy pipeline để có gói suy luận models/inference/ (run_pipeline.py, tune_models.py, evaluate.py).

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\python.exe"
$frontend = Join-Path $root "frontend"

if (-not (Test-Path $python)) { Write-Error "Không thấy .venv. Chạy: python -m venv .venv; .venv\Scripts\pip install -r requirements.txt"; exit 1 }
if (-not (Test-Path (Join-Path $root "models\inference\model.json"))) {
    Write-Warning "Chưa có gói suy luận (models\inference). Tab Suy luận sẽ báo 'Chưa có mô hình' cho tới khi chạy pipeline + evaluate.py."
}
if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Output "[UI] Cài thư viện frontend (lần đầu)..."
    pnpm --dir $frontend install
}

Start-Process powershell -WorkingDirectory $root -ArgumentList "-NoExit", "-Command", "& '$python' -m uvicorn backend.app:app --port 8000"
Start-Process powershell -WorkingDirectory $frontend -ArgumentList "-NoExit", "-Command", "pnpm dev"

Write-Output "[UI] Đang khởi động backend (http://localhost:8000) và frontend (http://localhost:3000)..."
for ($i = 0; $i -lt 60; $i++) {
    try { Invoke-WebRequest -Uri "http://localhost:3000/infer" -UseBasicParsing -TimeoutSec 2 | Out-Null; break } catch { Start-Sleep -Seconds 1 }
}
Start-Process "http://localhost:3000/infer"
