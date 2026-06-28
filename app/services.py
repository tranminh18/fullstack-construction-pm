import json
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from .models import (
    AcceptanceRecord,
    AuditLog,
    ChangeOrder,
    CostEntry,
    Issue,
    PaymentRecord,
    Project,
    ProjectPhoto,
    ProjectActivityReportRead,
    ProjectDashboardRead,
    ProjectMember,
    ProjectReportItem,
    ProjectStatus,
    SiteReport,
    Task,
    WorkItem,
    WorkItemTreeRead,
)
from .security import require_project_access


def get_accessible_projects(current_user, session: Session) -> List[Project]:
    """Trả về các project user sở hữu hoặc là thành viên (gộp, không trùng)."""
    owned = session.exec(select(Project).where(Project.owner_id == current_user.id)).all()
    member_rows = session.exec(
        select(ProjectMember).where(ProjectMember.user_id == current_user.id)
    ).all()
    member_ids = [member.project_id for member in member_rows]
    member_projects = (
        session.exec(select(Project).where(Project.id.in_(member_ids))).all() if member_ids else []
    )
    project_map = {project.id: project for project in owned}
    for project in member_projects:
        project_map[project.id] = project
    return list(project_map.values())


def build_workitem_tree(project_id: int, current_user, session: Session) -> List[WorkItemTreeRead]:
    """Trả về cấu trúc phân rã công việc (WBS) dạng cây lồng nhau."""
    require_project_access(project_id, current_user, session)
    work_items = session.exec(select(WorkItem).where(WorkItem.project_id == project_id)).all()

    nodes: dict[int, WorkItemTreeRead] = {
        item.id: WorkItemTreeRead.model_validate(item, from_attributes=True) for item in work_items
    }
    roots: List[WorkItemTreeRead] = []
    for item in work_items:
        node = nodes[item.id]
        parent = nodes.get(item.parent_id) if item.parent_id is not None else None
        if parent is not None:
            parent.children.append(node)
        else:
            # parent_id None, hoặc trỏ tới item ngoài project -> coi như gốc
            roots.append(node)
    return roots


def write_audit_log(
    session: Session,
    action: str,
    entity_type: str,
    entity_id: Optional[int] = None,
    project_id: Optional[int] = None,
    actor_id: Optional[int] = None,
    metadata: Optional[dict] = None,
):
    audit_log = AuditLog(
        actor_id=actor_id,
        project_id=project_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
    )
    session.add(audit_log)


def build_project_dashboard(project_id: int, current_user, session: Session) -> ProjectDashboardRead:
    project = require_project_access(project_id, current_user, session)
    work_items = session.exec(select(WorkItem).where(WorkItem.project_id == project_id)).all()
    tasks = session.exec(select(Task).where(Task.project_id == project_id)).all()
    cost_entries = session.exec(select(CostEntry).where(CostEntry.project_id == project_id)).all()
    payments = session.exec(select(PaymentRecord).where(PaymentRecord.project_id == project_id)).all()
    change_orders = session.exec(select(ChangeOrder).where(ChangeOrder.project_id == project_id)).all()
    issues = session.exec(select(Issue).where(Issue.project_id == project_id)).all()
    photos = session.exec(select(ProjectPhoto).where(ProjectPhoto.project_id == project_id)).all()
    site_reports = session.exec(select(SiteReport).where(SiteReport.project_id == project_id)).all()
    members = session.exec(select(ProjectMember).where(ProjectMember.project_id == project_id)).all()

    now = datetime.utcnow()
    task_counts = {"todo": 0, "in_progress": 0, "done": 0}
    overdue_tasks = 0
    for task in tasks:
        task_counts[task.status] = task_counts.get(task.status, 0) + 1
        if task.due_date and task.due_date < now and task.status != "done":
            overdue_tasks += 1

    issue_counts = {"open": 0, "resolved": 0}
    for issue in issues:
        issue_counts[issue.status] = issue_counts.get(issue.status, 0) + 1

    change_order_counts = {"pending": 0, "approved": 0, "rejected": 0}
    for change_order in change_orders:
        change_order_counts[change_order.status] = change_order_counts.get(change_order.status, 0) + 1

    members_by_role: dict[str, int] = {}
    for member in members:
        members_by_role[member.role] = members_by_role.get(member.role, 0) + 1

    total_cost = sum(entry.amount for entry in cost_entries)
    total_paid = sum(payment.amount for payment in payments if payment.status == "paid")
    completion_percent = round(sum(item.progress for item in work_items) / len(work_items), 2) if work_items else 0.0

    return ProjectDashboardRead(
        project_id=project.id,
        project_name=project.name,
        budget=project.budget,
        total_cost=round(total_cost, 2),
        total_paid=round(total_paid, 2),
        outstanding_balance=round(total_cost - total_paid, 2),
        budget_variance=round(project.budget - total_cost, 2) if project.budget is not None else None,
        completion_percent=completion_percent,
        work_item_count=len(work_items),
        completed_work_items=len([item for item in work_items if item.is_completed]),
        task_counts=task_counts,
        overdue_tasks=overdue_tasks,
        issue_counts=issue_counts,
        change_order_counts=change_order_counts,
        change_order_value=round(sum(item.amount_change for item in change_orders), 2),
        photo_count=len(photos),
        site_report_count=len(site_reports),
        member_count=len(members),
        members_by_role=members_by_role,
        generated_at=now,
    )


def derive_project_status(project: Project, work_items: List[WorkItem], now: datetime) -> str:
    if work_items and all(item.is_completed or item.progress >= 100 for item in work_items):
        return ProjectStatus.completed.value
    if project.end_date and project.end_date < now:
        return ProjectStatus.delayed.value
    if project.start_date and project.start_date > now:
        return ProjectStatus.planning.value
    return ProjectStatus.active.value


def get_report_period_bounds(year: Optional[int], month: Optional[int]):
    if year is None and month is None:
        return None, None, "all_time"
    if year is None or month is None:
        raise HTTPException(status_code=400, detail="Both year and month must be provided together")
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
    start = datetime(year, month, 1)
    end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    return start, end, f"{year:04d}-{month:02d}"


def is_in_period(value: Optional[datetime], start: Optional[datetime], end: Optional[datetime]) -> bool:
    if start is None or end is None:
        return True
    if value is None:
        return False
    return start <= value < end


def build_activity_report(current_user, session: Session, year: Optional[int] = None, month: Optional[int] = None, status: Optional[str] = None) -> ProjectActivityReportRead:
    start, end, period_label = get_report_period_bounds(year, month)
    accessible_projects = get_accessible_projects(current_user, session)
    now = datetime.utcnow()

    project_items: List[ProjectReportItem] = []
    activity_counts = {
        "cost_entries": 0,
        "payments": 0,
        "change_orders": 0,
        "issues": 0,
        "site_reports": 0,
        "acceptances": 0,
    }
    status_counts: dict[str, int] = {"planning": 0, "active": 0, "completed": 0, "delayed": 0}

    total_budget = 0.0
    total_cost = 0.0
    total_paid = 0.0
    outstanding_balance = 0.0

    for project in accessible_projects:
        work_items = session.exec(select(WorkItem).where(WorkItem.project_id == project.id)).all()
        project_status = derive_project_status(project, work_items, now)
        if status and project_status != status:
            continue

        cost_entries = session.exec(select(CostEntry).where(CostEntry.project_id == project.id)).all()
        payments = session.exec(select(PaymentRecord).where(PaymentRecord.project_id == project.id)).all()
        change_orders = session.exec(select(ChangeOrder).where(ChangeOrder.project_id == project.id)).all()
        issues = session.exec(select(Issue).where(Issue.project_id == project.id)).all()

        project_cost = sum(entry.amount for entry in cost_entries if is_in_period(entry.cost_date, start, end))
        project_paid = sum(payment.amount for payment in payments if payment.status == "paid" and is_in_period(payment.paid_at, start, end))
        project_issues = len([item for item in issues if is_in_period(item.created_at, start, end)])

        project_items.append(
            ProjectReportItem(
                project_id=project.id,
                project_name=project.name,
                status=project_status,
                budget=project.budget,
                total_cost=round(project_cost, 2),
                total_paid=round(project_paid, 2),
                outstanding_balance=round(project_cost - project_paid, 2),
                completion_percent=round(sum(item.progress for item in work_items) / len(work_items), 2) if work_items else 0.0,
                issue_count=project_issues,
                pending_change_orders=len([item for item in change_orders if item.status == "pending"]),
            )
        )

        status_counts[str(project_status)] = status_counts.get(str(project_status), 0) + 1
        total_budget += project.budget or 0.0
        total_cost += project_cost
        total_paid += project_paid
        outstanding_balance += project_cost - project_paid

        activity_counts["cost_entries"] += len([entry for entry in cost_entries if is_in_period(entry.cost_date, start, end)])
        activity_counts["payments"] += len([payment for payment in payments if payment.status == "paid" and is_in_period(payment.paid_at, start, end)])
        activity_counts["change_orders"] += len([item for item in change_orders if is_in_period(item.created_at, start, end)])
        activity_counts["issues"] += project_issues
        activity_counts["site_reports"] += len([item for item in session.exec(select(SiteReport).where(SiteReport.project_id == project.id)).all() if is_in_period(item.created_at, start, end)])
        activity_counts["acceptances"] += len([item for item in session.exec(select(AcceptanceRecord).where(AcceptanceRecord.project_id == project.id)).all() if is_in_period(item.accepted_at, start, end)])

    return ProjectActivityReportRead(
        period=period_label,
        project_count=len(project_items),
        total_budget=round(total_budget, 2),
        total_cost=round(total_cost, 2),
        total_paid=round(total_paid, 2),
        outstanding_balance=round(outstanding_balance, 2),
        project_status_counts=status_counts,
        activity_counts=activity_counts,
        projects=project_items,
        generated_at=now,
    )
