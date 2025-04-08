from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from src.security import auth
from src.core import sse
from src.services import langfuse, litellm


router = APIRouter(prefix="/langfuse")


@router.post("/litellm", dependencies=[auth.via_api_key])
@sse.endpoint
async def langfuse_litellm(request: langfuse.PromptConfig):
    func, args = langfuse.track(litellm.call), request
    return await func(args)
