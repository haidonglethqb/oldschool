#!/usr/bin/env bash
# ==============================================================================
# Script cài đặt và khởi chạy tự động từ A-Z cho Old School (macOS / Linux / Git Bash)
# Cách dùng:
#   ./setup.sh                  (Mặc định: 2 cơ sở CS1 & CS2 + bật server)
#   ./setup.sh --branches 3     (Bản mở rộng: 3 cơ sở CS1, CS2, CS3)
#   ./setup.sh --reset-db       (Xóa db.sqlite3 cũ và tạo mới từ đầu)
#   ./setup.sh --no-server      (Chỉ cài đặt, không bật runserver)
# ==============================================================================
set -e

BRANCHES=2
RESET_DB=0
NO_SERVER=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --branches|-b)
      BRANCHES="$2"
      shift 2
      ;;
    --reset-db|-r)
      RESET_DB=1
      shift
      ;;
    --no-server|-n)
      NO_SERVER=1
      shift
      ;;
    *)
      shift
      ;;
  esac
done

cd "$(dirname "$0")"

echo "======================================================================"
echo "   OLD SCHOOL - THIẾT LẬP HỆ THỐNG TỰ ĐỘNG TỪ A ĐẾN Z"
echo "======================================================================"

# 1. Tìm Python 3 & tạo .venv
echo "[1/6] Kiểm tra môi trường Python & Virtual Environment (.venv)..."
if [ ! -d ".venv" ]; then
  if command -v python3 >/dev/null 2>&1; then
    PY_CMD="python3"
  elif command -v python >/dev/null 2>&1; then
    PY_CMD="python"
  else
    echo "[LỖI] Không tìm thấy Python 3! Vui lòng cài đặt Python 3.10+ trước."
    exit 1
  fi
  echo "  -> Đang tạo .venv bằng $PY_CMD..."
  "$PY_CMD" -m venv .venv
fi

if [ -f ".venv/Scripts/python.exe" ]; then
  VENV_PY=".venv/Scripts/python.exe"
else
  VENV_PY=".venv/bin/python"
fi

# 2. Cài đặt thư viện
echo "[2/6] Cài đặt thư viện từ requirements.txt..."
"$VENV_PY" -m pip install --disable-pip-version-check -r requirements.txt

# 3. Tạo file .env nếu chưa có
echo "[3/6] Kiểm tra file cấu hình .env..."
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "  -> Đã tự động tạo file .env từ .env.example."
fi

# 4. Kiểm tra và làm sạch DB nếu cần
echo "[4/6] Kiểm tra trạng thái Cơ sở dữ liệu..."
if [ "$RESET_DB" -eq 1 ] && [ -f "db.sqlite3" ]; then
  rm -f db.sqlite3
  echo "  -> Đã xóa db.sqlite3 cũ."
fi

# 5. Migrate & Seed
echo "[5/6] Chạy Django Migrations và khởi tạo dữ liệu mẫu ($BRANCHES cơ sở)..."
"$VENV_PY" manage.py migrate
if [ "$BRANCHES" -eq 3 ]; then
  "$VENV_PY" manage.py seed_oldschool_3b
else
  "$VENV_PY" manage.py seed_oldschool
fi

echo ""
echo "======================================================================"
echo "   HOÀN TẤT CÀI ĐẶT! HỆ THỐNG ĐÃ SẴN SÀNG SỬ DỤNG"
echo "   URL truy cập   : http://127.0.0.1:8000/"
echo "   Mật khẩu chung : OldSchool@123"
echo "   Tài khoản Demo : admin_owner | manager_cs1 | manager_cs2 | staff_cs1 | staff_cs2"
echo "======================================================================"
echo ""

if [ "$NO_SERVER" -eq 0 ]; then
  echo "[6/6] Đang khởi động Web Server tại http://127.0.0.1:8000/ ..."
  "$VENV_PY" manage.py runserver 8000
fi
