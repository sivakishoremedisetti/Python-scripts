import os
from functools import wraps
import app_logger
import traceback


LOGGER = app_logger.get_logger(__name__)


def safe_run(function):

    @wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)

        except Exception as err:
            os.environ["CACHE_MANAGER_PROCESS_EXPECTED_ERROR"] = "1"
            LOGGER.critical("Traceback:\n{}".format(traceback.format_exc()))
            raise Exception(str(err))

    return wrapper
