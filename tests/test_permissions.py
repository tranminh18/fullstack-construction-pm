"""Test phân quyền nghiệp vụ và cấu trúc WBS cây."""
import pytest

from app.models import UserRole
from conftest import auth_header


@pytest.fixture
def project(client, users):
    """Project do homeowner tạo; các vai trò khác được thêm làm thành viên."""
    owner = auth_header(client, f"{UserRole.homeowner.value}@test.com")
    pid = client.post("/projects/", headers=owner, json={"name": "P1"}).json()["id"]
    for role in [UserRole.construction_company, UserRole.contractor, UserRole.site_manager, UserRole.worker]:
        client.post(
            f"/projects/{pid}/members",
            headers=owner,
            json={"user_email": f"{role.value}@test.com", "role": "member"},
        )
    return pid


def test_wbs_tree_is_nested(client, users, project):
    owner = auth_header(client, f"{UserRole.homeowner.value}@test.com")
    parent = client.post(f"/projects/{project}/workitems/", headers=owner, json={"name": "Phần móng"}).json()
    client.post(
        f"/projects/{project}/workitems/",
        headers=owner,
        json={"name": "Đào đất", "parent_id": parent["id"]},
    )
    tree = client.get(f"/projects/{project}/workitems/tree", headers=owner).json()
    assert len(tree) == 1
    assert tree[0]["name"] == "Phần móng"
    assert len(tree[0]["children"]) == 1
    assert tree[0]["children"][0]["name"] == "Đào đất"


def test_workitem_rejects_foreign_parent(client, users, project):
    owner = auth_header(client, f"{UserRole.homeowner.value}@test.com")
    resp = client.post(
        f"/projects/{project}/workitems/",
        headers=owner,
        json={"name": "X", "parent_id": 9999},
    )
    assert resp.status_code == 404


@pytest.mark.parametrize(
    "role,expected",
    [
        (UserRole.site_manager, 200),
        (UserRole.construction_company, 200),
        (UserRole.worker, 403),
        (UserRole.homeowner, 403),
    ],
)
def test_assign_task_permission(client, users, project, role, expected):
    header = auth_header(client, f"{role.value}@test.com")
    resp = client.post(f"/projects/{project}/tasks/", headers=header, json={"title": "t"})
    assert resp.status_code == expected


@pytest.mark.parametrize(
    "role,expected",
    [
        (UserRole.homeowner, 200),
        (UserRole.construction_company, 200),
        (UserRole.worker, 403),
        (UserRole.site_manager, 403),
    ],
)
def test_approve_change_order_permission(client, users, project, role, expected):
    company = auth_header(client, f"{UserRole.construction_company.value}@test.com")
    co_id = client.post(
        f"/projects/{project}/change-orders",
        headers=company,
        json={"title": "CO", "amount_change": 1000},
    ).json()["id"]
    header = auth_header(client, f"{role.value}@test.com")
    assert client.patch(f"/change-orders/{co_id}/approve", headers=header).status_code == expected


def test_progress_100_marks_completed(client, users, project):
    owner = auth_header(client, f"{UserRole.homeowner.value}@test.com")
    wi = client.post(f"/projects/{project}/workitems/", headers=owner, json={"name": "W"}).json()
    resp = client.patch(
        f"/workitems/{wi['id']}/progress",
        headers=owner,
        json={"progress_percentage": 100},
    )
    assert resp.status_code == 200
    assert resp.json()["is_completed"] is True


def test_non_member_cannot_access_project(client, users, project):
    # Tạo user ngoài dự án
    client.post(
        "/register",
        json={"email": "outsider@test.com", "full_name": "Out", "password": "password123"},
    )
    outsider = auth_header(client, "outsider@test.com")
    assert client.get(f"/projects/{project}", headers=outsider).status_code == 403


def test_assign_task_to_member(client, users, project):
    """Giao việc cho một thành viên dự án phải lưu được assignee_id."""
    manager = auth_header(client, f"{UserRole.site_manager.value}@test.com")
    worker = client.get("/me", headers=auth_header(client, f"{UserRole.worker.value}@test.com")).json()
    resp = client.post(
        f"/projects/{project}/tasks/",
        headers=manager,
        json={"title": "Đổ bê tông", "assignee_id": worker["id"]},
    )
    assert resp.status_code == 200
    assert resp.json()["assignee_id"] == worker["id"]


def test_assign_task_to_non_member_rejected(client, users, project):
    """Không được giao việc cho người ngoài dự án."""
    manager = auth_header(client, f"{UserRole.site_manager.value}@test.com")
    client.post(
        "/register",
        json={"email": "ghost@test.com", "full_name": "Ghost", "password": "password123"},
    )
    ghost = client.get("/me", headers=auth_header(client, "ghost@test.com")).json()
    resp = client.post(
        f"/projects/{project}/tasks/",
        headers=manager,
        json={"title": "t", "assignee_id": ghost["id"]},
    )
    assert resp.status_code == 400


def test_acceptance_completes_workitem(client, users, project):
    """Nghiệm thu hạng mục phải khép kín tiến độ về 100% / hoàn thành."""
    owner = auth_header(client, f"{UserRole.homeowner.value}@test.com")
    manager = auth_header(client, f"{UserRole.site_manager.value}@test.com")
    wi = client.post(f"/projects/{project}/workitems/", headers=owner, json={"name": "Trần thạch cao"}).json()
    resp = client.post(
        f"/projects/{project}/acceptances",
        headers=manager,
        json={"work_item_id": wi["id"], "quantity": 50},
    )
    assert resp.status_code == 200
    refreshed = client.get(f"/projects/{project}/workitems/", headers=owner).json()
    target = next(item for item in refreshed if item["id"] == wi["id"])
    assert target["is_completed"] is True
    assert target["progress"] == 100.0


def test_activity_report_status_keys_are_plain(client, users, project):
    """project_status_counts phải dùng key 'active'... không phải 'ProjectStatus.active'."""
    owner = auth_header(client, f"{UserRole.homeowner.value}@test.com")
    report = client.get("/reports/projects", headers=owner).json()
    for key in report["project_status_counts"]:
        assert "ProjectStatus" not in key
    assert set(report["project_status_counts"]) <= {"planning", "active", "delayed", "completed"}
