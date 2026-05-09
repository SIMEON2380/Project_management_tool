from datetime import date, datetime
from html import escape

import pandas as pd
import requests
import streamlit as st


API_URL = "http://127.0.0.1:8000"

STATUSES = ["Not Started", "In Progress", "Blocked", "Completed"]
PRIORITIES = ["Low", "Medium", "High", "Urgent"]


st.set_page_config(page_title="Project Management Tool", layout="wide")
st.title("📌 Project Management Tool")

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
        padding-bottom: 1rem;
        max-width: 95%;
    }

    h1 {
        margin-top: 0rem;
        margin-bottom: 1rem;
        line-height: 1.2;
    }

    div[data-testid="stVerticalBlock"] {
        gap: 0.45rem;
    }

    div[data-testid="stExpander"] {
        margin-top: -0.25rem;
        margin-bottom: -0.25rem;
    }

    div.stButton > button {
        padding: 0.25rem 0.6rem;
        font-size: 13px;
        min-height: 2.1rem;
        border-radius: 0.5rem;
    }

    hr {
        margin-top: 0.45rem !important;
        margin-bottom: 0.45rem !important;
    }

    p {
        margin-bottom: 0.25rem;
    }

    section[data-testid="stSidebar"] {
        min-width: 330px;
        max-width: 330px;
    }

    .task-title {
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 2px;
        line-height: 1.2;
    }

    .badge {
        display: inline-block;
        padding: 3px 9px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
        margin-top: 4px;
        margin-bottom: 4px;
    }

    .badge-low {
        background-color: #374151;
        color: #e5e7eb;
    }

    .badge-medium {
        background-color: #1d4ed8;
        color: #dbeafe;
    }

    .badge-high {
        background-color: #ea580c;
        color: #ffedd5;
    }

    .badge-urgent {
        background-color: #dc2626;
        color: #fee2e2;
    }

    .overdue {
        color: #f87171;
        font-weight: 700;
        font-size: 13px;
    }

    .due-normal {
        color: #d1d5db;
        font-size: 13px;
    }

    .status-pill {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
        margin-bottom: 6px;
    }

    .status-not-started {
        background-color: #374151;
        color: #e5e7eb;
    }

    .status-in-progress {
        background-color: #1d4ed8;
        color: #dbeafe;
    }

    .status-blocked {
        background-color: #991b1b;
        color: #fee2e2;
    }

    .status-completed {
        background-color: #166534;
        color: #dcfce7;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


if "user" not in st.session_state:
    st.session_state.user = None

if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "selected_task_id" not in st.session_state:
    st.session_state.selected_task_id = None


# =========================
# AUTH HEADERS
# =========================
def auth_headers():
    if not st.session_state.access_token:
        return {}

    return {"Authorization": f"Bearer {st.session_state.access_token}"}


# =========================
# UI HELPERS
# =========================
def priority_badge(priority):
    safe_priority = escape(priority or "Medium")
    css_class = {
        "Low": "badge-low",
        "Medium": "badge-medium",
        "High": "badge-high",
        "Urgent": "badge-urgent",
    }.get(priority, "badge-medium")

    return f"<span class='badge {css_class}'>⚡ {safe_priority}</span>"


def status_badge(status):
    safe_status = escape(status or "Not Started")
    css_class = {
        "Not Started": "status-not-started",
        "In Progress": "status-in-progress",
        "Blocked": "status-blocked",
        "Completed": "status-completed",
    }.get(status, "status-not-started")

    return f"<span class='status-pill {css_class}'>{safe_status}</span>"


def parse_due_date(due_date):
    if not due_date:
        return None

    try:
        return datetime.strptime(str(due_date), "%Y-%m-%d").date()
    except ValueError:
        return None


def due_date_display(task):
    due_date_value = task.get("due_date")
    parsed_date = parse_due_date(due_date_value)

    if not due_date_value:
        return "<span class='due-normal'>📅 No due date</span>"

    if parsed_date and parsed_date < date.today() and task.get("status") != "Completed":
        return f"<span class='overdue'>⚠️ Overdue: {escape(str(due_date_value))}</span>"

    return f"<span class='due-normal'>📅 {escape(str(due_date_value))}</span>"


# =========================
# API REQUEST HELPER
# =========================
def safe_request(method, url, **kwargs):
    try:
        return requests.request(method, url, timeout=10, **kwargs)

    except requests.exceptions.ConnectionError:
        st.error(
            "Backend is not running. Start FastAPI with: "
            "`uvicorn backend.main:app --reload`"
        )
        return None

    except requests.exceptions.Timeout:
        st.error("Backend request timed out.")
        return None

    except requests.exceptions.RequestException as error:
        st.error(f"API error: {error}")
        return None


# =========================
# LOGIN
# =========================
def login():
    st.subheader("Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        response = safe_request(
            "POST",
            f"{API_URL}/login",
            json={"email": email, "password": password},
        )

        if response and response.status_code == 200:
            payload = response.json()
            st.session_state.user = payload["user"]
            st.session_state.access_token = payload["access_token"]
            st.success("Login successful")
            st.rerun()

        elif response:
            st.error("Invalid credentials")


# =========================
# API HELPERS
# =========================
def get_tasks(params=None):
    response = safe_request(
        "GET",
        f"{API_URL}/tasks",
        params=params or {},
        headers=auth_headers(),
    )

    if response and response.status_code == 200:
        return response.json()

    if response:
        st.error(response.text)

    return []


def get_users():
    response = safe_request(
        "GET",
        f"{API_URL}/users",
        headers=auth_headers(),
    )

    if response and response.status_code == 200:
        return response.json()

    return []


def create_user_admin(full_name, email, password, role):
    response = safe_request(
        "POST",
        f"{API_URL}/users",
        json={
            "full_name": full_name,
            "email": email,
            "password": password,
            "role": role,
        },
        headers=auth_headers(),
    )

    if response and response.status_code == 200:
        st.success("User created")
        st.rerun()

    elif response:
        st.error(response.text)


def get_comments(task_id):
    response = safe_request(
        "GET",
        f"{API_URL}/tasks/{task_id}/comments",
        headers=auth_headers(),
    )

    if response and response.status_code == 200:
        return response.json()

    return []


def get_files(task_id):
    response = safe_request(
        "GET",
        f"{API_URL}/tasks/{task_id}/files",
        headers=auth_headers(),
    )

    if response and response.status_code == 200:
        return response.json()

    return []


def get_dashboard_stats():
    response = safe_request(
        "GET",
        f"{API_URL}/dashboard/stats",
        headers=auth_headers(),
    )

    if response and response.status_code == 200:
        return response.json()

    return {}


def get_audit_logs():
    response = safe_request(
        "GET",
        f"{API_URL}/audit-logs",
        headers=auth_headers(),
    )

    if response and response.status_code == 200:
        return response.json()

    return []


def add_comment(task_id, comment):
    response = safe_request(
        "POST",
        f"{API_URL}/comments",
        json={
            "task_id": task_id,
            "user_id": st.session_state.user["id"],
            "comment": comment,
        },
        headers=auth_headers(),
    )

    if response and response.status_code == 200:
        st.success("Comment added")
        st.rerun()

    elif response:
        st.error(response.text)


def delete_comment(comment_id):
    response = safe_request(
        "DELETE",
        f"{API_URL}/comments/{comment_id}",
        headers=auth_headers(),
    )

    if response and response.status_code == 200:
        st.success("Comment deleted")
        st.rerun()

    elif response:
        st.error(response.text)


def upload_file(task_id, uploaded_file):
    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            uploaded_file.type,
        )
    }

    data = {"uploaded_by_id": st.session_state.user["id"]}

    response = safe_request(
        "POST",
        f"{API_URL}/tasks/{task_id}/files",
        files=files,
        data=data,
        headers=auth_headers(),
    )

    if response and response.status_code == 200:
        st.success("File uploaded")
        st.rerun()

    elif response:
        st.error(response.text)


def delete_file(file_id):
    response = safe_request(
        "DELETE",
        f"{API_URL}/files/{file_id}",
        headers=auth_headers(),
    )

    if response and response.status_code == 200:
        st.success("File deleted")
        st.rerun()

    elif response:
        st.error(response.text)


def move_task(task_id, new_status):
    response = safe_request(
        "PUT",
        f"{API_URL}/tasks/{task_id}/status",
        json={
            "status": new_status,
            "user_id": st.session_state.user["id"],
        },
        headers=auth_headers(),
    )

    if response and response.status_code == 200:
        st.rerun()

    elif response:
        st.error(response.text)


def delete_task(task_id):
    response = safe_request(
        "DELETE",
        f"{API_URL}/tasks/{task_id}",
        headers=auth_headers(),
    )

    if response and response.status_code == 200:
        st.session_state.selected_task_id = None
        st.success("Task deleted")
        st.rerun()

    elif response:
        st.error(response.text)


def update_task(task_id, payload):
    response = safe_request(
        "PUT",
        f"{API_URL}/tasks/{task_id}",
        json=payload,
        headers=auth_headers(),
    )

    if response and response.status_code == 200:
        st.session_state.selected_task_id = None
        st.success("Task updated")
        st.rerun()

    elif response:
        st.error(response.text)


# =========================
# DASHBOARD
# =========================
def render_dashboard():
    st.subheader("Dashboard")

    stats = get_dashboard_stats()

    if not stats:
        st.info("No dashboard data yet.")
        return

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Tasks", stats.get("total_tasks", 0))
    col2.metric("Completed", stats.get("completed_tasks", 0))
    col3.metric("In Progress", stats.get("in_progress_tasks", 0))
    col4.metric("Blocked", stats.get("blocked_tasks", 0))

    col5, col6, col7 = st.columns(3)

    col5.metric("Not Started", stats.get("not_started_tasks", 0))
    col6.metric("Urgent", stats.get("urgent_tasks", 0))
    col7.metric("High Priority", stats.get("high_priority_tasks", 0))

    workload = stats.get("workload", [])

    if workload:
        st.subheader("Workload by User")
        workload_df = pd.DataFrame(workload)
        st.bar_chart(workload_df.set_index("user_name"))


# =========================
# USER MANAGEMENT
# =========================
def render_user_management():
    st.subheader("Admin - User Management")

    with st.form("create_user_form"):
        full_name = st.text_input("Full Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["user", "admin"])

        submitted = st.form_submit_button("Create User")

        if submitted:
            if not full_name.strip() or not email.strip() or not password.strip():
                st.error("Full name, email, and password are required.")
            else:
                create_user_admin(
                    full_name=full_name,
                    email=email,
                    password=password,
                    role=role,
                )

    st.divider()

    users = get_users()

    if users:
        st.subheader("Existing Users")
        users_df = pd.DataFrame(users)
        st.dataframe(users_df, use_container_width=True, hide_index=True)
    else:
        st.info("No users found.")


# =========================
# TASK CREATION
# =========================
def create_task():
    st.subheader("Create Task")

    title = st.text_input("Task Title")
    description = st.text_area("Description")
    status = st.selectbox("Status", STATUSES)
    priority = st.selectbox("Priority", PRIORITIES)
    due_date = st.date_input("Due Date")

    users = get_users()

    user_options = {
        f"{user['full_name']} ({user['role']})": user["id"]
        for user in users
    }

    selected_user = st.selectbox(
        "Assign To",
        list(user_options.keys()) if user_options else ["No users"],
    )

    if st.button("Save Task"):
        if not title.strip():
            st.error("Task title is required.")
            return

        assigned_to_id = (
            user_options[selected_user]
            if selected_user in user_options
            else None
        )

        response = safe_request(
            "POST",
            f"{API_URL}/tasks",
            json={
                "title": title,
                "description": description,
                "status": status,
                "priority": priority,
                "due_date": str(due_date),
                "assigned_to_id": assigned_to_id,
                "created_by_id": st.session_state.user["id"],
            },
            headers=auth_headers(),
        )

        if response and response.status_code == 200:
            st.success("Task created")
            st.rerun()

        elif response:
            st.error(response.text)


# =========================
# FILTERS
# =========================
def build_task_filters():
    users = get_users()

    with st.expander("🔎 Search and Filters", expanded=False):
        search = st.text_input("Search title or description")

        col1, col2, col3 = st.columns(3)

        with col1:
            status_filter = st.selectbox("Status", ["All"] + STATUSES)

        with col2:
            priority_filter = st.selectbox("Priority", ["All"] + PRIORITIES)

        user_options = {"All": None}

        for user in users:
            user_options[f"{user['full_name']} ({user['role']})"] = user["id"]

        with col3:
            assigned_user = st.selectbox("Assigned To", list(user_options.keys()))

    params = {}

    if search.strip():
        params["search"] = search.strip()

    if status_filter != "All":
        params["status"] = status_filter

    if priority_filter != "All":
        params["priority"] = priority_filter

    if user_options[assigned_user] is not None:
        params["assigned_to_id"] = user_options[assigned_user]

    return params


# =========================
# SIDEBAR EDIT PANEL
# =========================
def render_sidebar_edit_panel(tasks):
    selected_task = None

    for task in tasks:
        if task["id"] == st.session_state.selected_task_id:
            selected_task = task
            break

    if not selected_task:
        return

    st.sidebar.divider()
    st.sidebar.subheader("Edit Task")

    users = get_users()

    user_options = {"Unassigned": None}

    for user in users:
        user_options[f"{user['full_name']} ({user['role']})"] = user["id"]

    current_assigned_id = selected_task.get("assigned_to_id")
    selected_user_label = "Unassigned"

    for label, user_id in user_options.items():
        if user_id == current_assigned_id:
            selected_user_label = label
            break

    new_title = st.sidebar.text_input(
        "Title",
        value=selected_task["title"],
        key=f"sidebar_title_{selected_task['id']}",
    )

    new_description = st.sidebar.text_area(
        "Description",
        value=selected_task.get("description") or "",
        key=f"sidebar_description_{selected_task['id']}",
    )

    current_status = selected_task.get("status") or "Not Started"
    current_priority = selected_task.get("priority") or "Medium"

    new_status = st.sidebar.selectbox(
        "Status",
        STATUSES,
        index=STATUSES.index(current_status)
        if current_status in STATUSES
        else 0,
        key=f"sidebar_status_{selected_task['id']}",
    )

    new_priority = st.sidebar.selectbox(
        "Priority",
        PRIORITIES,
        index=PRIORITIES.index(current_priority)
        if current_priority in PRIORITIES
        else 1,
        key=f"sidebar_priority_{selected_task['id']}",
    )

    selected_user = st.sidebar.selectbox(
        "Assigned To",
        list(user_options.keys()),
        index=list(user_options.keys()).index(selected_user_label),
        key=f"sidebar_assigned_{selected_task['id']}",
    )

    if st.sidebar.button("💾 Save Task", use_container_width=True):
        if not new_title.strip():
            st.sidebar.error("Task title is required.")
            return

        update_task(
            selected_task["id"],
            {
                "title": new_title,
                "description": new_description,
                "status": new_status,
                "priority": new_priority,
                "due_date": selected_task.get("due_date") or "",
                "assigned_to_id": user_options[selected_user],
                "created_by_id": st.session_state.user["id"],
            },
        )

    if st.sidebar.button("Close Edit Panel", use_container_width=True):
        st.session_state.selected_task_id = None
        st.rerun()


# =========================
# COMMENTS
# =========================
def render_comments(task):
    task_id = task["id"]

    with st.expander("💬 Comments", expanded=False):
        comments = get_comments(task_id)

        if comments:
            for comment in comments:
                with st.container(border=True):
                    st.write(comment["comment"])
                    st.caption(
                        f"👤 {comment.get('user_name', 'Unknown User')} • {comment['created_at']}"
                    )

                    can_delete = (
                        st.session_state.user["role"] == "admin"
                        or comment["user_id"] == st.session_state.user["id"]
                    )

                    if can_delete:
                        if st.button(
                            "🗑️ Delete Comment",
                            key=f"delete_comment_{comment['id']}",
                        ):
                            delete_comment(comment["id"])
        else:
            st.caption("No comments yet.")

        comment_text = st.text_area(
            "Add comment",
            key=f"comment_text_{task_id}",
        )

        if st.button("Post Comment", key=f"post_comment_{task_id}"):
            if comment_text.strip():
                add_comment(task_id, comment_text)
            else:
                st.warning("Write a comment first.")


# =========================
# FILES
# =========================
def render_files(task):
    task_id = task["id"]

    with st.expander("📎 Files", expanded=False):
        files = get_files(task_id)

        if files:
            for file in files:
                with st.container(border=True):
                    st.write(f"📄 {file['filename']}")
                    st.caption(f"Uploaded: {file['uploaded_at']}")

                    can_delete = (
                        st.session_state.user["role"] == "admin"
                        or file["uploaded_by_id"] == st.session_state.user["id"]
                    )

                    if can_delete:
                        if st.button(
                            "🗑️ Delete File",
                            key=f"delete_file_{file['id']}",
                        ):
                            delete_file(file["id"])
        else:
            st.caption("No files uploaded yet.")

        uploaded_file = st.file_uploader(
            "Upload file",
            key=f"upload_file_{task_id}",
        )

        if uploaded_file:
            if st.button("Upload", key=f"upload_btn_{task_id}"):
                upload_file(task_id, uploaded_file)


# =========================
# KANBAN BOARD
# =========================
def render_task_card(task, status):
    task_id = task["id"]
    task_title = escape(task.get("title") or "Untitled task")
    task_description = escape(task.get("description") or "No description added.")
    assigned_to = escape(task.get("assigned_to_name") or "Unassigned")

    with st.container(border=True):
        st.markdown(
            f"""
            <div class="task-title">{task_title}</div>
            <div style="font-size:13px;color:#9ca3af;margin-bottom:4px;">
                {task_description}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.caption(f"👤 {assigned_to}")

        st.markdown(priority_badge(task.get("priority")), unsafe_allow_html=True)
        st.markdown(due_date_display(task), unsafe_allow_html=True)

        btn_col1, btn_col2 = st.columns(2)

        with btn_col1:
            if st.button(
                "✏️ Edit",
                key=f"edit_btn_{task_id}",
                use_container_width=True,
            ):
                st.session_state.selected_task_id = task_id
                st.rerun()

        with btn_col2:
            if st.button(
                "🗑️ Delete",
                key=f"delete_btn_{task_id}",
                use_container_width=True,
            ):
                delete_task(task_id)

        render_comments(task)
        render_files(task)

        st.divider()

        move_col1, move_col2 = st.columns(2)
        status_index = STATUSES.index(status)

        with move_col1:
            if status_index > 0:
                if st.button(
                    "⬅️",
                    key=f"left_{task_id}",
                    use_container_width=True,
                ):
                    move_task(task_id, STATUSES[status_index - 1])

        with move_col2:
            if status_index < len(STATUSES) - 1:
                if st.button(
                    "➡️",
                    key=f"right_{task_id}",
                    use_container_width=True,
                ):
                    move_task(task_id, STATUSES[status_index + 1])


def render_kanban():
    st.subheader("Kanban Board")

    params = build_task_filters()
    tasks = get_tasks(params=params)

    render_sidebar_edit_panel(tasks)

    columns = st.columns(len(STATUSES))

    for index, status in enumerate(STATUSES):
        with columns[index]:
            status_tasks = [
                task for task in tasks
                if task["status"] == status
            ]

            st.markdown(status_badge(status), unsafe_allow_html=True)
            st.caption(f"{len(status_tasks)} task(s)")

            for task in status_tasks:
                render_task_card(task, status)


# =========================
# AUDIT LOGS
# =========================
def render_audit_logs():
    st.subheader("Audit Logs")

    logs = get_audit_logs()

    if not logs:
        st.info("No audit logs yet.")
        return

    logs_df = pd.DataFrame(logs)
    st.dataframe(logs_df, use_container_width=True, hide_index=True)


# =========================
# MAIN APP
# =========================
if st.session_state.user is None:
    login()

else:
    st.sidebar.success(
        f"Logged in as {st.session_state.user['full_name']}"
    )
    st.sidebar.caption(f"Role: {st.session_state.user['role']}")

    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.session_state.access_token = None
        st.session_state.selected_task_id = None
        st.rerun()

    menu_options = [
        "Dashboard",
        "Kanban Board",
        "Create Task",
    ]

    if st.session_state.user["role"] == "admin":
        menu_options.append("User Management")
        menu_options.append("Audit Logs")

    menu = st.sidebar.radio("Menu", menu_options)

    if menu == "Dashboard":
        render_dashboard()

    elif menu == "Create Task":
        create_task()

    elif menu == "Kanban Board":
        render_kanban()

    elif menu == "User Management":
        render_user_management()

    elif menu == "Audit Logs":
        render_audit_logs()