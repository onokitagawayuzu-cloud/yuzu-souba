@echo off
chcp 65001 > nul
cd /d "%~dp0"
rem GitHub に毎日たまっているデータを受け取ってから開く(2026-11-04)
rem 手元でデータを取り直すと、2台の自動の受け取りが止まるため、ここでは取り直さない
echo GitHub から最新のデータを受け取っています...
git pull --ff-only origin main
if errorlevel 1 (
  echo.
  echo 受け取れませんでした。上の英語の文を Claude に貼り付けてください。
  pause
  exit /b 1
)
start "" "web\index.html"
