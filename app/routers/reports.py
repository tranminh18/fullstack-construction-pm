from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.models import (
    AuditLog,
    AuditLogRead,
    ChangeOrder,
    CostEntry,
    Issue,
    PaymentRecord,
    PortfolioDashboardRead,
    ProjectActivityReportRead,
    ProjectDashboardRead,
)
from app.security import get_current_active_user, require_project_access
from app.services import build_activity_report, build_project_dashboard, get_accessible_projects

router = APIRouter(tags=["reports"])


@router.get("/projects/{project_id}/audit-logs", response_model=list[AuditLogRead])
def list_project_audit_logs(
    project_id: int,
    current_user=Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    require_project_access(project_id, current_user, session)
    return session.exec(select(AuditLog).where(AuditLog.project_id == project_id).order_by(AuditLog.created_at.desc())).all()


@router.get("/projects/{project_id}/dashboard", response_model=ProjectDashboardRead)
def project_dashboard(
    project_id: int,
    current_user=Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    return build_project_dashboard(project_id, current_user, session)


@router.get("/projects/{project_id}/summary")
def project_summary(
    project_id: int,
    current_user=Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    return build_project_dashboard(project_id, current_user, session)


@router.get("/dashboard", response_model=PortfolioDashboardRead)
def portfolio_dashboard(
    current_user=Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    accessible_projects = get_accessible_projects(current_user, session)
    project_ids = [project.id for project in accessible_projects]
    if not project_ids:
        return PortfolioDashboardRead(
            project_count=0,
            total_budget=0.0,
            total_cost=0.0,
            total_paid=0.0,
            outstanding_balance=0.0,
            open_issues=0,
            pending_change_orders=0,
            generated_at=datetime.utcnow(),
        )
    total_budget = sum(project.budget or 0.0 for project in accessible_projects)
    total_cost = sum(entry.amount for entry in session.exec(select(CostEntry).where(CostEntry.project_id.in_(project_ids))).all())
    total_paid = sum(payment.amount for payment in session.exec(select(PaymentRecord).where(PaymentRecord.project_id.in_(project_ids))).all() if payment.status == "paid")
    open_issues = len([item for item in session.exec(select(Issue).where(Issue.project_id.in_(project_ids))).all() if item.status == "open"])
    pending_change_orders = len([item for item in session.exec(select(ChangeOrder).where(ChangeOrder.project_id.in_(project_ids))).all() if item.status == "pending"])
    return PortfolioDashboardRead(
        project_count=len(accessible_projects),
        total_budget=round(total_budget, 2),
        total_cost=round(total_cost, 2),
        total_paid=round(total_paid, 2),
        outstanding_balance=round(total_cost - total_paid, 2),
        open_issues=open_issues,
        pending_change_orders=pending_change_orders,
        generated_at=datetime.utcnow(),
    )


@router.get("/reports/projects", response_model=ProjectActivityReportRead)
def project_activity_report(
    year: Optional[int] = None,
    month: Optional[int] = None,
    status: Optional[str] = None,
    current_user=Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    return build_activity_report(current_user=current_user, session=session, year=year, month=month, status=status)
