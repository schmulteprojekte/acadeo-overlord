from config import rates

from fastapi import FastAPI, Response

from src.security import auth, limits
from src.endpoints import ai, test


app = FastAPI()

app.include_router(ai.langfuse_router)
app.include_router(test.router)

limits.setup(app, rates)


@app.get("/", dependencies=[auth.via_api_key])
def health_check():
    return Response("Overlord is awake!")
