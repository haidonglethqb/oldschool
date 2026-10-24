# Hệ thống Quản lý Kho và Chuỗi Cung Ứng Cửa hàng Thời trang Old School

Hệ thống quản lý tồn kho đa cơ sở theo thời gian thực và điều phối chuỗi cung ứng nội bộ dành cho thương hiệu thời trang **Old School** tại TP. Đà Nẵng (`CS1` Kho tổng Hải Châu, `CS2` Thanh Khê, hỗ trợ mở rộng `CS3` Ngũ Hành Sơn).

Dự án được xây dựng dựa trên đặc tả nghiệp vụ `50K22.3-Nhom09-ChuDe6-BCTD2.docx` và tài liệu chuẩn hóa hệ thống [`docs/System.md`](docs/System.md), đáp ứng đầy đủ **53 Use Cases** (`UC-1` đến `UC-7.5`) và **10 Kịch bản nghiệm thu (User Acceptance Scenarios)**.

---

## 1. Công nghệ sử dụng (Tech Stack)
- **Ngôn ngữ & Framework**: Python 3.12 + Django 5.2 LTS
- **Cơ sở dữ liệu**: SQLite (mặc định môi trường dev — chạy ngay không cần cài đặt DB rời) hoặc PostgreSQL 16 (hỗ trợ `SELECT ... FOR UPDATE`, `CheckConstraint`, `UniqueConstraint`, khóa chống trùng lặp `idempotency_key`)
- **Giao diện người dùng**: Django Templates (SSR) + Bootstrap 5.3 + Chart.js 4.4 + Old School Figma Theme (`#4A2511`, `#F3E9DC`, `#DEC2A8`)
- **Xử lý bảng tính**: OpenPyXL (`.xlsx` upload validation, preview & safe export chống Formula Injection)
- **Kiểm thử tự động**: Pytest + `pytest-django` (bao gồm kiểm thử tương tranh `TransactionTestCase` trên PostgreSQL 16)

---

## 2. Cấu trúc thư mục dự án
```text
oldschool/
├── setup.bat                   # [1-Click Windows] Script tự động cài đặt & chạy từ A-Z
├── setup.ps1                   # Core PowerShell script xử lý cài đặt tự động
├── start.bat                   # [Quick Start] Script bật nhanh Web Server cho những lần sau
├── setup.sh                    # [1-Click macOS/Linux/GitBash] Script tự động cài đặt từ A-Z
├── manage.py                   # Entrypoint quản trị của Django
├── .env.example                # File mẫu cấu hình môi trường (SQLite / PostgreSQL)
├── config/                     # Cấu hình Django (settings, urls, wsgi, asgi)
├── apps/
│   ├── branches/               # Quản lý Cơ sở (CoSo: CS1 Kho tổng, CS2, mở rộng CS3)
│   ├── accounts/               # Người dùng, xác thực & phân quyền RBAC 3 vai trò
│   ├── catalog/                # Danh mục Sản phẩm (SanPham) & Biến thể SKU (BienThe)
│   ├── inventory/              # Tồn kho (TonKho), Sổ cái (StockMovement), Excel & Seed
│   ├── purchasing/             # Nhà cung cấp (NhaCungCap) & Phiếu nhập kho (PhieuNhapKho)
│   ├── sales_outbound/         # Yêu cầu xuất & Phiếu xuất hàng bán (PhieuXuatHangBan)
│   ├── transfers/              # Điều chuyển nội bộ 2 bước (PhieuDieuChuyen)
│   ├── stocktakes/             # Kiểm kê kho & đối chiếu chênh lệch (KiemKe)
│   ├── reports/                # Báo cáo Xuất-Nhập-Tồn động & biểu đồ (BaoCao)
│   └── notifications/          # Trung tâm Thông báo & Cảnh báo tồn kho thấp (ThongBao)
├── templates/                  # Giao diện tiếng Việt chuẩn thiết kế Figma Old School
├── static/                     # CSS & JS của hệ thống
├── sample_data/excel/          # Các file Excel (.xlsx) mẫu phục vụ tải lên
├── tests/                      # Bộ kiểm thử tự động toàn diện (Unit, Integration, Concurrency)
└── docs/                       # Tài liệu kiến trúc, CSDL, phân quyền, kiểm thử & hướng dẫn demo
```

---

## 3. Hướng dẫn cài đặt và khởi chạy nhanh

### Cách 1: Cài đặt tự động từ A-Z bằng 1 script duy nhất *(Khuyên dùng cho người mới clone)*

Người mới chỉ cần `git clone` dự án về và chạy **1 lệnh duy nhất** (hoặc nhấp đúp chuột vào file `setup.bat` trong thư mục dự án). Script sẽ tự động làm toàn bộ 6 bước:
1. Tự dò tìm Python 3 trên máy và khởi tạo môi trường ảo `.venv` (nếu chưa có).
2. Tự cài đặt toàn bộ thư viện trong `requirements.txt`.
3. Tự tạo file `.env` từ `.env.example` (mặc định dùng SQLite để chạy ngay lập tức).
4. Tự kiểm tra và dọn sạch cơ sở dữ liệu nếu phát hiện dữ liệu lệch phiên bản.
5. Tự chạy `migrate` và nạp dữ liệu mẫu chuẩn (`seed_oldschool`).
6. In danh sách tài khoản Demo và khởi chạy Web Server tại `http://127.0.0.1:8000/`.

#### Trên Windows (PowerShell hoặc CMD):
```powershell
git clone <url-repo>
cd oldschool
.\setup.bat
```

**Bảng các lệnh & tham số tiện ích trên Windows:**

| Mục đích sử dụng | Lệnh thực thi |
|---|---|
| **Cài đặt chuẩn từ A-Z (Mặc định 2 cơ sở CS1 & CS2)** + bật Server | `.\setup.bat` |
| **Cài đặt bản mở rộng 3 cơ sở (CS1, CS2, CS3)** + bật Server | `.\setup.bat -Branches 3` |
| **Xóa sạch DB cũ, làm mới lại từ đầu (2 cơ sở)** + bật Server | `.\setup.bat -ResetDb` |
| **Xóa sạch DB cũ và tạo lại bản 3 cơ sở** + bật Server | `.\setup.bat -Branches 3 -ResetDb` |
| **Chỉ cài đặt & nạp dữ liệu mẫu (không tự bật Server)** | `.\setup.bat -NoServer` |
| **Bật nhanh Web Server ở những lần mở máy tiếp theo** | `.\start.bat` |

#### Trên macOS / Linux / Git Bash:
```bash
chmod +x setup.sh
./setup.sh                  # Mặc định 2 cơ sở + bật Server
./setup.sh --branches 3     # Bản mở rộng 3 cơ sở
./setup.sh --reset-db       # Xóa DB cũ, tạo mới từ đầu
./setup.sh --no-server      # Chỉ cài đặt, không bật Server
```

---

### Cách 2: Cài đặt thủ công từng bước

#### Bước 1: Tạo môi trường ảo và cài đặt thư viện
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

#### Bước 2: Cấu hình biến môi trường (`.env`)
Sao chép `.env.example` thành `.env`. Hệ thống hỗ trợ cả SQLite (chạy ngay không cần cài đặt DB) lẫn PostgreSQL:
```powershell
Copy-Item .env.example .env
```

Nội dung `.env` mặc định:
```env
DEBUG=True
SECRET_KEY=django-insecure-oldschool-dev-secret-key-change-in-production
ALLOWED_HOSTS=127.0.0.1,localhost,testserver

# Chọn SQLite (chạy mặc định):
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# Hoặc PostgreSQL 16:
# DB_ENGINE=django.db.backends.postgresql
# DB_NAME=oldschool_db
# DB_USER=postgres
# DB_PASSWORD=postgres
# DB_HOST=127.0.0.1
# DB_PORT=5432
```

#### Bước 3: Chạy Migration và khởi tạo dữ liệu mẫu (2 phiên bản seed)

1. **Bản chuẩn 2 cơ sở (Mặc định theo đặc tả System.md §6.2 — CS1 Kho tổng & CS2 Thanh Khê, 5 tài khoản):**
```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_oldschool
```

2. **Bản mở rộng 3 cơ sở (Thêm CS3 Ngũ Hành Sơn, 7 tài khoản):**
```powershell
.\.venv\Scripts\python.exe manage.py seed_oldschool_3b
# Hoặc: .\.venv\Scripts\python.exe manage.py seed_oldschool --branches 3
```

> **Mẹo xóa dữ liệu thủ công để reset về bản 2 cơ sở sạch hoàn toàn (SQLite):**
> ```powershell
> Remove-Item db.sqlite3 -Force
> .\.venv\Scripts\python.exe manage.py migrate
> .\.venv\Scripts\python.exe manage.py seed_oldschool
> ```

#### Bước 4: Khởi chạy Web Server
```powershell
.\.venv\Scripts\python.exe manage.py runserver 8000
```
Truy cập ứng dụng tại: `http://127.0.0.1:8000/`

---

## 4. Danh sách tài khoản Demo (Mật khẩu chung: `OldSchool@123`)

### A. Phiên bản mặc định 2 cơ sở (`CS1` & `CS2` — 5 tài khoản)
| Vai trò | Tên đăng nhập | Cơ sở phụ trách | Quyền hạn chính |
|---|---|---|---|
| **Chủ cửa hàng (Admin)** | `admin_owner` | Toàn hệ thống (`ALL`) | Xem mọi cơ sở, phê duyệt Phiếu nhập kho (`UC-4.9`), phê duyệt Biên bản kiểm kê (`UC-6.10`), xem báo cáo toàn chuỗi |
| **Quản lý CS1 (Kho tổng)** | `manager_cs1` | CS1 — Hải Châu (Kho tổng) | Lập phiếu nhập kho từ NCC, xuất bán tại CS1, xuất điều chuyển cho CS2, kiểm kê & báo cáo CS1 |
| **Quản lý CS2** | `manager_cs2` | CS2 — Thanh Khê | Quản lý tồn kho CS2, lập & ghi nhận phiếu xuất bán CS2, yêu cầu/nhận điều chuyển, kiểm kê & báo cáo CS2 |
| **Nhân viên bán hàng CS1** | `staff_cs1` | CS1 — Hải Châu | Tra cứu hàng hóa & tồn kho CS1, gửi yêu cầu xuất hàng bán, xem/in phiếu xuất bán CS1 |
| **Nhân viên bán hàng CS2** | `staff_cs2` | CS2 — Thanh Khê | Tra cứu hàng hóa & tồn kho CS2, gửi yêu cầu xuất hàng bán, xem/in phiếu xuất bán CS2 |

### B. Tài khoản bổ sung khi khởi tạo bản mở rộng 3 cơ sở (`seed_oldschool_3b`)
| Vai trò | Tên đăng nhập | Cơ sở phụ trách | Quyền hạn chính |
|---|---|---|---|
| **Quản lý CS3** | `manager_cs3` | CS3 — Ngũ Hành Sơn | Quản lý tồn kho CS3, lập & ghi nhận phiếu xuất bán CS3, yêu cầu/nhận điều chuyển, kiểm kê & báo cáo CS3 |
| **Nhân viên bán hàng CS3** | `staff_cs3` | CS3 — Ngũ Hành Sơn | Tra cứu hàng hóa & tồn kho CS3, gửi yêu cầu xuất hàng bán, xem/in phiếu xuất bán CS3 |

---

## 5. Chạy bộ kiểm thử tự động (Automated Tests)
```powershell
.\.venv\Scripts\pytest.exe -v
```

---

## 6. Danh mục tài liệu kỹ thuật (`docs/`)
- [`docs/REQUIREMENTS_MATRIX.md`](docs/REQUIREMENTS_MATRIX.md): Ma trận ánh xạ 53 Use Cases sang Module, URL, Service, Template và Test.
- [`docs/ERD_AUDIT.md`](docs/ERD_AUDIT.md): Báo cáo đối chiếu và chuẩn hóa sơ đồ ERD / Lược đồ quan hệ.
- [`docs/DECISIONS.md`](docs/DECISIONS.md): Nhật ký giải quyết các điểm mâu thuẫn trong tài liệu đặc tả gốc (`DEC-01` đến `DEC-08`).
- [`docs/DATABASE_DESIGN.md`](docs/DATABASE_DESIGN.md): Thiết kế chi tiết các bảng CSDL PostgreSQL, ràng buộc toàn vẹn và chỉ mục.
- [`docs/PERMISSIONS.md`](docs/PERMISSIONS.md): Ma trận phân quyền RBAC và cơ chế cô lập dữ liệu theo cơ sở (`Branch Isolation`).
- [`docs/STOCK_WORKFLOWS.md`](docs/STOCK_WORKFLOWS.md): Máy trạng thái (State Machines) và quy tắc hạch toán sổ cái tồn kho (`StockMovement`).
- [`docs/TEST_RESULTS.md`](docs/TEST_RESULTS.md): Báo cáo kết quả kiểm thử tự động và nghiệm thu 10 kịch bản cốt lõi.
- [`docs/DEMO_GUIDE.md`](docs/DEMO_GUIDE.md): Kịch bản trình diễn (Demo Walkthrough) từng bước cho hội đồng nghiệm thu.
