import src.dedicated_logger as dedicated_logger
from threading import Event
from config import *
from logger import *


#region private

_start_event = Event()

def _thread():
    from socket import AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_BROADCAST, socket as Socket, timeout as SocketTimeoutError, error as SocketError
    from json import loads as json_decode

    try:
        socket_server = Socket(AF_INET, SOCK_DGRAM, 0)

        socket_server.bind((config["host"], config["port"]))
        socket_server.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        socket_server.settimeout(1.0)


        _start_event.set()

        while True:
            try:
                data, remote_address = socket_server.recvfrom(2048)

                log_data = json_decode(data)

                if len(log_data) < 4:
                    warn(f"Invalid log format received: \"{data.decode()}\".")
                    continue

                log_data["source"] = remote_address[0]
                
                dedicated_logger.add_entry(log_data)
            except SocketTimeoutError:
                pass
            except SocketError as exception:
                error("Socket exception occured", exception)
    finally:
        _start_event.set()

#endregion


def start():
    """Starts the logger server."""
    from threading import Thread


    Thread(target=_thread, name="Log Server", daemon=True).start()
    _start_event.wait()