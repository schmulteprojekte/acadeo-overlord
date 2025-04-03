from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from src.core import sse
from src.services import langfuse, litellm


langfuse_router = APIRouter(prefix="/langfuse")


@langfuse_router.post("/litellm")
@sse.endpoint
async def langfuse_litellm(request: langfuse.PromptConfig):
    func, args = langfuse.track(litellm.call), request
    return await run_in_threadpool(func, args)
