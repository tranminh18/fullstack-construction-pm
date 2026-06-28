from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import (
    ProgressUpdate,
    Task,
    TaskCreate,
    TaskRead,
    User,
    WorkItem,
    WorkItemCreate,
    WorkItemRead,
    WorkItemTreeRead,
)
from app.security import (
    CAN_ASSIGN_TASK,
    get_current_active_user,
    get_project_role,
    require_business_role,
    require_project_access,
)
from app.services import build_workitem_tree

router = APIRouter(tags=["workitems & tasks"])


def _validate_task_links(project_id: int, assignee_id, work_item_id, session: Session):
    """Đảm bảo người được giao là thành viên dự án và hạng mục thuộc đúng dự án."""
    if assignee_id is not None and get_project_role(project_id, assignee_id, session) is None:
        raise HTTPException(status_code=400, detail="Assignee is not a member of this project")
    if work_item_id is not None:
        workitem = session.exec(
            select(WorkItem).where(WorkItem.id == work_item_id, WorkItem.project_id == project_id)
        ).first()
        if not workitem:
            raise HTTPException(status_code=404, detail="WorkItem not found in this project")


@router.post("/projects/{project_id}/workitems/", response_model=WorkItemRead)
def create_workitem(
    project_id: int,
    workitem: WorkItemCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    require_project_access(project_id, current_user, session)
    if workitem.parent_id is not None:
        parent = session.exec(
            select(WorkItem).where(WorkItem.id == workitem.parent_id, WorkItem.project_id == project_id)
        ).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent work item not found in this project")
    db_workitem = WorkItem(**workitem.model_dump(), project_id=project_id)
    session.add(db_workitem)
    session.commit()
    session.refresh(db_workitem)
    return db_workitem


@router.get("/projects/{project_id}/workitems/tree", response_model=List[WorkItemTreeRead])
def read_workitem_tree(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    return build_workitem_tree(project_id, current_user, session)


@router.get("/projects/{project_id}/workitems/", response_model=List[WorkItemRead])
def read_workitems(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    require_project_access(project_id, current_user, session)
    return session.exec(select(WorkItem).where(WorkItem.project_id == project_id)).all()


@router.patch("/workitems/{workitem_id}/progress", response_model=WorkItemRead)
def update_workitem_progress(
    workitem_id: int,
    progress_update: ProgressUpdate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    workitem = session.exec(select(WorkItem).where(WorkItem.id == workitem_id)).first()
    if not workitem:
        raise HTTPException(status_code=404, detail="WorkItem not found")
    require_project_access(workitem.project_id, current_user, session)
    workitem.progress = progress_update.progress_percentage
    if workitem.progress >= 100:
        workitem.is_completed = True
    session.add(workitem)
    session.commit()
    session.refresh(workitem)
    return workitem


@router.post("/projects/{project_id}/tasks/", response_model=TaskRead)
def create_task(
    project_id: int,
    task: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    require_project_access(project_id, current_user, session)
    require_business_role(current_user, CAN_ASSIGN_TASK)
    _validate_task_links(project_id, task.assignee_id, task.work_item_id, session)
    db_task = Task(**task.model_dump(), project_id=project_id)
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task


@router.get("/projects/{project_id}/tasks/", response_model=List[TaskRead])
def read_tasks(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    require_project_access(project_id, current_user, session)
    return session.exec(select(Task).where(Task.project_id == project_id)).all()


@router.patch("/tasks/{task_id}", response_model=TaskRead)
def update_task(
    task_id: int,
    task_update: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    task = session.exec(select(Task).where(Task.id == task_id)).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    require_project_access(task.project_id, current_user, session)
    task_data = task_update.model_dump(exclude_unset=True)
    _validate_task_links(
        task.project_id,
        task_data.get("assignee_id", task.assignee_id),
        task_data.get("work_item_id", task.work_item_id),
        session,
    )
    for key, value in task_data.items():
        setattr(task, key, value)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task
