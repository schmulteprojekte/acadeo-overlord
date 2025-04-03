import config as _

from fastapi import FastAPI, Response
from src.endpoints import ai, test


app = FastAPI()

app.include_router(ai.langfuse_router)
app.include_router(test.router)


@app.get("/")
def health_check():
    return Response("Overlord is awake!")
