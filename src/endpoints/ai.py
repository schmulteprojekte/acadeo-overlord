from fastapi import APIRouter

from src.core.queue import queue
from src.schemas import AIRequest


router = APIRouter()


@router.post("/ai")
async def queue_ai_request(request: AIRequest):
    job = queue.enqueue(
        "src.workers.ai.call_ai",
        request.messages,
        request.model,
    )
    return {"job_id": job.id}
