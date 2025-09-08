from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from src.security import auth
from src.core import sse

import uuid


router = APIRouter(prefix="/test")


@router.post("/gen_uuid")
@sse.endpoint
async def _():
    return await run_in_threadpool(lambda: str(uuid.uuid4()))
