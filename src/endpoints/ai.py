from fastapi import APIRouter, Security
from fastapi.concurrency import run_in_threadpool

from src.auth import api_key
from src.core import sse
from src.services import langfuse, litellm


langfuse_router = APIRouter(prefix="/langfuse")


@langfuse_router.post("/litellm", dependencies=[Security(api_key.validate)])
@sse.endpoint
async def langfuse_litellm(request: langfuse.PromptConfig):
    func, args = langfuse.track(litellm.call), request
    return await run_in_threadpool(func, args)
