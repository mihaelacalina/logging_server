from time import sleep
from logger import *

import src.dedicated_logger as dedicated_logger
import src.log_server as log_server


dedicated_logger.start()
log_server.start()

info("Started")


while True:
    sleep(1.0)