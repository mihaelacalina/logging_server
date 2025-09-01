from os.path import dirname, abspath
from logger import configure_logger
from logger import *
from os import chdir


# Changes cwd to the app directory.

chdir(dirname(abspath(__file__)))


try:
    from config import config

    configure_logger(
        log_local = True,
        log_remote = False,
        log_local_file = config["local_log_file"],
        app_name="Log Server",
        debug = config["debug"]
    )
    
    info("Starting up")

    import src.main as _
except KeyboardInterrupt:
    info("Stopped by keyboard")
except BaseException as exception:
    realtime("Log Server crashed", exception)
finally:
    info("Shutting down")