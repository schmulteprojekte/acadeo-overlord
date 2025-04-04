import config as _  # init

from fastapi import FastAPI, Response

from src.auth import api_key
from src.endpoints import ai, test


app = FastAPI()

app.include_router(ai.langfuse_router)
app.include_router(test.router)


@app.get("/", dependencies=[api_key.authentication])
def health_check():
    return Response("Overlord is awake!")
