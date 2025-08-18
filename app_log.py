from queue import Queue, Empty as QueueEmptyError
from threading import Event

#region Configuration

__all__ = ["info", "warn", "error", "wrap_exception", "configure"]
_level_to_string = ["INFO", "WARNING", "ERROR", "CRITICAL"]

_config = {
    "default_category": "",
    "write_stdout": True,
    "trace_min_level": 2,

    "log_remote": False,
    "remote_host": "127.0.0.1",
    "remote_port": 64000,

    "log_local": False,
    "log_file": "files/log.text"
}

_local_log_handle = None

_thread_running = False
_log_queue = Queue()

#endregion

#region Public functions

def info(message: str, category: str = None):
    _output(message, 0, category)

def warn(message: str, category: str = None):
    _output(message, 1, category)

def error(message: str, category: str = None):
    _output(message, 2, category)

def critical(message: str, category: str = None, sound: bool = True):
    _output(message, 3, category)

    if sound:
        try:
            with open("/dev/speaker", "w") as speaker:
                speaker.write("L64 B")
        except Exception:
            pass

def wrap_exception(message: str, exception: Exception, category: str = None):
    _output(f"Unhandled {exception.__class__.__name__}: {message}", 2, category, exception)

#endregion

def _write(message: str):
    global _local_log_handle

    if _config["write_stdout"]:
        print(message)
    
    if _config["log_local"]:
        if _local_log_handle is not None:
            _local_log_handle.write(message + "\n")

def _thread(event: Event):
    from socket import socket as Socket, AF_INET, SOCK_DGRAM
    from json import dumps as json_encode
    from threading import main_thread
    
    with Socket(AF_INET, SOCK_DGRAM) as socket:

        event.set()
        
        while True:
            if _log_queue.empty():
                if not _thread_running:
                    break

                if not _config["log_remote"]:
                    break

                if not main_thread().is_alive():
                    break

            try:
                log_entry = _log_queue.get(timeout=1.0)

                socket.sendto(json_encode(log_entry, separators=(",", ":")).encode(), (_config["remote_host"], _config["remote_port"]))
            except QueueEmptyError:
                pass
            except Exception as exception:
                wrap_exception("Unable to send log", exception)

def _output(message: str, level: int = 0, category:str = None, exception: Exception = None):
    from datetime import datetime


    formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    trace = ""

    if category is None:
        category = _config["default_category"]

    if _config["write_stdout"]:
        _write(f"[{formatted_time}] [{_level_to_string[level]}] [{category}]: {message}")

    if level >= _config["trace_min_level"]:
        from os.path import basename
        import traceback

        frames = None

        if exception:
            frames = traceback.extract_tb(exception.__traceback__)
        else:
            frames = traceback.extract_stack()[:-2]
        
        if _config["write_stdout"]:
            _write("[TRACE]:")

        for frame in frames:
            line = frame.lineno
            name = basename(frame.filename)
            text = frame.line.strip() if frame.line else "N/A"

            trace += f"    {name}:{line}\n"

            if _config["write_stdout"]:
                _write(f"    {name}:{line} [`{text}`]\n")
        
        

    _log_queue.put(
        [
            level,
            category,
            message,
            trace
        ]
    )


def configure(write_stdout: bool = True, trace_min_level: int = 2, default_category: str = "", log_remote: bool = False, remote_host: str = "127.0.0.1", remote_port: int = 64000, log_local: bool = False, log_file: str = "log.log"):
    from threading import Thread, Event

    global _thread_running, _config, _local_log_handle


    if _thread_running:
        raise RuntimeError("Logger has already been configured.")
    
    _config["write_stdout"] = write_stdout
    _config["trace_min_level"] = trace_min_level
    _config["default_category"] = default_category

    _config["log_remote"] = log_remote
    _config["remote_host"] = remote_host
    _config["remote_port"] = remote_port

    _config["log_local"] = log_local
    _config["log_file"] = log_file


    if log_remote:
        _load_event = Event()
        _thread_running = True
        
        Thread(target=_thread, args=(_load_event,)).start()

        _load_event.wait()
    
    if log_local:
        try:
            _local_log_handle = open(log_file, "w")
        except Exception:
            raise RuntimeError("Unable to create local log file.")
    