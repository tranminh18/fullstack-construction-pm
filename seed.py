"""
Seed dữ liệu mẫu để demo nhanh trên Swagger UI.

Chạy:  python seed.py
Sau đó đăng nhập tại /docs bằng bất kỳ tài khoản nào bên dưới (mật khẩu: password123).

Script idempotent: nếu các user mẫu đã tồn tại thì bỏ qua, không tạo trùng.
"""
from datetime import datetime, timedelta
import sys

from sqlmodel import Session, select

# Windows console mặc định cp1252 không in được tiếng Việt -> ép UTF-8.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.db import create_db_and_tables, engine
from app.models import (
    AcceptanceRecord,
    ChangeOrder,
    CostEntry,
    Issue,
    PaymentRecord,
    Project,
    ProjectMember,
    ProjectStatus,
    SiteReport,
    Task,
    User,
    UserRole,
    WorkItem,
)
from app.security import get_password_hash

DEFAULT_PASSWORD = "password123"

# (email, họ tên, vai trò nghiệp vụ, vai trò trong project)
USERS = [
    ("homeowner@example.com", "Chị Lan (Chủ đầu tư)", UserRole.homeowner, "owner"),
    ("company@example.com", "Cty XD Hòa Bình", UserRole.construction_company, "manager"),
    ("contractor@example.com", "Nhà thầu Minh Phát", UserRole.contractor, "manager"),
    ("sitemanager@example.com", "Anh Tuấn (QL công trình)", UserRole.site_manager, "member"),
    ("worker@example.com", "Anh Hùng (Công nhân)", UserRole.worker, "member"),
]


# Đặc tả các project bổ sung, phủ đủ 4 trạng thái vòng đời để demo portfolio/báo cáo.
_ADDITIONAL_PROJECTS = [
    {
        "name": "Biệt thự sân vườn - Thảo Điền",
        "description": "Dự án đang lập kế hoạch, chưa khởi công.",
        "status": ProjectStatus.planning,
        "start_offset": 15, "end_offset": 300, "budget": 5_000_000_000,
        "work_items": [
            {"name": "Thiết kế kiến trúc", "budget": 300_000_000, "progress": 0.0},
            {"name": "Xin phép xây dựng", "budget": 50_000_000, "progress": 0.0},
        ],
        "tasks": [
            {"title": "Hoàn thiện bản vẽ thi công", "status": "todo", "due_offset": 10, "priority": 3},
        ],
        "costs": [{"category": "design", "amount": 120_000_000, "note": "Phí thiết kế đợt 1"}],
        "payments": [{"payee": "Cty thiết kế An Cư", "amount": 120_000_000, "status": "pending"}],
        "reports": ["Đang chờ giấy phép xây dựng, chưa triển khai hiện trường."],
        "issues": [],
        "change_orders": [],
    },
    {
        "name": "Văn phòng cho thuê - Quận 1",
        "description": "Dự án đang thi công nhưng đã trễ tiến độ.",
        "status": ProjectStatus.delayed,
        "start_offset": -90, "end_offset": -10, "budget": 8_000_000_000,
        "work_items": [
            {"name": "Phần móng", "budget": 1_500_000_000, "progress": 100.0, "accepted": True},
            {"name": "Phần thân", "budget": 4_000_000_000, "progress": 55.0},
            {"name": "Hoàn thiện", "budget": 2_000_000_000, "progress": 5.0},
        ],
        "tasks": [
            {"title": "Đổ sàn tầng 5", "status": "in_progress", "due_offset": -3, "priority": 3},
            {"title": "Lắp đặt thang máy", "status": "todo", "due_offset": 20, "priority": 2},
        ],
        "costs": [
            {"category": "materials", "amount": 2_100_000_000, "note": "Bê tông, thép"},
            {"category": "labor", "amount": 900_000_000, "note": "Nhân công phần thân"},
        ],
        "payments": [
            {"payee": "Nhà cung cấp bê tông Lê Phan", "amount": 1_500_000_000, "status": "paid"},
            {"payee": "Đội thi công phần thân", "amount": 600_000_000, "status": "pending"},
        ],
        "reports": [
            "Mưa kéo dài làm chậm tiến độ đổ sàn tầng 4-5.",
            "Đã bổ sung nhân công ca đêm để bù tiến độ.",
        ],
        "issues": [
            {"title": "Thiếu hụt vật tư thép", "severity": "high", "status": "resolved"},
            {"title": "Chậm bàn giao mặt bằng tầng 6", "severity": "medium", "status": "open"},
        ],
        "change_orders": [
            {"title": "Phát sinh chống thấm tầng hầm", "amount": 250_000_000, "status": "approved"},
        ],
    },
    {
        "name": "Nhà xưởng - KCN Long Hậu",
        "description": "Dự án đã hoàn thành và nghiệm thu bàn giao.",
        "status": ProjectStatus.completed,
        "start_offset": -200, "end_offset": -20, "budget": 6_000_000_000,
        "work_items": [
            {"name": "Nền móng nhà xưởng", "budget": 2_000_000_000, "progress": 100.0, "accepted": True},
            {"name": "Khung thép mái", "budget": 2_500_000_000, "progress": 100.0, "accepted": True},
            {"name": "Hệ thống điện nước", "budget": 1_500_000_000, "progress": 100.0, "accepted": True},
        ],
        "tasks": [
            {"title": "Bàn giao công trình", "status": "done", "due_offset": -20, "priority": 3},
        ],
        "costs": [
            {"category": "materials", "amount": 3_500_000_000, "note": "Kết cấu thép, bê tông"},
            {"category": "labor", "amount": 1_800_000_000, "note": "Toàn bộ nhân công"},
        ],
        "payments": [
            {"payee": "Tổng thầu cơ điện", "amount": 1_500_000_000, "status": "paid"},
            {"payee": "Nhà cung cấp kết cấu thép", "amount": 2_500_000_000, "status": "paid"},
        ],
        "reports": ["Đã nghiệm thu toàn bộ và bàn giao cho chủ đầu tư."],
        "issues": [
            {"title": "Điều chỉnh độ dốc mái thoát nước", "severity": "low", "status": "resolved"},
        ],
        "change_orders": [
            {"title": "Nâng cấp hệ thống PCCC", "amount": 400_000_000, "status": "approved"},
        ],
    },
]


def get_or_create_users(session: Session) -> dict[UserRole, User]:
    users: dict[UserRole, User] = {}
    for email, full_name, role, _ in USERS:
        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            user = User(
                email=email,
                full_name=full_name,
                role=role,
                hashed_password=get_password_hash(DEFAULT_PASSWORD),
            )
            session.add(user)
            session.commit()
            session.refresh(user)
        users[role] = user
    return users


def seed():
    create_db_and_tables()
    with Session(engine) as session:
        users = get_or_create_users(session)
        owner = users[UserRole.homeowner]

        existing = session.exec(
            select(Project).where(Project.name == "Nhà phố 3 tầng - Quận 7")
        ).first()
        if existing:
            print("Project chính đã tồn tại, bỏ qua. (project_id =", existing.id, ")")
            seed_additional_projects(session, users)
            _print_credentials()
            return

        now = datetime.utcnow()
        project = Project(
            name="Nhà phố 3 tầng - Quận 7",
            description="Công trình nhà phố mẫu để demo nền tảng quản trị thi công.",
            start_date=now - timedelta(days=30),
            end_date=now + timedelta(days=120),
            budget=2_500_000_000,
            status=ProjectStatus.active,
            owner_id=owner.id,
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        # Gán các bên còn lại vào project theo vai trò project
        for email, _, role, project_role in USERS:
            user = users[role]
            if user.id == owner.id:
                project_role = "owner"
            session.add(
                ProjectMember(project_id=project.id, user_id=user.id, role=project_role)
            )
        session.commit()

        # WBS cây: 2 hạng mục cha, mỗi cha có 2 hạng mục con
        foundation = WorkItem(
            name="Phần móng", description="Đào, đổ bê tông móng",
            budget=600_000_000, progress=100.0, is_completed=True, project_id=project.id,
        )
        structure = WorkItem(
            name="Phần thân", description="Cột, dầm, sàn các tầng",
            budget=1_200_000_000, progress=40.0, project_id=project.id,
        )
        session.add(foundation)
        session.add(structure)
        session.commit()
        session.refresh(foundation)
        session.refresh(structure)

        children = [
            WorkItem(name="Đào đất hố móng", budget=200_000_000, progress=100.0,
                     is_completed=True, parent_id=foundation.id, project_id=project.id),
            WorkItem(name="Đổ bê tông móng", budget=400_000_000, progress=100.0,
                     is_completed=True, parent_id=foundation.id, project_id=project.id),
            WorkItem(name="Cột tầng 1", budget=500_000_000, progress=70.0,
                     parent_id=structure.id, project_id=project.id),
            WorkItem(name="Sàn tầng 2", budget=700_000_000, progress=10.0,
                     parent_id=structure.id, project_id=project.id),
        ]
        session.add_all(children)
        session.commit()
        session.refresh(children[2])

        site_manager = users[UserRole.site_manager]
        worker = users[UserRole.worker]
        company = users[UserRole.construction_company]

        # Task giao cho công nhân
        session.add_all([
            Task(title="Lắp cốp pha cột tầng 1", description="Cột trục A-C",
                 due_date=now + timedelta(days=3), priority=2, status="in_progress",
                 estimated_hours=24, project_id=project.id,
                 work_item_id=children[2].id, assignee_id=worker.id),
            Task(title="Nghiệm thu thép sàn tầng 2", priority=3, status="todo",
                 due_date=now + timedelta(days=10), project_id=project.id,
                 work_item_id=children[3].id, assignee_id=site_manager.id),
        ])

        # Báo cáo hiện trường, phát sinh, issue, nghiệm thu, chi phí, thanh toán
        session.add(SiteReport(report_type="site_update",
                               description="Đã hoàn tất đổ bê tông móng, bắt đầu dựng cột tầng 1.",
                               project_id=project.id, created_by_id=site_manager.id))

        change_order = ChangeOrder(
            title="Phát sinh gia cố nền đất yếu",
            description="Khảo sát phát hiện nền yếu, cần ép thêm cọc.",
            amount_change=150_000_000, status="pending",
            project_id=project.id, requested_by_id=company.id,
        )
        session.add(change_order)

        session.add(Issue(title="Thấm nước hố móng", description="Nước ngầm rỉ vào hố móng khi mưa.",
                          severity="medium", status="open",
                          project_id=project.id, reported_by_id=site_manager.id))

        session.add(AcceptanceRecord(quantity=600_000_000, status="accepted",
                                     notes="Nghiệm thu khối lượng phần móng.",
                                     project_id=project.id, work_item_id=foundation.id,
                                     accepted_by_id=site_manager.id))

        session.add_all([
            CostEntry(category="materials", amount=320_000_000, note="Thép, xi măng đợt 1",
                      project_id=project.id, work_item_id=foundation.id, created_by_id=company.id),
            CostEntry(category="labor", amount=80_000_000, note="Nhân công phần móng",
                      project_id=project.id, work_item_id=foundation.id, created_by_id=company.id),
        ])

        session.add(PaymentRecord(payee_name="Nhà cung cấp thép Pomina", amount=320_000_000,
                                  payment_method="bank_transfer", status="paid", paid_at=now,
                                  note="Thanh toán thép đợt 1",
                                  project_id=project.id, created_by_id=owner.id))

        session.commit()
        print(f"Đã tạo project mẫu (project_id = {project.id}) với đầy đủ dữ liệu.")

    # Các project bổ sung phủ đủ 4 trạng thái vòng đời (chạy lại không tạo trùng).
    with Session(engine) as session:
        users = get_or_create_users(session)
        seed_additional_projects(session, users)

    _print_credentials()


def seed_additional_projects(session: Session, users: dict[UserRole, User]) -> None:
    """Tạo thêm project ở các trạng thái khác nhau để portfolio/báo cáo phong phú.

    Idempotent theo tên project: đã có thì bỏ qua.
    """
    owner = users[UserRole.homeowner]
    company = users[UserRole.construction_company]
    site_manager = users[UserRole.site_manager]
    worker = users[UserRole.worker]
    now = datetime.utcnow()

    for spec in _ADDITIONAL_PROJECTS:
        if session.exec(select(Project).where(Project.name == spec["name"])).first():
            continue
        project = Project(
            name=spec["name"],
            description=spec["description"],
            start_date=now + timedelta(days=spec["start_offset"]),
            end_date=now + timedelta(days=spec["end_offset"]),
            budget=spec["budget"],
            status=spec["status"],
            owner_id=owner.id,
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        for user, role in [(owner, "owner"), (company, "manager"),
                           (site_manager, "member"), (worker, "member")]:
            session.add(ProjectMember(project_id=project.id, user_id=user.id, role=role))

        for wi in spec["work_items"]:
            item = WorkItem(
                name=wi["name"], budget=wi["budget"], progress=wi["progress"],
                is_completed=wi["progress"] >= 100, project_id=project.id,
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            if wi.get("accepted"):
                session.add(AcceptanceRecord(
                    quantity=wi["budget"], status="accepted",
                    notes=f"Nghiệm thu {wi['name']}", project_id=project.id,
                    work_item_id=item.id, accepted_by_id=site_manager.id,
                ))

        for task in spec["tasks"]:
            session.add(Task(
                title=task["title"], priority=task.get("priority", 2),
                status=task["status"], due_date=now + timedelta(days=task["due_offset"]),
                project_id=project.id, assignee_id=worker.id,
            ))

        for cost in spec["costs"]:
            session.add(CostEntry(
                category=cost["category"], amount=cost["amount"], note=cost["note"],
                project_id=project.id, created_by_id=company.id,
            ))

        for pay in spec["payments"]:
            session.add(PaymentRecord(
                payee_name=pay["payee"], amount=pay["amount"], status=pay["status"],
                payment_method="bank_transfer",
                paid_at=now if pay["status"] == "paid" else None,
                project_id=project.id, created_by_id=owner.id,
            ))

        for report in spec["reports"]:
            session.add(SiteReport(
                report_type="site_update", description=report,
                project_id=project.id, created_by_id=site_manager.id,
            ))

        for issue in spec["issues"]:
            session.add(Issue(
                title=issue["title"], description=issue["title"],
                severity=issue["severity"], status=issue["status"],
                resolved_at=now if issue["status"] == "resolved" else None,
                project_id=project.id, reported_by_id=site_manager.id,
            ))

        for co in spec["change_orders"]:
            session.add(ChangeOrder(
                title=co["title"], description=co["title"],
                amount_change=co["amount"], status=co["status"],
                approved_by_id=owner.id if co["status"] == "approved" else None,
                approved_at=now if co["status"] == "approved" else None,
                project_id=project.id, requested_by_id=company.id,
            ))

        session.commit()
        print(f"  + {spec['name']} (project_id = {project.id}, {spec['status'].value})")


def _print_credentials():
    print("\nTài khoản demo (mật khẩu chung: %s)" % DEFAULT_PASSWORD)
    for email, full_name, role, _ in USERS:
        print(f"  - {email:<28} {role.value:<22} {full_name}")
    print("\nĐăng nhập tại http://localhost:8000/docs (nút Authorize, dùng email làm username).")


if __name__ == "__main__":
    seed()
