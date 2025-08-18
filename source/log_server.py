import source.logger as logger

from app_config import *
from app_log import *


_running_log_server_thread = False

def _thread():
    from socket import AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_BROADCAST, socket as Socket, timeout as SocketTimeoutError, error as SocketError
    from json import loads as json_decode

    socket_server = Socket(AF_INET, SOCK_DGRAM, 0)

    socket_server.bind((app_config.get_string("log_server.host"), app_config.get_int("log_server.port")))
    socket_server.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    socket_server.settimeout(1.0)


    while True:
        if not _running_log_server_thread:
            break

        try:
            data, remote_address = socket_server.recvfrom(2048)

            log_data = json_decode(data)

            if len(log_data) < 4:
                warn(f"Invalid log format received: \"{data.decode()}\".")
                continue
            
            logger.log(remote_address[0], log_data[0], log_data[1], log_data[2], log_data[3])
        except SocketTimeoutError:
            pass
        except SocketError as exception:
            wrap_exception("Socket exception occured", exception)


def stop():
    global _running_log_server_thread

    info("Log Server thread is shutting down.")

    _running_log_server_thread = False

if __name__ != "__main__":
    from threading import Thread

    info("Log Server is starting up.")


    _running_log_server_thread = True
    Thread(target=_thread, daemon=True).start()