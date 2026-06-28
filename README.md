# Construction Project Management Platform

Fullstack platform for construction project operations — connects owners, construction companies, contractors, site managers, and workers in a single workflow. FastAPI backend + React (TypeScript) frontend.

## What this project covers

- Authentication with JWT access and refresh tokens (with `/refresh` rotation and token-type separation)
- Role-based project membership and access control
- Project lifecycle management from planning to completion
- Work item and task breakdown for site execution
- Site progress updates and photo reporting
- Change order handling and approval flow
- Issue tracking and resolution
- Quantity acceptance and payment tracking
- Cost logging and project-level dashboards
- Portfolio-level reporting across accessible projects
- Audit trail for important operational actions

## Technical stack

Backend:
- FastAPI + Uvicorn (ASGI)
- SQLModel (SQLAlchemy + Pydantic) — SQLite cho dev, PostgreSQL-ready qua `DATABASE_URL`
- JWT auth (python-jose) với access + refresh token, bcrypt hashing
- Pydantic v2 validation
- pytest + httpx (in-memory SQLite)

Frontend:
- React 18 + TypeScript + Vite
- Tailwind CSS
- React Router (routing + bảo vệ route theo đăng nhập)
- Axios (interceptor tự gắn token + tự refresh khi 401)

Vận hành:
- Docker + docker-compose
- Swagger UI / ReDoc (tự sinh)

## How it is positioned

The codebase is written in a backend-engineering style aligned with the user's CV experience:

- API-first design
- RBAC-oriented workflow control
- Operational auditability
- Dashboard and reporting endpoints for business visibility
- Clear model separation for projects, work items, issues, finance, and approvals

## Project structure

```
main.py                  # khởi tạo app + include_router (gọn, không chứa route nghiệp vụ)
app/
  db.py                  # engine + session
  models.py              # SQLModel tables + Pydantic schemas + enums
  security.py            # JWT, hashing, RBAC (project role + business role)
  services.py            # business logic: dashboard, report, WBS tree, accessible projects
  routers/
    auth.py              # /register, /token
    projects.py          # projects + members
    workitems.py         # work items (WBS), tasks, progress
    finance.py           # change orders, costs, payments
    site.py              # site reports, issues, acceptances, photos
    reports.py           # dashboards, portfolio, activity report, audit logs
seed.py                  # dữ liệu mẫu
tests/                   # pytest: auth + phân quyền + WBS
frontend/                # React + TS + Vite + Tailwind
  src/
    api.ts               # axios client + auto refresh token
    types.ts             # types khớp schema backend
    roles.ts             # nhãn vai trò + ma trận phân quyền (khớp security.py)
    context/AuthContext  # trạng thái đăng nhập
    components/          # Layout, Modal, UI primitives
    pages/               # Login, Portfolio, Projects, ProjectDetail
    pages/tabs/          # Dashboard, WBS, Tasks, Finance, Site, Members, Audit
```

## Run locally

Backend:

1. `pip install -r requirements.txt`
2. `python seed.py` (tạo 5 user theo 5 vai trò + 1 project mẫu đủ dữ liệu)
3. `uvicorn main:app --reload` → API tại `http://localhost:8000`, docs tại `/docs`
4. `pytest` để chạy test

Frontend:

1. `cd frontend && npm install`
2. `npm run dev` → giao diện tại `http://localhost:5173`
3. Đăng nhập bằng một trong các tài khoản demo bên dưới

Mặc định frontend gọi backend ở `http://localhost:8000`; đổi qua biến `VITE_API_URL`. Backend cho phép CORS từ `http://localhost:5173` (đổi qua `CORS_ORIGINS`).

### Chạy bằng Docker (một lệnh)

Cần Docker Desktop đang chạy:

```
docker compose up --build
```

- Backend: `http://localhost:8000` (tự seed dữ liệu mẫu khi khởi động)
- Frontend: `http://localhost:8080`

Backend lưu DB vào volume `./data`, ảnh upload vào `./uploads`. Đặt `SECRET_KEY` qua biến môi trường để không dùng giá trị mặc định.

Tài khoản demo (mật khẩu chung `password123`, dùng email làm username khi Authorize):

| Email | Vai trò nghiệp vụ |
|---|---|
| homeowner@example.com | Chủ đầu tư (homeowner) |
| company@example.com | Công ty xây dựng (construction_company) |
| contractor@example.com | Nhà thầu (contractor) |
| sitemanager@example.com | Quản lý công trình (site_manager) |
| worker@example.com | Công nhân (worker) |

## Scope và quyết định thiết kế

Đây là bản backend hoàn thiện trong thời gian giới hạn, nên tôi ưu tiên chiều sâu nghiệp vụ thay vì làm dàn trải. Những quyết định chính:

- **Hai tầng phân quyền.** Vai trò nghiệp vụ ở cấp hệ thống (`UserRole`: 5 bên tham gia) tách khỏi vai trò cộng tác ở cấp dự án (`owner/manager/member`). Lý do: một công ty xây dựng có thể là "manager" ở dự án này nhưng "member" ở dự án khác — vai trò nghiệp vụ là cố định, vai trò trong dự án thì theo ngữ cảnh.
- **Ma trận phân quyền nghiệp vụ.** Tập trung tại `app/security.py` để dễ rà soát và giải trình, phản ánh "ai được làm gì trên công trường":
  - Giao việc (tạo task): công ty xây dựng, nhà thầu, quản lý công trình.
  - Nghiệm thu khối lượng: công ty xây dựng, quản lý công trình.
  - Duyệt phát sinh (change order): chủ đầu tư, công ty xây dựng — vì là quyết định tài chính.
  - Tất toán thanh toán: chủ đầu tư, công ty xây dựng — bên chi tiền.
  - Với các hành động đã có cổng vai trò nghiệp vụ, cổng cấp dự án chỉ kiểm tra "có thuộc dự án không"; vai trò nghiệp vụ mới là cổng quyết định.
- **Hạng mục dạng cây (WBS).** `WorkItem` tự tham chiếu qua `parent_id`, có endpoint `/workitems/tree` trả về cấu trúc lồng nhau — phản ánh đúng cách công trình được phân rã (phần móng → đào đất, đổ bê tông...).
- **Khép vòng tiến độ.** Cập nhật tiến độ đạt 100% sẽ tự đánh dấu hạng mục hoàn thành (`is_completed`).
- **Audit log.** Mọi thao tác nghiệp vụ quan trọng đều ghi vết, phục vụ yêu cầu minh bạch giữa các bên.
- **Tổ chức code.** Route tách theo domain thành các router riêng; `main.py` chỉ còn lắp ráp. Logic dùng chung (lấy danh sách project truy cập được) gom về `services.py` thay vì lặp lại.
- **Phân quyền hiển thị ở frontend.** UI ẩn/hiện nút theo cùng ma trận vai trò của backend (`frontend/src/roles.ts` khớp `app/security.py`) — ví dụ chỉ chủ đầu tư/công ty xây dựng thấy nút "Duyệt phát sinh". Backend vẫn là nơi chốt quyền cuối cùng; frontend chỉ cải thiện trải nghiệm.

Những phần tôi chủ động để lại cho vòng sau (đã có hướng rõ):

- **Migrations.** Hiện dùng `create_all` cho nhanh; production sẽ chuyển sang Alembic.
- **Quản lý cấu hình tập trung.** `SECRET_KEY` và `DATABASE_URL` đã đọc từ biến môi trường; bước sau gom về một module settings bằng pydantic-settings.
- **Hiển thị ảnh thật + lọc/tìm kiếm nâng cao.** Frontend hiện liệt kê ảnh theo tên file; bước sau phục vụ ảnh tĩnh và thêm bộ lọc/sắp xếp cho các danh sách.