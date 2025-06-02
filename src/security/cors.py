from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI


def setup(app: FastAPI, allowed_origins: list[str]):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["x-api-key", "x-client-type", "content-type"],
    )
