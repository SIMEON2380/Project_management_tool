from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from . import models
from .auth import hash_password, verify_password


# =========================
# AUDIT LOGS
# =========================
def create_audit_log(
    db: Session,
    user_id: int | None,
    action: str,
    details: str = "",
):
    log = models.AuditLog(
        user_id=user_id,
        action=action,
        details=details,
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return log


def get_audit_logs(db: Session):
    return (
        db.query(models.AuditLog)
        .order_by(models.AuditLog.created_at.desc())
        .all()
    )


# =========================
# USERS
# =========================
def create_user(
    db: Session,
    full_name: str,
    email: str,
    password: str,
    role: str = "user",
):
    existing_user = (
        db.query(models.User)
        .filter(models.User.email == email)
        .first()
    )

    if existing_user:
        return None

    user = models.User(
        full_name=full_name,
        email=email,
        password_hash=hash_password(password),
        role=role,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    create_audit_log(
        db=db,
        user_id=user.id,
        action="USER_CREATED",
        details=f"User created: {user.full_name} ({user.email})",
    )

    return user


def authenticate_user(
    db: Session,
    email: str,
    password: str,
):
    user = (
        db.query(models.User)
        .filter(models.User.email == email)
        .first()
    )

    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    create_audit_log(
        db=db,
        user_id=user.id,
        action="USER_LOGIN",
        details=f"User logged in: {user.email}",
    )

    return user


def get_users(db: Session):
    return (
        db.query(models.User)
        .order_by(models.User.full_name)
        .all()
    )


def get_user_by_id(db: Session, user_id: int):
    return (
        db.query(models.User)
        .filter(models.User.id == user_id)
        .first()
    )


# =========================
# TASKS
# =========================
def create_task(
    db: Session,
    title: str,
    description: str,
    status: str,
    priority: str,
    due_date: str,
    assigned_to_id: int | None,
    created_by_id: int | None,
):
    task = models.Task(
        title=title,
        description=description,
        status=status,
        priority=priority,
        due_date=due_date,
        assigned_to_id=assigned_to_id,
        created_by_id=created_by_id,
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    create_audit_log(
        db=db,
        user_id=created_by_id,
        action="TASK_CREATED",
        details=f"Task created: {task.title}",
    )

    return task


def get_tasks(
    db: Session,
    status: str | None = None,
    priority: str | None = None,
    assigned_to_id: int | None = None,
    search: str | None = None,
):
    query = db.query(models.Task)

    if status:
        query = query.filter(models.Task.status == status)

    if priority:
        query = query.filter(models.Task.priority == priority)

    if assigned_to_id:
        query = query.filter(models.Task.assigned_to_id == assigned_to_id)

    if search:
        query = query.filter(
            or_(
                models.Task.title.ilike(f"%{search}%"),
                models.Task.description.ilike(f"%{search}%"),
            )
        )

    return (
        query.order_by(models.Task.created_at.desc())
        .all()
    )


def get_task_by_id(db: Session, task_id: int):
    return (
        db.query(models.Task)
        .filter(models.Task.id == task_id)
        .first()
    )


def update_task_status(
    db: Session,
    task_id: int,
    status: str,
    user_id: int | None = None,
):
    task = get_task_by_id(db, task_id)

    if not task:
        return None

    old_status = task.status
    task.status = status
    task.updated_at = func.now()

    db.commit()
    db.refresh(task)

    create_audit_log(
        db=db,
        user_id=user_id,
        action="TASK_STATUS_UPDATED",
        details=f"Task '{task.title}' moved from {old_status} to {status}",
    )

    return task


def update_task(
    db: Session,
    task_id: int,
    title: str,
    description: str,
    status: str,
    priority: str,
    due_date: str,
    assigned_to_id: int | None,
    user_id: int | None = None,
):
    task = get_task_by_id(db, task_id)

    if not task:
        return None

    task.title = title
    task.description = description
    task.status = status
    task.priority = priority
    task.due_date = due_date
    task.assigned_to_id = assigned_to_id
    task.updated_at = func.now()

    db.commit()
    db.refresh(task)

    create_audit_log(
        db=db,
        user_id=user_id,
        action="TASK_UPDATED",
        details=f"Task updated: {task.title}",
    )

    return task


def delete_task(
    db: Session,
    task_id: int,
    user_id: int | None = None,
):
    task = get_task_by_id(db, task_id)

    if not task:
        return None

    task_title = task.title

    db.query(models.Comment).filter(models.Comment.task_id == task_id).delete()
    db.query(models.TaskFile).filter(models.TaskFile.task_id == task_id).delete()

    db.delete(task)
    db.commit()

    create_audit_log(
        db=db,
        user_id=user_id,
        action="TASK_DELETED",
        details=f"Task deleted: {task_title}",
    )

    return task


# =========================
# COMMENTS
# =========================
def add_comment(
    db: Session,
    task_id: int,
    user_id: int,
    comment: str,
):
    new_comment = models.Comment(
        task_id=task_id,
        user_id=user_id,
        comment=comment,
    )

    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    create_audit_log(
        db=db,
        user_id=user_id,
        action="COMMENT_ADDED",
        details=f"Comment added to task ID {task_id}",
    )

    return new_comment


def get_task_comments(
    db: Session,
    task_id: int,
):
    comments = (
        db.query(models.Comment)
        .filter(models.Comment.task_id == task_id)
        .order_by(models.Comment.created_at.desc())
        .all()
    )

    results = []

    for comment in comments:
        user = get_user_by_id(db, comment.user_id)

        results.append(
            {
                "id": comment.id,
                "task_id": comment.task_id,
                "user_id": comment.user_id,
                "user_name": user.full_name if user else "Unknown User",
                "comment": comment.comment,
                "created_at": comment.created_at,
            }
        )

    return results


def delete_comment(
    db: Session,
    comment_id: int,
    user_id: int | None = None,
):
    comment = (
        db.query(models.Comment)
        .filter(models.Comment.id == comment_id)
        .first()
    )

    if not comment:
        return None

    task_id = comment.task_id

    db.delete(comment)
    db.commit()

    create_audit_log(
        db=db,
        user_id=user_id,
        action="COMMENT_DELETED",
        details=f"Comment deleted from task ID {task_id}",
    )

    return comment


# =========================
# FILES
# =========================
def add_task_file(
    db: Session,
    task_id: int,
    filename: str,
    filepath: str,
    uploaded_by_id: int,
):
    task_file = models.TaskFile(
        task_id=task_id,
        filename=filename,
        filepath=filepath,
        uploaded_by_id=uploaded_by_id,
    )

    db.add(task_file)
    db.commit()
    db.refresh(task_file)

    create_audit_log(
        db=db,
        user_id=uploaded_by_id,
        action="FILE_UPLOADED",
        details=f"File uploaded to task ID {task_id}: {filename}",
    )

    return task_file


def get_task_files(
    db: Session,
    task_id: int,
):
    return (
        db.query(models.TaskFile)
        .filter(models.TaskFile.task_id == task_id)
        .order_by(models.TaskFile.uploaded_at.desc())
        .all()
    )


def delete_task_file(
    db: Session,
    file_id: int,
    user_id: int | None = None,
):
    task_file = (
        db.query(models.TaskFile)
        .filter(models.TaskFile.id == file_id)
        .first()
    )

    if not task_file:
        return None

    filename = task_file.filename

    db.delete(task_file)
    db.commit()

    create_audit_log(
        db=db,
        user_id=user_id,
        action="FILE_DELETED",
        details=f"File deleted: {filename}",
    )

    return task_file


# =========================
# DASHBOARD
# =========================
def get_dashboard_stats(db: Session):
    total_tasks = db.query(models.Task).count()

    completed_tasks = (
        db.query(models.Task)
        .filter(models.Task.status == "Completed")
        .count()
    )

    in_progress_tasks = (
        db.query(models.Task)
        .filter(models.Task.status == "In Progress")
        .count()
    )

    blocked_tasks = (
        db.query(models.Task)
        .filter(models.Task.status == "Blocked")
        .count()
    )

    not_started_tasks = (
        db.query(models.Task)
        .filter(models.Task.status == "Not Started")
        .count()
    )

    urgent_tasks = (
        db.query(models.Task)
        .filter(models.Task.priority == "Urgent")
        .count()
    )

    high_priority_tasks = (
        db.query(models.Task)
        .filter(models.Task.priority == "High")
        .count()
    )

    workload = (
        db.query(
            models.User.full_name,
            func.count(models.Task.id).label("task_count"),
        )
        .outerjoin(models.Task, models.User.id == models.Task.assigned_to_id)
        .group_by(models.User.id)
        .order_by(models.User.full_name)
        .all()
    )

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "in_progress_tasks": in_progress_tasks,
        "blocked_tasks": blocked_tasks,
        "not_started_tasks": not_started_tasks,
        "urgent_tasks": urgent_tasks,
        "high_priority_tasks": high_priority_tasks,
        "workload": [
            {
                "user_name": item.full_name,
                "task_count": item.task_count,
            }
            for item in workload
        ],
    }