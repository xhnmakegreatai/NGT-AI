"""
NGT-AI FastAPI 后端主应用
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

try:  # pragma: no cover - optional dependency
    import redis.asyncio as redis_async
except ImportError:  # pragma: no cover
    redis_async = None

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.app.api import auth, decision, health, websocket, workspace  # noqa: E402
from backend.app.config import settings  # noqa: E402
from backend.app.db import SessionLocal  # noqa: E402
from backend.app.services.decision_service import (  # noqa: E402
    DecisionService,
    create_decision_service,
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_decision_service(app: FastAPI) -> DecisionService:
    service: Optional[DecisionService] = getattr(app.state, "decision_service", None)
    if not service:
        raise RuntimeError("Decision service is not initialized")
    return service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 NGT-AI API 启动中...")

    # 确保数据表存在(SQLite 本地开发开箱即用;生产建议用 Alembic 迁移)
    from backend.app.db import Base, engine
    from backend.app.models import decision as _decision  # noqa: F401
    from backend.app.models import user as _user  # noqa: F401

    Base.metadata.create_all(bind=engine)

    redis_client = None
    if settings.redis_url and redis_async:
        try:
            redis_client = redis_async.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info("🔌 Redis 连接成功")
        except Exception as exc:  # pragma: no cover - optional component
            logger.warning("❗ 无法连接 Redis: %s", exc)
    else:
        if settings.redis_url:
            logger.warning("Redis 客户端未安装，跳过连接")

    decision_service = create_decision_service(
        use_real_apis=settings.use_real_apis,
        session_factory=SessionLocal,
        redis_client=redis_client,
    )
    app.state.decision_service = decision_service
    app.state.redis = redis_client
    logger.info("✅ 决策服务初始化完成 (real_apis=%s)", settings.use_real_apis)

    try:
        yield
    finally:
        logger.info("🧹 正在关闭决策服务")
        await decision_service.shutdown()
        if redis_client:
            await redis_client.close()
        logger.info("👋 NGT-AI API 已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="NGT-AI Decision API",
    description="基于名义小组技术的多AI协作决策系统API",
    version="2.1.0",
    lifespan=lifespan,
)


# CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册路由
app.include_router(health.router, prefix="/api", tags=["健康检查"])
app.include_router(decision.router, prefix="/api", tags=["决策分析"])
app.include_router(websocket.router, prefix="/api", tags=["实时通信"])
app.include_router(auth.router, prefix="/api")
app.include_router(workspace.router, prefix="/api", tags=["工作区"])


@app.middleware("http")
async def inject_service(request: Request, call_next):
    """
    中间件：将决策服务注入到 request.state，便于路由访问
    """
    request.state.decision_service = _get_decision_service(request.app)
    response = await call_next(request)
    return response


@app.get("/")
async def root():
    """根路由"""
    return {
        "message": "NGT-AI Decision System API",
        "version": "2.1.0",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error("全局异常: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "type": type(exc).__name__,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )
