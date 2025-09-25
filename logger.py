from typing import TypedDict
from threading import Event
from queue import Queue


__all__ = ["log_context", "debug", "info", "warn", "error", "realtime"]

#region private

_level_to_string = ["DEBUG", "INFO", "WARNING", "ERROR", "REALTIME"]
_context_names = {}
_app_name = "APP"

_log_stdout = True
_debug = False

_log_local = True
_log_local_file = "log.log"
_log_local_encoding = "utf-8"

_log_remote = False
_log_remote_host = "127.0.0.1"
_log_remote_port = "64000"

_trace_min_level = 3

_log_configured = False
_log_queue: Queue["LogEntry"] = Queue()
_log_thread_event = Event()


def _logger_thread():
    try:
        from queue import Empty as QueueEmptyError
        from socket import socket as Socket
        from threading import main_thread
        from _io import TextIOWrapper

        global _log_local, _log_remote


        local_handle: TextIOWrapper|None = None
        remote_handle: Socket|None = None


        if _log_local:
            try:
                local_handle = open(_log_local_file, "a", encoding=_log_local_encoding)
            except OSError:
                error("Unable to open local log file for writing. Disabling local log.")

                local_handle = None
                _log_local = False
        
        if _log_remote:
            from socket import AF_INET, SOCK_DGRAM

            
            try:
                remote_handle = Socket(AF_INET, SOCK_DGRAM)
            except OSError:
                error("Unable to create a socket for remote logging. Disabling remote log.")

                remote_handle = None
                _log_remote = False
        
        _log_thread_event.set()

        while True:
            try:
                _entry = _log_queue.get(timeout = 1)
                entry = _entry["entry"]

                text_log = None

                if _log_stdout or _log_local:
                    text_log = _get_log_text(entry)
                
                if _log_stdout:
                    try:
                        print(text_log)
                    except Exception:
                        print(text_log.encode("unicode-escape").decode("ascii"))

                if _log_local and local_handle is not None:
                    try:
                        local_handle.write(text_log + "\n")
                        local_handle.flush()
                    except Exception:
                        print("Unable to write to local log. Disabling local logging.")

                        try:
                            local_handle.close()
                        except Exception:
                            pass

                        local_handle = None
                        _log_local = False
                
                if _log_remote and remote_handle is not None and _entry["send_remote"]:
                    from json import dumps


                    packet = {
                        "time": entry["time"],
                        "level": entry["level"],
                        "message": entry["message"],
                        "context": entry["context"],
                        "app_name": _app_name,
                        "exception_message": str(entry["exception"]),
                        "trace": entry["trace"]
                    }

                    try:
                        str_packet = dumps(packet, separators=(",", ":"))

                        remote_handle.sendto(str_packet.encode(), (_log_remote_host, _log_remote_port))
                    except IOError as exception:
                        error("Unable to send remote log", exception, send_remote=False)
                
                
            except QueueEmptyError:
                pass
            finally:
                # Exit if the main thread is dead and the log queue is empty, otherwise continue saving logs before exiting.

                if not main_thread().is_alive() and _log_queue.qsize() == 0:
                    break
    finally:
        _log_thread_event.set()

def _get_log_text(log_entry: "LogEntry"):
    from os.path import basename


    level = log_entry["level"]
    string_level = _level_to_string[level]
    message = log_entry["message"]
    exception = log_entry["exception"]
    string_exception = str(exception)
    trace = log_entry["trace"]
    context = log_entry["context"]
    time = log_entry["time"]

    text = None

    if exception is None:
        text = f"[{time}] [{context}] [{string_level}]: {message}"
    else:
        text = f"[{time}] [{context}] [{string_level}]: {message}: [{exception.__class__.__name__}]: {string_exception}"

    if level >= _trace_min_level:
        text += "\n[TRACE]:"

        for entry in trace:
            file_name = basename(entry["file"])
            line = entry["line"]
            trace_text = entry["text"]

            text += f"\n    [{file_name}:{line}] {trace_text}"

    return text

#region types

class TraceFrame(TypedDict):
    file: str
    line: int
    text: str

class LogEntry(TypedDict):
    level: int
    message: str
    exception: BaseException|None
    trace: list[TraceFrame]
    context: str
    time: str

class RemoteLogEntry(TypedDict):
    time: str
    level: int
    source: str
    message: str
    context: str
    app_name: str
    exception_message: str
    trace: list[TraceFrame]

#endregion

#region utilities

def _get_calling_file() -> str|None:
    """
        Gets the file path of the first stack frame call from another file.
        
        Used to get the file path of the module logging with this module.

        
        :return The module file path or None:
    """
    from inspect import currentframe, getmodule
    from os.path import abspath


    try:
        stack_frame = currentframe()
        lib_path = abspath(__file__)
        src_path = None

        while stack_frame:
            module = getmodule(stack_frame)

            if module is None:
                return None
            
            src_path = getattr(module, "__file__", None)

            if src_path is None:
                return None
            
            src_path = abspath(src_path)
            
            if src_path != lib_path:
                return src_path
            
            stack_frame = stack_frame.f_back
        
        return None
    except Exception:
        return None

def _get_context_for_file(file_path: str) -> str:
    context = "UNKNOWN"
    
    if file_path is not None:
        if file_path in _context_names.keys():
            context = _context_names[file_path]
        else:
            from os.path import basename

            file_name = basename(file_path)

            if len(file_name) < 4:
                context = file_name
            else:
                context = basename(file_path)[0:-3]
    
    return context.upper()

def _get_trace(exception: BaseException|None = None):
    from traceback import extract_tb, extract_stack


    trace: list[TraceFrame] = []
    frames = None

    if exception:
        frames = extract_tb(exception.__traceback__)
    else:
        frames = extract_stack()[:-2]

    for frame in frames:
        line = frame.lineno
        file = frame.filename
        text = frame.line.strip() if frame.line else "N/A"

        trace_frame = {
            "file": file,
            "line": line,
            "text": text
        }

        trace.append(trace_frame)

    return trace

def _is_valid_ipv4(address: str):
    from ipaddress import IPv4Address, AddressValueError

    try:
        IPv4Address(address)

        return True
    except AddressValueError:
        return False

def _is_valid_domain(address: str):
    """Checks if the given domain name can be resolved."""
    from socket import gethostbyname, gaierror


    try:
        gethostbyname(address)

        return True
    except gaierror:
        return False

#endregion

#endregion

#region public

def log_context(name: str):
    """
        Sets the context name for all log calls from this file to the provided one.

        :param name: The name of the context assigned to the module calling this function.
        It will be turned to uppercase.
    """
    calling_file = _get_calling_file()

    if calling_file is None:
        return
    
    _context_names[calling_file] = name.upper()

def configure_logger(
        log_stdout: bool = True,
        log_local = False,
        log_local_file: str = "local.log",
        log_local_encoding: str = "utf-8",
        log_remote: bool = False,
        log_remote_host: str = "127.0.0.1",
        log_remote_port: int = 64000,
        app_name: str = "DEFAULT",
        trace_min_level: int = 3,
        debug: bool = False
    ):
    """
        Sets up the logger and start the logging thread.

        :param log_stdout: Set to True in order to write logs to the console.
        :param log_local: Set to True to write logs to a local file.
        :param log_local_file: The name and path of the local log file. Only used if log_local is True.
        :param log_local_encoding: The character encoding to use for the local log file.
        :param log_remote: Set to True to send logs to a remote network log server.
        :param log_remote_host: The IP address or hostname of the remote log server. Only used if log_remote is True.
        :param log_remote_port: The network port of the remote log server. Only used if log_remote is True.
        :param app_name: The app name that will be sent to the log server. Only used if log_remote is True.
        :param trace_min_level: The minimum log level on which the trace will be displayed in the console and local log. The trace will be saved for all remote logs.
        :param debug: If set to true, debug logs will be enabled.

        :raises PermissionError: If the log_local_file is not writable.
        :raises ValueError: If the log_remote_host or the log_remote_port is invalid.
        :raises RuntimeError: If this function is called again after configuring the logger.
    """
    from threading import Thread
    
    global _log_configured, _debug
    global _log_stdout, _trace_min_level, _app_name
    global _log_local, _log_local_file, _log_local_encoding
    global _log_remote, _log_remote_host, _log_remote_port


    if _log_configured:
        raise RuntimeError("Logger has already been configured.")
    
    _debug = debug

    _log_configured = True
    _app_name = app_name
    _log_stdout = log_stdout
    _trace_min_level = trace_min_level
    
    _log_local = log_local
    _log_local_file = log_local_file
    _log_local_encoding = log_local_encoding

    _log_remote = log_remote
    _log_remote_host = log_remote_host
    _log_remote_port = log_remote_port

    if log_local:
        try:
            with open(_log_local_file, "a"):
                pass
        except OSError:
            raise PermissionError("Access denied to local log file.")
    
    
    if _log_remote_port > 65535:
        raise ValueError("Remote log port is not in the range [0 - 65535].")
    
    if not _is_valid_ipv4(log_remote_host) and not _is_valid_domain(log_remote_host):
        raise ValueError("Remote log host is not a valid ipv4 address or the domain cannot be resolved.")


    Thread(target=_logger_thread, name="Logger Thread", daemon=False).start()

    _log_thread_event.wait()

#region logging

def debug(message: str, exception: Exception|None = None, send_remote=True):
    """
        Adds a log entry with the provided message and exception message, if present.

        The stack trace will be logged as well and in case an exception is provided,
        the exception trace will be saved instead.

        This function will not block for IO operations.

        The debug log call will be ignored if the logger has not been configured with debug set to True.


        :param message: The message to write to the log.
        :param exception: The exception to log or None if no exception is to be logged.
        :param send_remote: If set to false, the log will not be sent to the remote logging server.
    """
    from datetime import datetime

    if not _debug:
        return

    time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    context = _get_context_for_file(_get_calling_file())

    log_entry = {
        "entry": {
            "level": 0,
            "message": message,
            "context": context,
            "exception": exception,
            "trace": _get_trace(exception),
            "time": time
        },
        "send_remote": send_remote
    }

    _log_queue.put(log_entry)

def info(message: str, exception: Exception|None = None, send_remote=True):
    """
        Adds a log entry with the provided message and exception message, if present.

        The stack trace will be logged as well and in case an exception is provided,
        the exception trace will be saved instead.

        This function will not block for IO operations.
        

        :param message: The message to write to the log.
        :param exception: The exception to log or None if no exception is to be logged.
        :param send_remote: If set to false, the log will not be sent to the remote logging server.
    """
    from datetime import datetime


    time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    context = _get_context_for_file(_get_calling_file())

    log_entry = {
        "entry": {
            "level": 1,
            "message": message,
            "context": context,
            "exception": exception,
            "trace": _get_trace(exception),
            "time": time
        },
        "send_remote": send_remote
    }

    _log_queue.put(log_entry)

def warn(message: str, exception: Exception|None = None, send_remote=True):
    """
        Adds a log entry with the provided message and exception message, if present.

        The stack trace will be logged as well and in case an exception is provided,
        the exception trace will be saved instead.

        This function will not block for IO operations.
        

        :param message: The message to write to the log.
        :param exception: The exception to log or None if no exception is to be logged.
        :param send_remote: If set to false, the log will not be sent to the remote logging server.
    """
    from datetime import datetime


    time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    context = _get_context_for_file(_get_calling_file())

    log_entry = {
        "entry": {
            "level": 2,
            "message": message,
            "context": context,
            "exception": exception,
            "trace": _get_trace(exception),
            "time": time
        },
        "send_remote": send_remote
    }

    _log_queue.put(log_entry)

def error(message: str, exception: Exception|None = None, send_remote=True):
    """
        Adds a log entry with the provided message and exception message, if present.

        The stack trace will be logged as well and in case an exception is provided,
        the exception trace will be saved instead.

        This function will not block for IO operations.
        

        :param message: The message to write to the log.
        :param exception: The exception to log or None if no exception is to be logged.
        :param send_remote: If set to false, the log will not be sent to the remote logging server.
    """
    from datetime import datetime


    time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    context = _get_context_for_file(_get_calling_file())

    log_entry = {
        "entry": {
            "level": 3,
            "message": message,
            "context": context,
            "exception": exception,
            "trace": _get_trace(exception),
            "time": time
        },
        "send_remote": send_remote
    }

    _log_queue.put(log_entry)

def realtime(message: str, exception: Exception|None = None, send_remote=True):
    """
        Adds a log entry with the provided message and exception message, if present.

        The stack trace will be logged as well and in case an exception is provided,
        the exception trace will be saved instead.

        This function will not block for IO operations.
        

        :param message: The message to write to the log.
        :param exception: The exception to log or None if no exception is to be logged.
        :param send_remote: If set to false, the log will not be sent to the remote logging server.
    """
    from datetime import datetime


    time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    context = _get_context_for_file(_get_calling_file())

    log_entry = {
        "entry": {
            "level": 4,
            "message": message,
            "context": context,
            "exception": exception,
            "trace": _get_trace(exception),
            "time": time
        },
        "send_remote": send_remote
    }

    _log_queue.put(log_entry)

#endregion

#endregion
