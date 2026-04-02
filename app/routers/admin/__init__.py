"""
管理端路由包

将原来平铺在 routers/ 下的 admin_*.py 收拢到 admin/ 子包。
main.py 通过此 __init__.py 统一导入。
"""
from app.routers.admin.auth import router as auth_router
from app.routers.admin.agents import router as agents_router
from app.routers.admin.config import router as config_router
from app.routers.admin.dashboard import router as dashboard_router
from app.routers.admin.logs import router as logs_router
from app.routers.admin.reviews import router as reviews_router
from app.routers.admin.scores import router as scores_router
from app.routers.admin.tasks import router as tasks_router
from app.routers.admin.prompts import router as prompts_router
from app.routers.admin.managed_agents import router as managed_agents_router

__all__ = [
    "auth_router",
    "agents_router",
    "config_router",
    "dashboard_router",
    "logs_router",
    "reviews_router",
    "scores_router",
    "tasks_router",
    "prompts_router",
    "managed_agents_router",
]
