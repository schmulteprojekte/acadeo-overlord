from fastapi import FastAPI, Response

from config import name, rates, origins

from src.core import logging
from src.security import auth, limits, cors
from src.endpoints import ai, test


app = FastAPI(dependencies=[auth.via_api_key])


# setup security middlewares
cors.setup(app, origins)
limits.setup(app, rates)
logging.setup(app, name)


# include module routers
app.include_router(ai.router)
app.include_router(test.router)


@app.get("/")
def health_check():
    return Response(f"{name} is awake")
