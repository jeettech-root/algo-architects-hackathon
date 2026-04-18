# CyberShield Startup Script
# Run this after laptop restart

Write-Host "🚀 Starting CyberShield System..." -ForegroundColor Green

# 1. Start Backend
Write-Host "📡 Starting Backend API..." -ForegroundColor Yellow
Set-Location "$PSScriptRoot\backend"
Start-Process -FilePath "python" -ArgumentList "main.py" -NoNewWindow

# Wait for backend to start
Start-Sleep -Seconds 3

# 2. Start Dashboard
Write-Host "📊 Starting React Dashboard..." -ForegroundColor Yellow
Set-Location "$PSScriptRoot\dashboard"
Start-Process -FilePath "npm" -ArgumentList "run dev" -NoNewWindow

Write-Host "✅ CyberShield System Started!" -ForegroundColor Green
Write-Host "🌐 Backend: http://localhost:8000" -ForegroundColor Cyan
Write-Host "📱 Dashboard: http://localhost:5173" -ForegroundColor Cyan
Write-Host "🔧 Extension: Already loaded in Chrome" -ForegroundColor Cyan