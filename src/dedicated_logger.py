from sqlite3 import Connection as SqliteConnection
from queue import Queue, Empty as QueueEmptyError
from threading import Event
from typing import TypedDict
from config import *
from logger import *
import schedule 


log_context("Dedicated Logger")

#region private

#region types

class TraceFrame(TypedDict):
    file: str
    line: int
    text: str

class RemoteLogEntry(TypedDict):
    time: str
    level: int
    message: str
    context: str
    app_name: str
    exception_message: str
    trace: list[TraceFrame]

class LogEntry(TypedDict, RemoteLogEntry):
    source: str

class DatabaseLogEntry(TypedDict, LogEntry):
    id: int

#endregion

#region sql statements

_create_statement = """
    create table if not exists logs (
        id integer primary key autoincrement not null,
        time text not null,
        level integer not null,
        source text not null,
        message text not null,
        context text not null,
        app_name text not null,
        exception_message text,
        trace text
    )
"""

_insert_statement = """
    insert into logs (
        time,
        level,
        source,
        message,
        context,
        app_name,
        exception_message,
        trace
    ) values (
        :time,
        :level,
        :source,
        :message,
        :context,
        :app_name,
        :exception_message,
        :trace
    );
"""

_delete_statement = """
    delete from logs where time < datetime('now', '-' || :days || ' days');
"""

#endregion

_log_start = Event()
_log_queue: Queue[LogEntry] = Queue()
_connection: SqliteConnection = None


def _commit():
    debug("Commiting to database.")

    try:
        _connection.commit()
    except Exception as exception:
        error("Unable to commit to database", exception)

def _periodic_deletion():
    debug("Performing periodic deletion.")

    try:
        _connection.execute(_delete_statement, {"days": config["dedicated_log_storage_period"]})
    except Exception as exception:
        error("Unable to perform deletion maintenance", exception)

def _thread():
    try:
        from sqlite3 import connect as sqlite
        from threading import main_thread
        from json import dumps
        
        global _connection
        

        _connection = sqlite(config["dedicated_log_file"])

        try:
            _connection.execute(_create_statement)
        except Exception as exception:
            warn("Unable to execute table create statement", exception)
        
        schedule.every().day.at("03:50").do(_periodic_deletion)
        schedule.every().second.do(_commit)

        _log_start.set()

        _periodic_deletion()
        
        while True:
            try:
                entry = _log_queue.get(timeout = 0.25)

                debug("Recieved log entry")
                debug(str(entry))

                entry["trace"] = dumps(entry["trace"], separators=(",", ":"))

                try:
                    _connection.execute(_insert_statement, entry)
                except Exception as exception:
                    warn("Unable to write log entry to database", exception)
            except QueueEmptyError:
                pass
            finally:
                try:
                    schedule.run_pending()
                except Exception as exception:
                    error("Error occured while running tasks", exception)

                # Exit the thread if all logs have been saved and the main thread is dead.

                if not main_thread().is_alive() and _log_queue.qsize() == 0:
                    break
    except Exception as exception:
        error("Thread died", exception)
    finally:
        _log_start.set()
        _commit()

#endregion

#region public

def start():
    """Starts the dedicated logger thread."""
    from threading import Thread
    

    Thread(target=_thread, name="Log Server", daemon=False).start()
    
    _log_start.wait()

def add_entry(entry: LogEntry):
    """Adds the provided log entry to the log queue."""


    _log_queue.put(entry)

#endregion