from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from src.core import sse
from src.schemas import AIRequest
from src.services.ai import call_ai


router = APIRouter()


@router.post("/ai")
@sse.endpoint
async def ai_request(request: AIRequest):
    # avoid blocking via threadpool
    response = await run_in_threadpool(
        call_ai,
        request.messages,
        request.model,
    )
    return response
