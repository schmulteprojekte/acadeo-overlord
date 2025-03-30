from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from src.core import sse, langfuse, litellm
from src.utils.helper import gen_uuid


router = APIRouter()


@router.post("/langfuse_litellm")
@sse.endpoint
async def _(request: langfuse.Request):
    return await run_in_threadpool(
        langfuse.track(litellm.call),
        request.prompt_params,
        request.prompt_placeholders,
        request.metadata,
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
async def _():
    return await run_in_threadpool(gen_uuid)
