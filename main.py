from config import rates, origins

from fastapi import FastAPI, Response

from src.security import auth, limits, cors
from src.endpoints import ai, test


app = FastAPI()

app.include_router(ai.router)
app.include_router(test.router)

limits.setup(app, rates)
cors.setup(app, origins)


@app.get("/", dependencies=[auth.via_api_key])
def health_check():
    return Response("Overlord is awake!")
