from fastapi import APIRouter

from app.api.routes.agent import router as agent_router
from app.api.routes.auth import router as auth_router
from app.api.routes.auth import user_router
from app.api.routes.communities import router as communities_router
from app.api.routes.community import router as community_router
from app.api.routes.fan_tokens import router as fan_tokens_router
from app.api.routes.health import router as health_router
from app.api.routes.membership import router as membership_router
from app.api.routes.membership_payment import router as membership_payment_router
from app.api.routes.roles import router as roles_router
from app.api.routes.tasks import check_in_router, task_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["system"])
api_router.include_router(agent_router, tags=["agent"])
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(user_router, tags=["users"])
api_router.include_router(communities_router, tags=["communities"])
api_router.include_router(community_router, tags=["community"])
api_router.include_router(task_router, tags=["tasks"])
api_router.include_router(check_in_router, tags=["check-ins"])
api_router.include_router(fan_tokens_router, tags=["fan-tokens"])
api_router.include_router(roles_router, tags=["roles"])
api_router.include_router(membership_router, tags=["membership"])
api_router.include_router(membership_payment_router, tags=["membership"])
