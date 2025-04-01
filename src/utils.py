import logging, uuid


# LOGGING


# logging.basicConfig(level=logging.DEBUG, format="%(levelname)s LOG: %(message)s")
# logger = logging.getLogger(__name__)


# HELPER


def gen_uuid():
    return str(uuid.uuid4())
