from fastapi import APIRouter

from src.core.queue import queue
from src.schemas import AIRequest
from src.utils.decorators import sse_endpoint


router = APIRouter()


@router.post("/ai")
@sse_endpoint(queue.fetch_job)
async def ai_request(request: AIRequest):
    """Main AI endpoint - returns response as SSE stream"""
    job = queue.enqueue(
        "src.workers.ai.call_ai",
        request.messages,
        request.model,
    )
    return {"job_id": job.id}


@router.post("/mock_ai")
@sse_endpoint(queue.fetch_job)
async def mock_ai_request(request: AIRequest):
    """Main AI endpoint - returns response as SSE stream"""
    job = queue.enqueue(
        "src.workers.ai.mock_ai",
        request.messages,
        request.model,
    )
    return {"job_id": job.id}
