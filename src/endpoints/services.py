from src.core import sse, langfuse, litellm

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from src.utils.helper import gen_uuid


router = APIRouter()


@router.post("/langfuse_litellm")
@sse.endpoint
async def _call_litellm(request: langfuse.Request):
    return await run_in_threadpool(
        litellm.call,
        prompt_params=request.prompt_params,
        prompt_placeholders=request.prompt_placeholders,
        metadata=request.metadata,
    )


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
