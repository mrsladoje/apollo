"""What-If route — POST /api/whatif (PLAN-C §5.1, §12)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from apollo.mocks.tool_mocks import run_counterfactual

router = APIRouter(prefix="/api")


class WhatIfRequest(BaseModel):
    run_id: str
    branch_t: float
    alt_action: str


@router.post("/whatif")
async def whatif(req: WhatIfRequest) -> dict:
    result = run_counterfactual(req.run_id, req.branch_t, req.alt_action)
    return result
