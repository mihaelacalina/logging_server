import source.log_server as log_server
import source.logger as logger

from app_config import *
from time import sleep
from app_log import *

try:
    info("Startup finished.")

    while True:
        sleep(1)
except KeyboardInterrupt:
    pass
finally:
    log_server.stop()
    logger.stop()