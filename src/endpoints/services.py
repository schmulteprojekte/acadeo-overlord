from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool


from src.core import sse

from src.utils.helper import gen_uuid

from src.schemas import AIRequest

from src.services.ai import call_openai


router = APIRouter()


@router.post("/call_openai")
@sse.endpoint
async def endpoint_call_openai(request: AIRequest):
    # avoid blocking via threadpool
    response = await run_in_threadpool(
        call_openai,
        request.messages,
        request.model,
    )
    return response


@router.post("/gen_uuid")
@sse.endpoint
async def endpoint_gen_uuid():
    response = await run_in_threadpool(gen_uuid)
    return response
