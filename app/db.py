import os

from sqlmodel import Session, SQLModel, create_engine

SQLITE_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./construction.db")
engine = create_engine(SQLITE_DATABASE_URL, connect_args={"check_same_thread": False})


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
