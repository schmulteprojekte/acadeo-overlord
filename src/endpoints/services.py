from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool


from src.core import sse

from src.utils.helper import gen_uuid

from src.endpoints.schemas import AIRequest

from src.services.ai import call_litellm


router = APIRouter()


@router.post("/call_ai")
@sse.endpoint
async def endpoint_call_openai(request: AIRequest):
    # avoid blocking via threadpool
    response = await run_in_threadpool(
        call_litellm,
        request.messages,
        request.model,
    )
    return response


@router.post("/gen_uuid")
@sse.endpoint
async def endpoint_gen_uuid():
    response = await run_in_threadpool(gen_uuid)
    return response
