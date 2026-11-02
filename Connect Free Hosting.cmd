@echo off
setlocal
cd /d "%~dp0online_service"
set "SCANNER_NODE=C:\Users\HP\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
echo Connect the official Cloudflare Wrangler deployment tool.
echo Open the printed link yourself. Its domain must be dash.cloudflare.com.
echo Review access to account info, user info and Workers Scripts in your account.
echo This does not approve scanner users or choose a paid hosting plan.
echo.
"%SCANNER_NODE%" "%~dp0online_service\node_modules\wrangler\bin\wrangler.js" login --browser=false --scopes account:read user:read workers_scripts:write
if errorlevel 1 (
  echo.
  echo Sign-in did not finish. No scanner service was deployed by this launcher.
) else (
  echo.
  echo Cloudflare sign-in completed. Return to the chat so deployment can continue.
)
pause
