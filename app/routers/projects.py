from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import (
    Project,
    ProjectCreate,
    ProjectMember,
    ProjectMemberCreate,
    ProjectMemberRead,
    ProjectRead,
    User,
)
from app.security import get_current_active_user, require_project_access, require_project_management
from app.services import get_accessible_projects, write_audit_log

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", response_model=ProjectRead)
def create_project(
    project: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    db_project = Project(**project.model_dump(), owner_id=current_user.id)
    session.add(db_project)
    session.commit()
    session.refresh(db_project)
    session.add(ProjectMember(project_id=db_project.id, user_id=current_user.id, role="owner"))
    write_audit_log(
        session,
        "project.created",
        "Project",
        db_project.id,
        db_project.id,
        current_user.id,
        {"name": db_project.name},
    )
    session.commit()
    return db_project


@router.get("/", response_model=List[ProjectRead])
def read_projects(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    projects = get_accessible_projects(current_user, session)
    return projects[skip : skip + limit]


@router.get("/{project_id}", response_model=ProjectRead)
def read_project(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    return require_project_access(project_id, current_user, session)


@router.post("/{project_id}/members", response_model=ProjectMemberRead)
def add_project_member(
    project_id: int,
    member: ProjectMemberCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    require_project_management(project_id, current_user, session)
    target_user = session.exec(select(User).where(User.email == member.user_email)).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    existing_member = session.exec(
        select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == target_user.id)
    ).first()
    if existing_member:
        existing_member.role = member.role
        session.add(existing_member)
        write_audit_log(
            session,
            "project.member.updated",
            "ProjectMember",
            existing_member.id,
            project_id,
            current_user.id,
            {"user_id": existing_member.user_id, "role": existing_member.role},
        )
        session.commit()
        session.refresh(existing_member)
        return existing_member
    db_member = ProjectMember(project_id=project_id, user_id=target_user.id, role=member.role)
    session.add(db_member)
    write_audit_log(
        session,
        "project.member.added",
        "ProjectMember",
        None,
        project_id,
        current_user.id,
        {"user_id": target_user.id, "role": member.role},
    )
    session.commit()
    session.refresh(db_member)
    return db_member


@router.get("/{project_id}/members", response_model=List[ProjectMemberRead])
def list_project_members(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    require_project_access(project_id, current_user, session)
    return session.exec(select(ProjectMember).where(ProjectMember.project_id == project_id)).all()
