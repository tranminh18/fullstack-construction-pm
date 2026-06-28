import json
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field
from sqlmodel import Field, Relationship, SQLModel


class ProjectStatus(str, Enum):
    planning = "planning"
    active = "active"
    delayed = "delayed"
    completed = "completed"


class UserRole(str, Enum):
    """Vai trò nghiệp vụ của các bên tham gia, theo đề bài."""

    homeowner = "homeowner"  # chủ nhà / chủ đầu tư
    construction_company = "construction_company"  # công ty xây dựng
    contractor = "contractor"  # nhà thầu
    site_manager = "site_manager"  # quản lý công trình
    worker = "worker"  # công nhân


class UserBase(SQLModel):
    email: EmailStr = Field(index=True, unique=True)
    full_name: str
    role: UserRole = Field(default=UserRole.worker, index=True)
    is_active: bool = True


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    projects: List["Project"] = Relationship(back_populates="owner")
    tasks: List["Task"] = Relationship(back_populates="assignee")


class UserCreate(UserBase):
    password: str = Field(min_length=6)


class UserRead(UserBase):
    id: int
    is_active: bool


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


class ProjectBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[float] = None
    status: ProjectStatus = Field(default=ProjectStatus.planning, index=True)


class Project(ProjectBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id")
    owner: User = Relationship(back_populates="projects")
    work_items: List["WorkItem"] = Relationship(back_populates="project")
    tasks: List["Task"] = Relationship(back_populates="project")
    photos: List["ProjectPhoto"] = Relationship(back_populates="project")


class ProjectCreate(ProjectBase):
    pass


class ProjectRead(ProjectBase):
    id: int
    owner_id: int


class AuditLogRead(BaseModel):
    id: int
    actor_id: Optional[int]
    project_id: Optional[int]
    action: str
    entity_type: str
    entity_id: Optional[int]
    metadata_json: Optional[str]
    created_at: datetime


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    actor_id: Optional[int] = Field(default=None, foreign_key="user.id")
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    action: str = Field(index=True)
    entity_type: str = Field(index=True)
    entity_id: Optional[int] = None
    metadata_json: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class WorkItemBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    budget: Optional[float] = None
    progress: float = 0.0
    is_completed: bool = False


class WorkItem(WorkItemBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    parent_id: Optional[int] = Field(default=None, foreign_key="workitem.id", index=True)
    project: Project = Relationship(back_populates="work_items")
    tasks: List["Task"] = Relationship(back_populates="work_item")


class WorkItemCreate(WorkItemBase):
    parent_id: Optional[int] = None


class WorkItemRead(WorkItemBase):
    id: int
    project_id: int
    parent_id: Optional[int] = None
    progress: float = 0.0


class WorkItemTreeRead(WorkItemRead):
    children: List["WorkItemTreeRead"] = []


class TaskBase(SQLModel):
    title: str = Field(index=True)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: int = Field(default=1, ge=1, le=3)
    status: str = Field(default="todo")
    estimated_hours: Optional[float] = None


class Task(TaskBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    work_item_id: Optional[int] = Field(foreign_key="workitem.id")
    assignee_id: Optional[int] = Field(foreign_key="user.id")

    project: Project = Relationship(back_populates="tasks")
    work_item: Optional[WorkItem] = Relationship(back_populates="tasks")
    assignee: Optional[User] = Relationship(back_populates="tasks")


class TaskCreate(TaskBase):
    assignee_id: Optional[int] = None
    work_item_id: Optional[int] = None


class TaskRead(TaskBase):
    id: int
    project_id: int
    work_item_id: Optional[int]
    assignee_id: Optional[int]


class ProgressUpdate(BaseModel):
    progress_percentage: float = Field(ge=0, le=100)
    notes: Optional[str] = None


class ProjectPhotoBase(SQLModel):
    filename: str
    description: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectPhoto(ProjectPhotoBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    site_report_id: Optional[int] = Field(default=None, foreign_key="sitereport.id", index=True)
    file_path: str
    project: Project = Relationship(back_populates="photos")


class ProjectPhotoCreate(BaseModel):
    description: Optional[str] = None
    site_report_id: Optional[int] = None


class ProjectPhotoRead(ProjectPhotoBase):
    id: int
    project_id: int
    site_report_id: Optional[int] = None
    uploaded_at: datetime


class ProjectMemberBase(SQLModel):
    role: str = Field(default="member", index=True)


class ProjectMember(ProjectMemberBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    user_id: int = Field(foreign_key="user.id")


class ProjectMemberCreate(BaseModel):
    user_email: EmailStr
    role: str = Field(default="member")


class ProjectMemberRead(ProjectMemberBase):
    id: int
    project_id: int
    user_id: int


class ChangeOrderBase(SQLModel):
    title: str
    description: Optional[str] = None
    amount_change: float = 0.0
    status: str = Field(default="pending", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChangeOrder(ChangeOrderBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    requested_by_id: int = Field(foreign_key="user.id")
    approved_by_id: Optional[int] = Field(default=None, foreign_key="user.id")
    approved_at: Optional[datetime] = None


class ChangeOrderCreate(BaseModel):
    title: str
    description: Optional[str] = None
    amount_change: float = 0.0


class ChangeOrderRead(ChangeOrderBase):
    id: int
    project_id: int
    requested_by_id: int
    approved_by_id: Optional[int]
    approved_at: Optional[datetime]


class SiteReportBase(SQLModel):
    report_type: str = Field(default="site_update", index=True)
    description: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SiteReport(SiteReportBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    created_by_id: int = Field(foreign_key="user.id")


class SiteReportCreate(BaseModel):
    report_type: str = Field(default="site_update")
    description: str


class SiteReportRead(SiteReportBase):
    id: int
    project_id: int
    created_by_id: int


class IssueBase(SQLModel):
    title: str
    description: str
    severity: str = Field(default="medium", index=True)
    status: str = Field(default="open", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Issue(IssueBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    reported_by_id: int = Field(foreign_key="user.id")
    resolved_at: Optional[datetime] = None


class IssueCreate(BaseModel):
    title: str
    description: str
    severity: str = Field(default="medium")


class IssueRead(IssueBase):
    id: int
    project_id: int
    reported_by_id: int
    resolved_at: Optional[datetime]


class AcceptanceBase(SQLModel):
    quantity: float = 0.0
    status: str = Field(default="pending", index=True)
    notes: Optional[str] = None
    accepted_at: datetime = Field(default_factory=datetime.utcnow)


class AcceptanceRecord(AcceptanceBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    work_item_id: Optional[int] = Field(default=None, foreign_key="workitem.id")
    accepted_by_id: int = Field(foreign_key="user.id")


class AcceptanceCreate(BaseModel):
    work_item_id: Optional[int] = None
    quantity: float = 0.0
    notes: Optional[str] = None


class AcceptanceRead(AcceptanceBase):
    id: int
    project_id: int
    work_item_id: Optional[int]
    accepted_by_id: int


class CostEntryBase(SQLModel):
    category: str = Field(index=True)
    amount: float
    note: Optional[str] = None
    cost_date: datetime = Field(default_factory=datetime.utcnow)


class CostEntry(CostEntryBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    work_item_id: Optional[int] = Field(default=None, foreign_key="workitem.id")
    created_by_id: int = Field(foreign_key="user.id")


class CostEntryCreate(BaseModel):
    category: str
    amount: float
    note: Optional[str] = None
    work_item_id: Optional[int] = None


class CostEntryRead(CostEntryBase):
    id: int
    project_id: int
    work_item_id: Optional[int]
    created_by_id: int


class PaymentBase(SQLModel):
    payee_name: str
    amount: float
    payment_method: str = Field(default="bank_transfer")
    status: str = Field(default="pending", index=True)
    paid_at: Optional[datetime] = None
    note: Optional[str] = None


class PaymentRecord(PaymentBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    created_by_id: int = Field(foreign_key="user.id")


class PaymentCreate(BaseModel):
    payee_name: str
    amount: float
    payment_method: str = Field(default="bank_transfer")
    note: Optional[str] = None


class PaymentRead(PaymentBase):
    id: int
    project_id: int
    created_by_id: int


class ProjectDashboardRead(BaseModel):
    project_id: int
    project_name: str
    budget: Optional[float] = None
    total_cost: float
    total_paid: float
    outstanding_balance: float
    budget_variance: Optional[float] = None
    completion_percent: float
    work_item_count: int
    completed_work_items: int
    task_counts: dict[str, int]
    overdue_tasks: int
    issue_counts: dict[str, int]
    change_order_counts: dict[str, int]
    change_order_value: float
    photo_count: int
    site_report_count: int
    member_count: int
    members_by_role: dict[str, int]
    generated_at: datetime


class PortfolioDashboardRead(BaseModel):
    project_count: int
    total_budget: float
    total_cost: float
    total_paid: float
    outstanding_balance: float
    open_issues: int
    pending_change_orders: int
    generated_at: datetime


class ProjectReportItem(BaseModel):
    project_id: int
    project_name: str
    status: str
    budget: Optional[float] = None
    total_cost: float
    total_paid: float
    outstanding_balance: float
    completion_percent: float
    issue_count: int
    pending_change_orders: int


class ProjectActivityReportRead(BaseModel):
    period: str
    project_count: int
    total_budget: float
    total_cost: float
    total_paid: float
    outstanding_balance: float
    project_status_counts: dict[str, int]
    activity_counts: dict[str, int]
    projects: List[ProjectReportItem]
    generated_at: datetime


WorkItemTreeRead.model_rebuild()
