from fastapi import FastAPI

from src.endpoints import ai


app = FastAPI()

app.include_router(ai.router)
