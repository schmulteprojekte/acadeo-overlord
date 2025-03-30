import config as _

from fastapi import FastAPI, Response
from fastapi.concurrency import run_in_threadpool

from src.core import sse, langfuse, litellm
from src.utils.helper import gen_uuid


app = FastAPI()


@app.get("/")
def _():
    return Response("Overlord is awake!")


@app.post("/gen_uuid")
@sse.endpoint
async def _():
    return await run_in_threadpool(gen_uuid)


@app.post("/langfuse_litellm")
@sse.endpoint
async def _(request: langfuse.Request):
    return await run_in_threadpool(
        langfuse.track(litellm.call),
        request.prompt_params,
        request.prompt_placeholders,
        request.metadata,
    )
