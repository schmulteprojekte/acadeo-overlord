from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from src.core import sse

from src.utils.helper import gen_uuid

from src.endpoints.schemas import LangfuseRequest, GeminiRequest

from src.services.ai import call_litellm


router = APIRouter()


@router.post("/call_openai")
@sse.endpoint
async def _call_openai(request: LangfuseRequest):
    response = await run_in_threadpool(
        call_litellm,
        prompt=request.prompt,
        placeholders=request.placeholders,
        metadata=request.metadata,
    )
    return response


# @router.post("/call_gemini")
# @sse.endpoint
# async def _call_gemini(request: GeminiRequest):
#     response = await run_in_threadpool(
#         call_litellm,
#         messages=request.messages,
#         model=f"gemini/{request.model}",
#         temperature=request.temperature,
#         max_tokens=request.max_tokens,
#         response_format=None,  # TODO
#         safety_settings=request.safety_settings,
#     )
#     return response


@router.post("/gen_uuid")
@sse.endpoint
async def _gen_uuid():
    response = await run_in_threadpool(gen_uuid)
    return response
