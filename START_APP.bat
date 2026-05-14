@echo off
setlocal

set "ROOT=%~dp0"
set "API_DIR=%ROOT%api"
set "FRONTEND_DIR=%ROOT%frontend"
set "API_PYTHON=%API_DIR%\.venv\Scripts\python.exe"

if not exist "%ROOT%.env" (
    echo Missing .env file in project root.
    echo Copy .env.example to .env and add your OpenAI API key first.
    pause
    exit /b 1
)

findstr /b /c:"APP_LOGIN_USERNAME=" "%ROOT%.env" >nul 2>nul
if errorlevel 1 (
    echo APP_LOGIN_USERNAME is missing from .env.
    echo Add APP_LOGIN_USERNAME and APP_LOGIN_PASSWORD to .env before starting.
    pause
    exit /b 1
)

findstr /b /c:"APP_LOGIN_PASSWORD=" "%ROOT%.env" >nul 2>nul
if errorlevel 1 (
    echo APP_LOGIN_PASSWORD is missing from .env.
    echo Add APP_LOGIN_USERNAME and APP_LOGIN_PASSWORD to .env before starting.
    pause
    exit /b 1
)

if not exist "%API_DIR%\pyproject.toml" (
    echo Backend folder not found: %API_DIR%
    pause
    exit /b 1
)

if not exist "%FRONTEND_DIR%\package.json" (
    echo Frontend folder not found: %FRONTEND_DIR%
    pause
    exit /b 1
)

where uv >nul 2>nul
if errorlevel 1 (
    echo uv is not available in PATH.
    echo Install it with: pip install uv
    pause
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo npm is not available in PATH.
    echo Install Node.js 18+ first.
    pause
    exit /b 1
)

if not exist "%API_PYTHON%" (
    echo Backend virtual environment not found. Installing backend dependencies...
    pushd "%API_DIR%"
    uv sync
    if errorlevel 1 (
        echo Backend dependency installation failed.
        popd
        pause
        exit /b 1
    )
    popd
)

if not exist "%API_PYTHON%" (
    echo Backend Python not found after setup: %API_PYTHON%
    pause
    exit /b 1
)

if not exist "%FRONTEND_DIR%\node_modules" (
    echo Frontend dependencies not found. Installing frontend dependencies...
    pushd "%FRONTEND_DIR%"
    npm install
    if errorlevel 1 (
        echo Frontend dependency installation failed.
        popd
        pause
        exit /b 1
    )
    popd
)

echo Selecting free random ports...
for /f "tokens=1,2" %%a in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "$l1=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,0); $l1.Start(); $api=$l1.LocalEndpoint.Port; $l2=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,0); $l2.Start(); $front=$l2.LocalEndpoint.Port; $l1.Stop(); $l2.Stop(); Write-Output ($api.ToString() + ' ' + $front.ToString())"') do (
    set "API_PORT=%%a"
    set "FRONTEND_PORT=%%b"
)

if not defined API_PORT (
    echo Failed to select a backend port.
    pause
    exit /b 1
)

if not defined FRONTEND_PORT (
    echo Failed to select a frontend port.
    pause
    exit /b 1
)

set "API_URL=http://127.0.0.1:%API_PORT%"
set "FRONTEND_URL=http://127.0.0.1:%FRONTEND_PORT%"
set "VITE_API_URL=%API_URL%"

echo Selected backend port: %API_PORT%
echo Selected frontend port: %FRONTEND_PORT%
echo Frontend API target: %VITE_API_URL%

echo Starting PowerBI Vision backend on %API_URL% ...
start "PowerBI Vision Backend" /D "%API_DIR%" cmd /k ""%API_PYTHON%" -m uvicorn src.main:app --reload --host 127.0.0.1 --port %API_PORT%"

echo Waiting for backend health check...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$deadline=(Get-Date).AddSeconds(45); do { try { $r=Invoke-WebRequest -UseBasicParsing '%API_URL%/health' -TimeoutSec 2; if ($r.StatusCode -lt 500) { exit 0 } } catch {}; Start-Sleep -Seconds 1 } while ((Get-Date) -lt $deadline); exit 1"
if errorlevel 1 (
    echo Backend did not respond at %API_URL%/health.
    echo Check the PowerBI Vision Backend window for errors.
    pause
    exit /b 1
)

echo Starting PowerBI Vision frontend on %FRONTEND_URL% ...
start "PowerBI Vision Frontend" /D "%FRONTEND_DIR%" cmd /k "echo VITE_API_URL=%VITE_API_URL% && call npm.cmd run dev -- --host 127.0.0.1 --port %FRONTEND_PORT% --strictPort"

echo Waiting for frontend dev server...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$deadline=(Get-Date).AddSeconds(45); do { try { $r=Invoke-WebRequest -UseBasicParsing '%FRONTEND_URL%' -TimeoutSec 2; if ($r.StatusCode -lt 500) { exit 0 } } catch {}; Start-Sleep -Seconds 1 } while ((Get-Date) -lt $deadline); exit 1"
if errorlevel 1 (
    echo Frontend did not respond at %FRONTEND_URL%.
    echo Check the PowerBI Vision Frontend window for errors.
    pause
    exit /b 1
)

echo.
echo Backend:  %API_URL%
echo API Docs: %API_URL%/docs
echo Frontend: %FRONTEND_URL%
echo.
echo Opening the app...
start "" "%FRONTEND_URL%"

endlocal
