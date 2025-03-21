from fastapi import FastAPI

from src.core.queue import queue
from src.endpoints import ai


app = FastAPI()

app.include_router(ai.router)


@app.get("/result/{job_id}")
async def get_result(job_id: str):

    job = queue.fetch_job(job_id)

    if not job:
        return {"status": "not_found"}

    if job.is_finished:
        return {"status": "completed", "result": job.result}

    return {"status": "pending"}
