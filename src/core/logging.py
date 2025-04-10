from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from contextvars import ContextVar
import logging, json, time, uuid


# HELPER

logger = None

request_id_context = ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = dict(
            level=record.levelname,
            datetime=self.formatTime(record, self.datefmt),
            message=record.getMessage(),
            # from context:
            id=request_id_context.get(),
            # extra info:
            endpoint=getattr(record, "endpoint", None),
            method=getattr(record, "method", None),
            status=getattr(record, "status", None),
            ms=getattr(record, "ms", None),
        )

        log_data_clean = {k: v for k, v in log_data.items() if v}
        return json.dumps(log_data_clean)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = str(uuid.uuid4())
        request_id_context.set(req_id)
        start_time = time.time()

        # REQUEST
        request_info = dict(
            method=request.method,
            endpoint=request.url.path,
        )
        logger.info(f"Request", extra=request_info)

        try:
            # CALL
            response = await call_next(request)
            process_time = round((time.time() - start_time) * 1000)

            # change level depending on status
            if response.status_code >= 500:
                log_method = logger.error
            elif response.status_code >= 400:
                log_method = logger.warning
            else:
                log_method = logger.info

            # RESPONSE
            response_info = dict(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code,
                ms=process_time,
            )
            log_method(f"Response", extra=response_info)
            return response

        except Exception as e:
            process_time = round((time.time() - start_time) * 1000)

            # ERROR
            error_info = dict(
                method=request.method,
                endpoint=request.url.path,
                ms=process_time,
            )
            logger.error(f"Error: {str(e)}", exc_info=True, extra=error_info)
            raise


# INIT


def setup(app: FastAPI, name: str):
    global logger

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

    app.add_middleware(LoggingMiddleware)


def get_logger():
    return logger
