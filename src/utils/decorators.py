import time

from src.utils.loggers import logger
from src.utils.exceptions import NotCompleted


def poll_until_completed(attempts: int = 6, delay: int = 1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < attempts:
                try:
                    return func(*args, **kwargs)
                except NotCompleted:
                    retries += 1
                    wait = delay * (2**retries - 1)
                    logger.debug(f"Waiting for {wait}s before polling again with attempt {retries}")
                    time.sleep(wait)

        return wrapper

    return decorator
