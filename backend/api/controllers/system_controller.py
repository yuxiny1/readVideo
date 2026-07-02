from fastapi import APIRouter, Response

from backend.application import get_mediator
from backend.application.messages.system import AppConfigQuery, HealthQuery, ReadinessQuery


router = APIRouter()


@router.get("/health")
async def health():
    return await get_mediator().send(HealthQuery())


@router.get("/health/ready")
async def readiness(response: Response):
    result = await get_mediator().send(ReadinessQuery())
    if result["status"] == "unavailable":
        response.status_code = 503
    return result


@router.get("/app_config")
async def app_config():
    return await get_mediator().send(AppConfigQuery())
