import asyncio, json
from functools import wraps

from sse_starlette.sse import EventSourceResponse


def sse_endpoint(check_job_func):
    """
    Decorator that turns any job-returning endpoint into an SSE endpoint.

    Args:
        check_job_func: Function that takes a job_id and returns job status/result
                        Should return None for not found, and have an is_finished
                        property and result property.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Run the original function to get job_id
            result = await func(*args, **kwargs)

            # If it's not a job submission endpoint that returns job_id, just return original result
            if not isinstance(result, dict) or "job_id" not in result:
                return result

            job_id = result["job_id"]

            # Create an event generator for SSE
            async def event_generator():
                while True:
                    # Check if job is complete using the provided function
                    job = check_job_func(job_id)

                    if job is None:
                        yield {"event": "error", "data": "job is None"}
                        break

                    if job.is_finished:
                        yield {"event": "result", "data": json.dumps(job.result)}
                        break

                    # Wait before checking again
                    await asyncio.sleep(0.5)

            return EventSourceResponse(event_generator())

        return wrapper

    return decorator
