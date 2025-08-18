from app_config import app_config
from app_log import *


try:
    configure(True, app_config.get_int("app_log.trace_min_level"), "APP", False, log_local=True, log_file=app_config.get_string("app_log.log_file"))

    info("Log Server is starting up.")

    import source.main as _
except Exception as exception:
    wrap_exception(str(exception), exception)
finally:
    info("Log Server is shutting down.")