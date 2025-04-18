from fastapi import APIRouter

from src.security import auth
from src.core import sse

from src.chat import ChatRequest, call


router = APIRouter(prefix="/ai")


@router.post("/chat", dependencies=[auth.via_api_key])
@sse.endpoint
async def chat(request: ChatRequest):
    return await call(request)
