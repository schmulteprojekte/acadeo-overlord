import config as _

from fastapi import FastAPI, Response
from fastapi.concurrency import run_in_threadpool

from src.core import sse
from src.services import langfuse, litellm
from src.utils import gen_uuid


app = FastAPI()


# HELPER


@app.get("/")
def _():
    return Response("Overlord is awake!")


@app.post("/gen_uuid")
@sse.endpoint
async def _():
    return await run_in_threadpool(gen_uuid)


# MAIN


@app.post("/langfuse_litellm")
@sse.endpoint
async def _(request: langfuse.PromptConfig):
    func, args = langfuse.track(litellm.call), request
    return await run_in_threadpool(func, args)
