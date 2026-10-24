from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base


DATABASE_URL = "sqlite:///./project_management.db"


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def ensure_task_completion_tracking():
    with engine.begin() as connection:
        columns = {column["name"] for column in inspect(connection).get_columns("tasks")}

        if "completed_at" not in columns:
            connection.execute(text("ALTER TABLE tasks ADD COLUMN completed_at DATETIME"))

        # Existing completed tasks use their last known update time as the best
        # available completion date. This keeps their history while allowing
        # the board to hide older items.
        connection.execute(
            text(
                "UPDATE tasks "
                "SET completed_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP) "
                "WHERE status = 'Completed' AND completed_at IS NULL"
            )
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()