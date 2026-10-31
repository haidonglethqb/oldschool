#!/usr/bin/env bash
# ==============================================================================
# Script khởi chạy nhanh Web Server cho Old School (macOS / Linux / Git Bash)
# ==============================================================================
set -e
cd "$(dirname "$0")"

if [ -f ".venv/Scripts/python.exe" ]; then
  VENV_PY=".venv/Scripts/python.exe"
elif [ -f ".venv/bin/python" ]; then
  VENV_PY=".venv/bin/python"
else
  echo "[!] Chưa tìm thấy môi trường .venv. Đang chạy setup.sh tự động..."
  ./setup.sh
  exit $?
fi

echo "======================================================================"
echo "  OLD SCHOOL - ĐANG CHẠY WEB SERVER TẠI: http://127.0.0.1:8000/"
echo "  (Nhấn Ctrl+C để dừng server)"
echo "======================================================================"

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://127.0.0.1:8000/" >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then
  open "http://127.0.0.1:8000/" >/dev/null 2>&1 &
fi

"$VENV_PY" manage.py runserver 8000
