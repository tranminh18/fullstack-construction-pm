from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import (
    ChangeOrder,
    ChangeOrderCreate,
    ChangeOrderRead,
    CostEntry,
    CostEntryCreate,
    CostEntryRead,
    PaymentCreate,
    PaymentRead,
    PaymentRecord,
    User,
    WorkItem,
)
from app.security import (
    CAN_APPROVE_CHANGE_ORDER,
    CAN_SETTLE_PAYMENT,
    get_current_active_user,
    require_business_role,
    require_project_access,
    require_project_management,
)
from app.services import write_audit_log

router = APIRouter(tags=["finance"])


@router.post("/projects/{project_id}/change-orders", response_model=ChangeOrderRead)
def create_change_order(
    project_id: int,
    change_order: ChangeOrderCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    require_project_access(project_id, current_user, session)
    db_change_order = ChangeOrder(**change_order.model_dump(), project_id=project_id, requested_by_id=current_user.id)
    session.add(db_change_order)
    write_audit_log(
        session,
        "change_order.created",
        "ChangeOrder",
        None,
        project_id,
        current_user.id,
        {"title": db_change_order.title, "amount_change": db_change_order.amount_change},
    )
    session.commit()
    session.refresh(db_change_order)
    return db_change_order


@router.get("/projects/{project_id}/change-orders", response_model=List[ChangeOrderRead])
def list_change_orders(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    require_project_access(project_id, current_user, session)
    return session.exec(select(ChangeOrder).where(ChangeOrder.project_id == project_id)).all()


@router.patch("/change-orders/{change_order_id}/approve", response_model=ChangeOrderRead)
def approve_change_order(
    change_order_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    change_order = session.exec(select(ChangeOrder).where(ChangeOrder.id == change_order_id)).first()
    if not change_order:
        raise HTTPException(status_code=404, detail="Change order not found")
    require_project_access(change_order.project_id, current_user, session)
    require_business_role(current_user, CAN_APPROVE_CHANGE_ORDER)
    change_order.status = "approved"
    change_order.approved_by_id = current_user.id
    change_order.approved_at = datetime.utcnow()
    session.add(change_order)
    write_audit_log(
        session,
        "change_order.approved",
        "ChangeOrder",
        change_order.id,
        change_order.project_id,
        current_user.id,
        {"amount_change": change_order.amount_change},
    )
    session.commit()
    session.refresh(change_order)
    return change_order


@router.post("/projects/{project_id}/costs", response_model=CostEntryRead)
def create_cost_entry(
    project_id: int,
    cost_entry: CostEntryCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    require_project_management(project_id, current_user, session)
    if cost_entry.work_item_id is not None:
        workitem = session.exec(
            select(WorkItem).where(WorkItem.id == cost_entry.work_item_id, WorkItem.project_id == project_id)
        ).first()
        if not workitem:
            raise HTTPException(status_code=404, detail="WorkItem not found")
    db_cost_entry = CostEntry(**cost_entry.model_dump(), project_id=project_id, created_by_id=current_user.id)
    session.add(db_cost_entry)
    write_audit_log(
        session,
        "cost.created",
        "CostEntry",
        None,
        project_id,
        current_user.id,
        {"category": db_cost_entry.category, "amount": db_cost_entry.amount},
    )
    session.commit()
    session.refresh(db_cost_entry)
    return db_cost_entry


@router.get("/projects/{project_id}/costs", response_model=List[CostEntryRead])
def list_cost_entries(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    require_project_access(project_id, current_user, session)
    return session.exec(select(CostEntry).where(CostEntry.project_id == project_id)).all()


@router.post("/projects/{project_id}/payments", response_model=PaymentRead)
def create_payment_record(
    project_id: int,
    payment: PaymentCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    require_project_management(project_id, current_user, session)
    db_payment = PaymentRecord(**payment.model_dump(), project_id=project_id, created_by_id=current_user.id)
    session.add(db_payment)
    write_audit_log(
        session,
        "payment.created",
        "PaymentRecord",
        None,
        project_id,
        current_user.id,
        {"payee_name": db_payment.payee_name, "amount": db_payment.amount},
    )
    session.commit()
    session.refresh(db_payment)
    return db_payment


@router.get("/projects/{project_id}/payments", response_model=List[PaymentRead])
def list_payment_records(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    require_project_access(project_id, current_user, session)
    return session.exec(select(PaymentRecord).where(PaymentRecord.project_id == project_id)).all()


@router.patch("/payments/{payment_id}/settle", response_model=PaymentRead)
def settle_payment_record(
    payment_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session),
):
    payment = session.exec(select(PaymentRecord).where(PaymentRecord.id == payment_id)).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    require_project_access(payment.project_id, current_user, session)
    require_business_role(current_user, CAN_SETTLE_PAYMENT)
    payment.status = "paid"
    payment.paid_at = datetime.utcnow()
    session.add(payment)
    write_audit_log(
        session,
        "payment.settled",
        "PaymentRecord",
        payment.id,
        payment.project_id,
        current_user.id,
        {"amount": payment.amount},
    )
    session.commit()
    session.refresh(payment)
    return payment
