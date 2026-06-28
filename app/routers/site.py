import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session, select

from app.db import get_session
from app.models import (
    AcceptanceCreate,
    AcceptanceRead,
    AcceptanceRecord,
    Issue,
    IssueCreate,
    IssueRead,
    ProjectPhoto,
    ProjectPhotoRead,
    SiteReport,
    SiteReportCreate,
    SiteReportRead,
    User,
    WorkItem,
)
from app.security import (
    CAN_ACCEPT_WORK,
    get_current_active_user,
    require_business_role,
    require_project_access,
)
from app.services import write_audit_log

router = APIRouter(tags=["site operations"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".doc", ".docx"}


@router.post("/projects/{project_id}/reports", response_model=SiteReportRead)
def create_site_report(
    project_id: int,
    report: SiteReportCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    require_project_access(project_id, current_user, session)
    db_report = SiteReport(**report.model_dump(), project_id=project_id, created_by_id=current_user.id)
    session.add(db_report)
    write_audit_log(
        session,
        "site_report.created",
        "SiteReport",
        None,
        project_id,
        current_user.id,
        {"report_type": db_report.report_type},
    )
    session.commit()
    session.refresh(db_report)
    return db_report


@router.get("/projects/{project_id}/reports", response_model=List[SiteReportRead])
def list_site_reports(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    require_project_access(project_id, current_user, session)
    return session.exec(select(SiteReport).where(SiteReport.project_id == project_id)).all()


@router.post("/projects/{project_id}/issues", response_model=IssueRead)
def create_issue(
    project_id: int,
    issue: IssueCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    require_project_access(project_id, current_user, session)
    db_issue = Issue(**issue.model_dump(), project_id=project_id, reported_by_id=current_user.id)
    session.add(db_issue)
    write_audit_log(
        session,
        "issue.created",
        "Issue",
        None,
        project_id,
        current_user.id,
        {"title": db_issue.title, "severity": db_issue.severity},
    )
    session.commit()
    session.refresh(db_issue)
    return db_issue


@router.get("/projects/{project_id}/issues", response_model=List[IssueRead])
def list_issues(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    require_project_access(project_id, current_user, session)
    return session.exec(select(Issue).where(Issue.project_id == project_id)).all()


@router.patch("/issues/{issue_id}/resolve", response_model=IssueRead)
def resolve_issue(
    issue_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    issue = session.exec(select(Issue).where(Issue.id == issue_id)).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    require_project_access(issue.project_id, current_user, session)
    issue.status = "resolved"
    issue.resolved_at = datetime.utcnow()
    session.add(issue)
    write_audit_log(session, "issue.resolved", "Issue", issue.id, issue.project_id, current_user.id, {})
    session.commit()
    session.refresh(issue)
    return issue


@router.post("/projects/{project_id}/acceptances", response_model=AcceptanceRead)
def create_acceptance(
    project_id: int,
    acceptance: AcceptanceCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    # Nghiệm thu: bất kỳ thành viên dự án nào, nhưng vai trò nghiệp vụ phải được phép
    # (QL công trình / công ty xây dựng). Business role là cổng chính ở đây.
    require_project_access(project_id, current_user, session)
    require_business_role(current_user, CAN_ACCEPT_WORK)
    workitem = None
    if acceptance.work_item_id is not None:
        workitem = session.exec(
            select(WorkItem).where(WorkItem.id == acceptance.work_item_id, WorkItem.project_id == project_id)
        ).first()
        if not workitem:
            raise HTTPException(status_code=404, detail="WorkItem not found")
    db_acceptance = AcceptanceRecord(
        project_id=project_id,
        work_item_id=acceptance.work_item_id,
        quantity=acceptance.quantity,
        notes=acceptance.notes,
        accepted_by_id=current_user.id,
        status="accepted",
    )
    session.add(db_acceptance)
    # Nghiệm thu đạt -> khép kín tiến độ: đánh dấu hạng mục hoàn thành.
    if workitem is not None:
        workitem.progress = 100.0
        workitem.is_completed = True
        session.add(workitem)
    write_audit_log(
        session,
        "acceptance.created",
        "AcceptanceRecord",
        None,
        project_id,
        current_user.id,
        {"work_item_id": acceptance.work_item_id, "quantity": acceptance.quantity},
    )
    session.commit()
    session.refresh(db_acceptance)
    return db_acceptance


@router.get("/projects/{project_id}/acceptances", response_model=List[AcceptanceRead])
def list_acceptances(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    require_project_access(project_id, current_user, session)
    return session.exec(select(AcceptanceRecord).where(AcceptanceRecord.project_id == project_id)).all()


@router.post("/projects/{project_id}/photos/", response_model=ProjectPhotoRead)
def upload_project_photo(
    project_id: int,
    file: UploadFile = File(...),
    description: Optional[str] = None,
    site_report_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    require_project_access(project_id, current_user, session)
    if site_report_id is not None:
        report = session.exec(
            select(SiteReport).where(SiteReport.id == site_report_id, SiteReport.project_id == project_id)
        ).first()
        if not report:
            raise HTTPException(status_code=404, detail="Site report not found in this project")
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed")
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    db_photo = ProjectPhoto(
        filename=safe_filename,
        description=description,
        file_path=str(file_path),
        project_id=project_id,
        site_report_id=site_report_id,
    )
    session.add(db_photo)
    session.commit()
    session.refresh(db_photo)
    return db_photo


@router.get("/projects/{project_id}/photos/", response_model=List[ProjectPhotoRead])
def read_project_photos(
    project_id: int,
    site_report_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    require_project_access(project_id, current_user, session)
    query = select(ProjectPhoto).where(ProjectPhoto.project_id == project_id)
    if site_report_id is not None:
        query = query.where(ProjectPhoto.site_report_id == site_report_id)
    return session.exec(query).all()
