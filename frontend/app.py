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

    .task-card {
        border: 1px solid rgba(128, 128, 128, 0.35);
        border-radius: 0.75rem;
        padding: 1rem;
        margin-bottom: 0.75rem;
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

        page = st.radio(
            "",
            pages,
            index=pages.index(st.session_state.page),
        )

        st.session_state.page = page


def dashboard_page():
    st.subheader("Dashboard")

    tasks = get_tasks()

    if not tasks:
        st.info("No tasks found.")
        return

    df = pd.DataFrame(tasks)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Tasks", len(df))
    col2.metric("Not Started", len(df[df["status"] == "Not Started"]) if "status" in df else 0)
    col3.metric("In Progress", len(df[df["status"] == "In Progress"]) if "status" in df else 0)
    col4.metric("Completed", len(df[df["status"] == "Completed"]) if "status" in df else 0)

    st.divider()
    st.dataframe(df, use_container_width=True)


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


def kanban_page():
    st.subheader("Kanban Board")

    tasks = get_tasks()

    if not tasks:
        st.info("No tasks found.")
        return

    cols = st.columns(len(STATUSES))

    for index, status in enumerate(STATUSES):
        with cols[index]:
            st.markdown(f"### {status}")

            status_tasks = [task for task in tasks if task.get("status") == status]

            if not status_tasks:
                st.caption("No tasks")

            for task in status_tasks:
                task_id = task.get("id")
                title = escape(str(task.get("title", "")))
                description = escape(str(task.get("description", "")))
                priority = escape(str(task.get("priority", "")))
                due_date = escape(str(task.get("due_date", "")))

                st.markdown(
                    f"""
                    <div class="task-card">
                        <strong>{title}</strong><br>
                        <small>{description}</small><br><br>
                        <strong>Priority:</strong> {priority}<br>
                        <strong>Due:</strong> {due_date}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                new_status = st.selectbox(
                    "Move to",
                    STATUSES,
                    index=STATUSES.index(status),
                    key=f"status_{task_id}",
                )

                if st.button("Update", key=f"update_{task_id}"):
                    response = api_put(f"/tasks/{task_id}/status", {"status": new_status})

                    if response and response.status_code == 200:
                        st.success("Task updated.")
                        st.rerun()
                    else:
                        st.error("Failed to update task.")


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