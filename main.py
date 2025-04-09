from fastapi import FastAPI, Response

from config import name, rates, origins

from src.core import logging
from src.security import auth, limits, cors
from src.endpoints import ai, test


app = FastAPI()

app.include_router(ai.router)
app.include_router(test.router)


cors.setup(app, origins)
limits.setup(app, rates)
logging.setup(app, name)


@app.get("/", dependencies=[auth.via_api_key])
def health_check():
    return Response("Overlord is awake!")
