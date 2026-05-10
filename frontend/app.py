from datetime import date
from html import escape

import pandas as pd
import requests
import streamlit as st


API_URL = "https://worklog.elitemind.uk/project-api"

STATUSES = ["Not Started", "In Progress", "Blocked", "Completed"]
PRIORITIES = ["Low", "Medium", "High", "Urgent"]


st.set_page_config(page_title="Project Management Tool", layout="wide")


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

    hr {
        margin-top: 0.45rem !important;
        margin-bottom: 0.45rem !important;
    }

    .status-pill {
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-bottom: 0.35rem;
    }

    .pill-not-started { background: #475569; color: white; }
    .pill-progress { background: #2563eb; color: white; }
    .pill-blocked { background: #dc2626; color: white; }
    .pill-completed { background: #16a34a; color: white; }

    .priority-low { background: #64748b; color: white; }
    .priority-medium { background: #2563eb; color: white; }
    .priority-high { background: #f97316; color: white; }
    .priority-urgent { background: #dc2626; color: white; }

    .priority-badge {
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-top: 0.25rem;
        margin-bottom: 0.25rem;
    }

    .dashboard-card {
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-radius: 0.9rem;
        padding: 1rem;
        margin-bottom: 0.75rem;
    }

    .dashboard-card-title {
        font-size: 0.85rem;
        opacity: 0.75;
        margin-bottom: 0.25rem;
    }

    .dashboard-card-value {
        font-size: 2rem;
        font-weight: 700;
        line-height: 1.1;
    }

    div.stButton > button,
    div[data-testid="stFormSubmitButton"] button {
        padding: 0.35rem 0.8rem;
        font-size: 14px;
        min-height: 2.2rem;
        border-radius: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


st.title("📌 Project Management Tool")


def api_headers():
    token = st.session_state.get("access_token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def api_get(path):
    try:
        return requests.get(f"{API_URL}{path}", headers=api_headers(), timeout=20)
    except requests.RequestException as e:
        st.error(f"API connection error: {e}")
        return None


def api_post(path, payload):
    try:
        return requests.post(
            f"{API_URL}{path}",
            json=payload,
            headers=api_headers(),
            timeout=20,
        )
    except requests.RequestException as e:
        st.error(f"API connection error: {e}")
        return None


def api_put(path, payload):
    try:
        return requests.put(
            f"{API_URL}{path}",
            json=payload,
            headers=api_headers(),
            timeout=20,
        )
    except requests.RequestException as e:
        st.error(f"API connection error: {e}")
        return None


def api_delete(path):
    try:
        return requests.delete(f"{API_URL}{path}", headers=api_headers(), timeout=20)
    except requests.RequestException as e:
        st.error(f"API connection error: {e}")
        return None


if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "user" not in st.session_state:
    st.session_state.user = None

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"


def login_page():
    st.subheader("Login")

    email = st.text_input("Email", value="")
    password = st.text_input("Password", type="password", value="")

    if st.button("Login"):
        if not email or not password:
            st.warning("Enter email and password.")
            return

        try:
            response = requests.post(
                f"{API_URL}/login",
                json={"email": email, "password": password},
                timeout=20,
            )
        except requests.RequestException as e:
            st.error(f"API connection error: {e}")
            return

        if response.status_code == 200:
            data = response.json()
            st.session_state.logged_in = True
            st.session_state.access_token = data.get("access_token")
            st.session_state.user = data.get("user")
            st.success("Login successful.")
            st.rerun()
        else:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            st.error(f"Login failed: {detail}")


def get_users():
    response = api_get("/users")
    if response and response.status_code == 200:
        return response.json()
    return []


def get_tasks():
    response = api_get("/tasks")
    if response and response.status_code == 200:
        return response.json()
    return []


def get_audit_logs():
    response = api_get("/audit-logs")
    if response and response.status_code == 200:
        return response.json()
    return []


def sidebar():
    user = st.session_state.user or {}

    with st.sidebar:
        st.success(f"Logged in as {user.get('full_name', 'User')}")
        st.write(f"Role: {user.get('role', 'user')}")

        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.access_token = None
            st.session_state.user = None
            st.rerun()

        st.write("Menu")

        pages = ["Dashboard", "Kanban Board", "Create Task", "User Management", "Audit Logs"]

        if user.get("role") != "admin":
            pages = ["Dashboard", "Kanban Board", "Create Task"]

        page = st.radio(
            "",
            pages,
            index=pages.index(st.session_state.page)
            if st.session_state.page in pages
            else 0,
        )

        st.session_state.page = page


def dashboard_card(title, value):
    st.markdown(
        f"""
        <div class="dashboard-card">
            <div class="dashboard-card-title">{escape(str(title))}</div>
            <div class="dashboard-card-value">{escape(str(value))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def dashboard_page():
    st.subheader("Dashboard")

    tasks = get_tasks()

    if not tasks:
        st.info("No tasks found.")
        return

    df = pd.DataFrame(tasks)

    if "status" not in df.columns:
        df["status"] = ""

    if "priority" not in df.columns:
        df["priority"] = ""

    total_tasks = len(df)
    not_started = len(df[df["status"] == "Not Started"])
    in_progress = len(df[df["status"] == "In Progress"])
    blocked = len(df[df["status"] == "Blocked"])
    completed = len(df[df["status"] == "Completed"])
    urgent = len(df[df["priority"] == "Urgent"])

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        dashboard_card("Total Tasks", total_tasks)
    with col2:
        dashboard_card("Not Started", not_started)
    with col3:
        dashboard_card("In Progress", in_progress)
    with col4:
        dashboard_card("Blocked", blocked)
    with col5:
        dashboard_card("Completed", completed)
    with col6:
        dashboard_card("Urgent", urgent)

    st.divider()
    st.subheader("Task List")

    preferred_columns = [
        "id",
        "title",
        "description",
        "status",
        "priority",
        "due_date",
        "assigned_to_name",
        "created_by_name",
        "created_at",
        "updated_at",
    ]

    visible_columns = [col for col in preferred_columns if col in df.columns]
    table_df = df[visible_columns].copy() if visible_columns else df.copy()

    table_df = table_df.rename(
        columns={
            "id": "ID",
            "title": "Title",
            "description": "Description",
            "status": "Status",
            "priority": "Priority",
            "due_date": "Due Date",
            "assigned_to_name": "Assigned To",
            "created_by_name": "Created By",
            "created_at": "Created At",
            "updated_at": "Updated At",
        }
    )

    st.dataframe(table_df, use_container_width=True, hide_index=True)


def create_task_page():
    st.subheader("Create Task")

    users = get_users()

    if not users:
        st.warning("No users found. Create a user first.")
        return

    user_options = {
        f"{u.get('full_name')} ({u.get('role')})": u.get("id")
        for u in users
    }

    with st.form("create_task_form"):
        title = st.text_input("Task Title", placeholder="Enter task title")
        description = st.text_area(
            "Description",
            placeholder="Enter task description",
            height=140,
        )

        col1, col2 = st.columns(2)

        with col1:
            status = st.selectbox("Status", STATUSES)

        with col2:
            priority = st.selectbox("Priority", PRIORITIES)

        col3, col4 = st.columns(2)

        with col3:
            due_date = st.date_input("Due Date", value=date.today())

        with col4:
            assigned_to_label = st.selectbox("Assign To", list(user_options.keys()))

        submitted = st.form_submit_button("Save Task")

        if submitted:
            if not title.strip():
                st.error("Task title is required.")
                return

            payload = {
                "title": title.strip(),
                "description": description.strip(),
                "status": status,
                "priority": priority,
                "due_date": due_date.strftime("%Y-%m-%d"),
                "assigned_to_id": user_options[assigned_to_label],
            }

            response = api_post("/tasks", payload)

            if response and response.status_code in [200, 201]:
                st.success("Task created successfully.")
                st.rerun()
            else:
                error = response.text if response else "No response from API"
                st.error(f"Failed to create task: {error}")


def get_status_pill_class(status):
    if status == "Not Started":
        return "pill-not-started"
    if status == "In Progress":
        return "pill-progress"
    if status == "Blocked":
        return "pill-blocked"
    if status == "Completed":
        return "pill-completed"
    return "pill-not-started"


def get_priority_class(priority):
    if priority == "Low":
        return "priority-low"
    if priority == "Medium":
        return "priority-medium"
    if priority == "High":
        return "priority-high"
    if priority == "Urgent":
        return "priority-urgent"
    return "priority-low"


def move_task(task_id, new_status):
    response = api_put(f"/tasks/{task_id}/status", {"status": new_status})

    if response and response.status_code == 200:
        st.success("Task updated.")
        st.rerun()

    error = response.text if response else "No response from API"
    st.error(f"Failed to update task: {error}")


def delete_task(task_id):
    response = api_delete(f"/tasks/{task_id}")

    if response and response.status_code in [200, 204]:
        st.success("Task deleted.")
        st.rerun()

    error = response.text if response else "No response from API"
    st.error(f"Failed to delete task: {error}")


def safe_due_date(value):
    try:
        if value:
            return pd.to_datetime(value).date()
    except Exception:
        pass
    return date.today()


def kanban_page():
    st.subheader("Kanban Board")

    tasks = get_tasks()

    if not tasks:
        st.info("No tasks found.")
        return

    with st.expander("🔎 Search and Filters"):
        search = st.text_input("Search tasks", placeholder="Search title or description")
        priority_filter = st.selectbox("Priority", ["All"] + PRIORITIES)
        assigned_filter = st.text_input("Assigned person contains", placeholder="Example: Simeon")

    filtered_tasks = []

    for task in tasks:
        title = str(task.get("title", ""))
        description = str(task.get("description", ""))
        priority = str(task.get("priority", ""))
        assigned_name = str(task.get("assigned_to_name", ""))

        matches_search = True
        matches_priority = True
        matches_assigned = True

        if search:
            search_lower = search.lower()
            matches_search = search_lower in title.lower() or search_lower in description.lower()

        if priority_filter != "All":
            matches_priority = priority == priority_filter

        if assigned_filter:
            matches_assigned = assigned_filter.lower() in assigned_name.lower()

        if matches_search and matches_priority and matches_assigned:
            filtered_tasks.append(task)

    cols = st.columns(len(STATUSES))

    for index, status in enumerate(STATUSES):
        with cols[index]:
            pill_class = get_status_pill_class(status)
            status_tasks = [task for task in filtered_tasks if task.get("status") == status]

            st.markdown(
                f"""
                <span class="status-pill {pill_class}">{escape(status)}</span>
                <div>{len(status_tasks)} task(s)</div>
                """,
                unsafe_allow_html=True,
            )

            if not status_tasks:
                st.caption("No tasks")

            for task in status_tasks:
                task_id = task.get("id")
                priority = str(task.get("priority", "Low"))
                priority_class = get_priority_class(priority)

                with st.container(border=True):
                    st.markdown(f"**{task.get('title', '')}**")

                    if task.get("description"):
                        st.caption(str(task.get("description", "")))

                    st.caption(f"👤 {task.get('assigned_to_name', 'Unassigned')}")

                    st.markdown(
                        f"""
                        <span class="priority-badge {priority_class}">
                            ⚡ {escape(priority)}
                        </span>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.caption(f"📅 {task.get('due_date', '')}")

                    col_edit, col_delete = st.columns(2)

                    with col_edit:
                        with st.expander("✏️ Edit"):
                            new_title = st.text_input(
                                "Title",
                                value=str(task.get("title", "")),
                                key=f"edit_title_{task_id}",
                            )

                            new_description = st.text_area(
                                "Description",
                                value=str(task.get("description", "")),
                                key=f"edit_description_{task_id}",
                            )

                            new_priority = st.selectbox(
                                "Priority",
                                PRIORITIES,
                                index=PRIORITIES.index(task.get("priority"))
                                if task.get("priority") in PRIORITIES
                                else 0,
                                key=f"edit_priority_{task_id}",
                            )

                            new_due_date = st.date_input(
                                "Due Date",
                                value=safe_due_date(task.get("due_date")),
                                key=f"edit_due_date_{task_id}",
                            )

                            if st.button("Save", key=f"save_edit_{task_id}"):
                                payload = {
                                    "title": new_title,
                                    "description": new_description,
                                    "status": task.get("status"),
                                    "priority": new_priority,
                                    "due_date": new_due_date.strftime("%Y-%m-%d"),
                                    "assigned_to_id": task.get("assigned_to_id"),
                                }

                                response = api_put(f"/tasks/{task_id}", payload)

                                if response and response.status_code == 200:
                                    st.success("Task updated.")
                                    st.rerun()

                                error = response.text if response else "No response from API"
                                st.error(f"Failed to update task: {error}")

                    with col_delete:
                        with st.expander("🗑️ Delete"):
                            st.warning("This will delete the task.")
                            confirm = st.checkbox("Confirm delete", key=f"confirm_delete_{task_id}")

                            if st.button("Delete", key=f"delete_{task_id}", disabled=not confirm):
                                delete_task(task_id)

                    with st.expander("💬 Comments"):
                        comment_text = st.text_area(
                            "Add comment",
                            key=f"comment_text_{task_id}",
                            placeholder="Write a comment...",
                        )

                        if st.button("Add Comment", key=f"add_comment_{task_id}"):
                            if not comment_text.strip():
                                st.warning("Comment cannot be empty.")
                            else:
                                response = api_post(
                                    "/comments",
                                    {
                                        "task_id": task_id,
                                        "user_id": st.session_state.user.get("id"),
                                        "comment": comment_text.strip(),
                                    },
                                )

                                if response and response.status_code in [200, 201]:
                                    st.success("Comment added.")
                                    st.rerun()
                                else:
                                    error = response.text if response else "No response from API"
                                    st.error(f"Failed to add comment: {error}")

                    with st.expander("📎 Files"):
                        st.caption("File upload section placeholder. Backend upload support can be connected next.")

                    current_index = STATUSES.index(status)
                    left_status = STATUSES[current_index - 1] if current_index > 0 else None
                    right_status = STATUSES[current_index + 1] if current_index < len(STATUSES) - 1 else None

                    left_col, right_col = st.columns(2)

                    with left_col:
                        if left_status:
                            if st.button("⬅️ Move Left", key=f"left_{task_id}"):
                                move_task(task_id, left_status)

                    with right_col:
                        if right_status:
                            if st.button("Move Right ➡️", key=f"right_{task_id}"):
                                move_task(task_id, right_status)


def user_management_page():
    st.subheader("User Management")

    current_user = st.session_state.user or {}

    if current_user.get("role") != "admin":
        st.warning("Only admins can access user management.")
        return

    users = get_users()

    st.write("Existing Users")

    if users:
        st.dataframe(pd.DataFrame(users), use_container_width=True)
    else:
        st.info("No users found.")

    st.divider()
    st.write("Create New User")

    with st.form("create_user_form"):
        full_name = st.text_input("Full Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["user", "admin"])

        submitted = st.form_submit_button("Create User")

        if submitted:
            if not full_name or not email or not password:
                st.error("Full name, email and password are required.")
                return

            payload = {
                "full_name": full_name.strip(),
                "email": email.strip(),
                "password": password,
                "role": role,
            }

            response = api_post("/users", payload)

            if response and response.status_code in [200, 201]:
                st.success("User created successfully.")
                st.rerun()
            else:
                error = response.text if response else "No response from API"
                st.error(f"Failed to create user: {error}")


def audit_logs_page():
    st.subheader("Audit Logs")

    current_user = st.session_state.user or {}

    if current_user.get("role") != "admin":
        st.warning("Only admins can view audit logs.")
        return

    logs = get_audit_logs()

    if not logs:
        st.info("No audit logs found.")
        return

    st.dataframe(pd.DataFrame(logs), use_container_width=True)


if not st.session_state.logged_in:
    login_page()
else:
    sidebar()

    if st.session_state.page == "Dashboard":
        dashboard_page()
    elif st.session_state.page == "Kanban Board":
        kanban_page()
    elif st.session_state.page == "Create Task":
        create_task_page()
    elif st.session_state.page == "User Management":
        user_management_page()
    elif st.session_state.page == "Audit Logs":
        audit_logs_page()