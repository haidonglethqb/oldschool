# Original User Request

## 2026-09-16T14:09:28Z

Khởi tạo và tích hợp bộ khung kỹ thuật cơ sở (Baseline Skeleton) bao gồm Cơ sở dữ liệu (Prisma ORM + PostgreSQL), Backend API (Express TypeScript) và Frontend Web (Next.js App Router) cho Hệ thống Quản trị Nhân sự BAHAU - Trường Đại học Kiến trúc Đà Nẵng, bám sát các tài liệu đặc tả kiến trúc đã thống nhất trong docs/.

Working directory: c:\Users\HaiChu\Documents\GitHub\BAHAU
Integrity mode: development

Tham chiếu kỹ thuật:
- docs/architecture/system-overview.md
- docs/architecture/domain-model.md
- docs/requirements/rbac-matrix.md
- docs/requirements/api-standards.md
- docs/requirements/module-01-core-hr-prd.md

## Requirements

### R1. Hoàn thiện Gói Cơ sở Dữ liệu (@bahau/database)
- Xây dựng schema Prisma hoàn chỉnh cho Phân hệ 1 theo tài liệu domain-model.md (User, Session, Role, Permission, RoleAssignment, OrganizationalUnit, Position, Employee, EmploymentAssignment, EmploymentContract, EmploymentEvent, OutboxEvent, AuditEvent).
- Thiết lập tệp dữ liệu mẫu (Seed Data) phản ánh trung thực cơ cấu tổ chức Trường Đại học Kiến trúc Đà Nẵng (Ban Giám hiệu, Khoa Kiến trúc, Khoa Xây dựng, các Bộ môn, Phòng Tổ chức - Hành chính, Phòng Đào tạo) cùng 5 tài khoản mẫu cho 5 nhóm vai trò với mật khẩu băm bảo mật.
- Cung cấp singleton PrismaClient export cho các ứng dụng trong monorepo và script chạy generate/seed thuận tiện.

### R2. Khởi tạo Ứng dụng Backend API (apps/api)
- Xây dựng dịch vụ Express API (TypeScript) với cấu trúc phân tầng rõ ràng (routes, controllers, services, middlewares).
- Tích hợp các middleware bảo mật và quản trị thiết yếu: CORS, Helmet, cookie-parser, Request-Id tracing (UUIDv7) và Centralized Error Handling chuẩn hóa theo api-standards.md.
- Triển khai endpoint kiểm tra sức khỏe `GET /api/v1/health` trả về trạng thái uptime, phiên bản API và kiểm tra kết nối tới cơ sở dữ liệu.

### R3. Khởi tạo Ứng dụng Frontend (apps/web)
- Khởi tạo ứng dụng Next.js (App Router, TypeScript, Tailwind CSS) trong thư mục apps/web.
- Xây dựng giao diện trang chủ cơ bản hiển thị tổng quan hệ thống BAHAU, trạng thái kết nối tới Backend API và điều hướng tới cổng đăng nhập.

## Acceptance Criteria

### Build & Type Verification
- [ ] Gói `@bahau/contracts` và `@bahau/database` được liên kết thành công trong npm workspaces.
- [ ] Lệnh `npm run db:generate` (hoặc lệnh tương đương) sinh thành công Prisma Client không có lỗi cú pháp.
- [ ] Lệnh build TypeScript toàn bộ monorepo thực thi thành công mà không có lỗi kiểu dữ liệu (`npm run build`).

### Backend Verification
- [ ] Ứng dụng Express API khởi động thành công trên cổng cấu hình (mặc định 4000).
- [ ] Gửi yêu cầu HTTP `GET /api/v1/health` nhận về HTTP Status 200 với định dạng JSON chuẩn: `{ "success": true, "data": { "status": "ok", ... } }`.

### Frontend Verification
- [ ] Ứng dụng Next.js khởi động thành công trên cổng cấu hình (mặc định 3000) và render trang giao diện không có lỗi runtime.
