from fastapi import FastAPI

from src.endpoints import services


app = FastAPI()

app.include_router(services.router)
