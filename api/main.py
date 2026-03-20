"""
CamPost API 서버
실행: uvicorn api.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import init_pool, close_pool
from api.routes import notices, files


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(
    title="CamPost API",
    description="단국대 SW학과 공지사항 재구성 플랫폼",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 프로덕션 배포 시 프론트 도메인으로 제한
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(notices.router)
app.include_router(files.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
