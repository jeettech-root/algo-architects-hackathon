@echo off
echo 🚀 Starting CyberShield System...
echo.

echo 📡 Starting Backend API...
cd backend
start "CyberShield Backend" python main.py
cd ..

timeout /t 3 /nobreak > nul

echo 📊 Starting React Dashboard...
cd dashboard
start "CyberShield Dashboard" npm run dev
cd ..

echo.
echo ✅ CyberShield System Started!
echo 🌐 Backend: http://localhost:8000
echo 📱 Dashboard: http://localhost:5173
echo 🔧 Extension: Already loaded in Chrome
echo.
pause