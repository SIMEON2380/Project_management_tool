from pathlib import Path
import shutil

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import services
from .auth import (
    create_access_token,
    get_current_user,
    require_admin,
)
from .db import Base, engine, get_db


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Project Management API")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# =========================
# SCHEMAS
# =========================
class UserCreate(BaseModel):
    full_name: str
    email: str
    password: str
    role: str = "user"


class LoginRequest(BaseModel):
    email: str
    password: str


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    status: str = "Not Started"
    priority: str = "Medium"
    due_date: str = ""
    assigned_to_id: int | None = None
    created_by_id: int | None = None


class TaskStatusUpdate(BaseModel):
    status: str
    user_id: int | None = None


class CommentCreate(BaseModel):
    task_id: int
    user_id: int
    comment: str


# =========================
# HEALTH
# =========================
@app.get("/")
def root():
    return {"message": "Project Management API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


# =========================
# USERS / AUTH
# =========================
@app.post("/users")
def create_user(
    payload: UserCreate,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = services.create_user(
        db=db,
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
        role=payload.role,
    )

    if not user:
        raise HTTPException(status_code=400, detail="User already exists")

    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
    }


@app.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = services.authenticate_user(
        db=db,
        email=payload.email,
        password=payload.password,
    )

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(
        data={
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
        }
    )

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
        },
    }


@app.get("/users")
def list_users(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = services.get_users(db)

    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
        }
        for user in users
    ]


# =========================
# TASKS
# =========================
@app.post("/tasks")
def create_task(
    payload: TaskCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = services.create_task(
        db=db,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        due_date=payload.due_date,
        assigned_to_id=payload.assigned_to_id,
        created_by_id=current_user["user_id"],
    )

    return task_response(task, db)


@app.get("/tasks")
def list_tasks(
    current_user: dict = Depends(get_current_user),
    status: str | None = None,
    priority: str | None = None,
    assigned_to_id: int | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    tasks = services.get_tasks(
        db=db,
        status=status,
        priority=priority,
        assigned_to_id=assigned_to_id,
        search=search,
    )

    return [task_response(task, db) for task in tasks]


@app.put("/tasks/{task_id}/status")
def update_task_status(
    task_id: int,
    payload: TaskStatusUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = services.update_task_status(
        db=db,
        task_id=task_id,
        status=payload.status,
        user_id=current_user["user_id"],
    )

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task_response(task, db)


@app.put("/tasks/{task_id}")
def update_task(
    task_id: int,
    payload: TaskCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = services.update_task(
        db=db,
        task_id=task_id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        due_date=payload.due_date,
        assigned_to_id=payload.assigned_to_id,
        user_id=current_user["user_id"],
    )

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task_response(task, db)


@app.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    task = services.delete_task(
        db=db,
        task_id=task_id,
        user_id=current_user["user_id"],
    )

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"message": "Task deleted successfully"}


# =========================
# COMMENTS
# =========================
@app.post("/comments")
def add_comment(
    payload: CommentCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comment = services.add_comment(
        db=db,
        task_id=payload.task_id,
        user_id=current_user["user_id"],
        comment=payload.comment,
    )

    user = services.get_user_by_id(db, comment.user_id)

    return {
        "id": comment.id,
        "task_id": comment.task_id,
        "user_id": comment.user_id,
        "user_name": user.full_name if user else "Unknown User",
        "comment": comment.comment,
        "created_at": str(comment.created_at),
    }


@app.get("/tasks/{task_id}/comments")
def get_task_comments(
    task_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comments = services.get_task_comments(
        db=db,
        task_id=task_id,
    )

    return [
        {
            "id": comment["id"],
            "task_id": comment["task_id"],
            "user_id": comment["user_id"],
            "user_name": comment["user_name"],
            "comment": comment["comment"],
            "created_at": str(comment["created_at"]),
        }
        for comment in comments
    ]


@app.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comment = services.delete_comment(
        db=db,
        comment_id=comment_id,
        user_id=current_user["user_id"],
    )

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    return {"message": "Comment deleted successfully"}


# =========================
# FILE UPLOADS
# =========================
@app.post("/tasks/{task_id}/files")
def upload_task_file(
    task_id: int,
    uploaded_by_id: int = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = services.get_task_by_id(db, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    safe_filename = file.filename.replace("/", "_").replace("\\", "_")
    stored_filename = f"task_{task_id}_{safe_filename}"
    filepath = UPLOAD_DIR / stored_filename

    with filepath.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    task_file = services.add_task_file(
        db=db,
        task_id=task_id,
        filename=file.filename,
        filepath=str(filepath),
        uploaded_by_id=current_user["user_id"],
    )

    return {
        "id": task_file.id,
        "task_id": task_file.task_id,
        "filename": task_file.filename,
        "filepath": task_file.filepath,
        "uploaded_by_id": task_file.uploaded_by_id,
        "uploaded_at": str(task_file.uploaded_at),
    }


@app.get("/tasks/{task_id}/files")
def get_task_files(
    task_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    files = services.get_task_files(db=db, task_id=task_id)

    return [
        {
            "id": file.id,
            "task_id": file.task_id,
            "filename": file.filename,
            "filepath": file.filepath,
            "uploaded_by_id": file.uploaded_by_id,
            "uploaded_at": str(file.uploaded_at),
        }
        for file in files
    ]


@app.delete("/files/{file_id}")
def delete_task_file(
    file_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task_file = services.delete_task_file(
        db=db,
        file_id=file_id,
        user_id=current_user["user_id"],
    )

    if not task_file:
        raise HTTPException(status_code=404, detail="File not found")

    return {"message": "File deleted successfully"}


# =========================
# DASHBOARD / AUDIT
# =========================
@app.get("/dashboard/stats")
def get_dashboard_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return services.get_dashboard_stats(db)


@app.get("/audit-logs")
def get_audit_logs(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    logs = services.get_audit_logs(db)

    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "details": log.details,
            "created_at": str(log.created_at),
        }
        for log in logs
    ]


# =========================
# RESPONSE HELPERS
# =========================
def task_response(task, db: Session):
    assigned_to_name = None
    created_by_name = None

    if task.assigned_to_id:
        assigned_user = services.get_user_by_id(db, task.assigned_to_id)
        assigned_to_name = assigned_user.full_name if assigned_user else None

    if task.created_by_id:
        created_user = services.get_user_by_id(db, task.created_by_id)
        created_by_name = created_user.full_name if created_user else None

    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "due_date": task.due_date,
        "assigned_to_id": task.assigned_to_id,
        "assigned_to_name": assigned_to_name,
        "created_by_id": task.created_by_id,
        "created_by_name": created_by_name,
        "created_at": str(task.created_at),
        "updated_at": str(task.updated_at) if task.updated_at else None,
    }