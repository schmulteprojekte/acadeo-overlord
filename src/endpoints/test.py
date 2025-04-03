from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from src.core import sse
from src.utils import gen_uuid


router = APIRouter(prefix="/test")


@router.post("/gen_uuid")
@sse.endpoint
async def _():
    return await run_in_threadpool(gen_uuid)
