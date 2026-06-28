import os
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import create_db_and_tables
from app.routers.auth import router as auth_router
from app.routers.finance import router as finance_router
from app.routers.projects import router as projects_router
from app.routers.reports import router as reports_router
from app.routers.site import router as site_router
from app.routers.workitems import router as workitems_router

app = FastAPI(
    title="Construction Project Management API",
    description="API for managing construction projects with auth, tasks, finance and photo upload",
    version="0.2.0",
)

# CORS cho frontend (Vite dev server mặc định chạy ở :5173).
# Cấu hình qua biến CORS_ORIGINS (danh sách phân tách bằng dấu phẩy).
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(workitems_router)
app.include_router(finance_router)
app.include_router(site_router)
app.include_router(reports_router)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
