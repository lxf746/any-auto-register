"""v2 Actions endpoints — platform action listing and execution."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from api.v2.response import ApiResponse
from application.actions import ActionsService
from domain.actions import ActionExecutionCommand

router = APIRouter(prefix="/actions", tags=["actions"])

_service = ActionsService()


class ActionExecuteRequest(BaseModel):
    account_id: int
    action_id: str
    params: dict = {}


@router.get("/{platform}")
def list_actions(platform: str):
    """List available actions for a platform."""
    result = _service.list_actions(platform)
    return ApiResponse(ok=True, data=result)


@router.get("/{platform}/capabilities")
def list_capabilities(platform: str):
    """List capabilities for a platform."""
    result = _service.list_capabilities(platform)
    return ApiResponse(ok=True, data=result)


@router.post("/{platform}/execute")
def execute_action(platform: str, body: ActionExecuteRequest):
    """Execute an action (sync or async task)."""
    command = ActionExecutionCommand(
        platform=platform,
        account_id=body.account_id,
        action_id=body.action_id,
        params=body.params,
    )
    result = _service.execute_action(command)
    return ApiResponse(ok=True, data=result)
