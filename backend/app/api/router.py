from fastapi import APIRouter

from app.api.routes.agent import router as agent_router
from app.api.routes.auth import router as auth_router
from app.api.routes.auth import user_router
from app.api.routes.communities import router as communities_router
from app.api.routes.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["system"])
api_router.include_router(agent_router, tags=["agent"])
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(user_router, tags=["users"])
api_router.include_router(communities_router, tags=["communities"])
