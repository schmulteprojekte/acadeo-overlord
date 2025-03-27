from fastapi import FastAPI, Response
from src.endpoints import services


app = FastAPI()
app.include_router(services.router)


@app.get("/")
def root():
    return Response("Overlord is awake!")
