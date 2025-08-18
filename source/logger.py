from queue import Queue

_running_log_thread = False
_message_queue = Queue()


def log(source: str, level: int, category: str, message: str, trace: str):
    _message_queue.put((level, message, trace, source, category))

def _cleanup(database):
    from app_config import app_config

    info("Log cleanup started.")

    max_entries = app_config.get_int("logger.max_entries")
    database.execute(
        f"""
            DELETE FROM logs
            WHERE id NOT IN (
                SELECT id FROM your_log_table
                ORDER BY id DESC
                LIMIT {max_entries}
            );
        """
    )
    
    database.commit()

    info("Log cleanup finished.")

def _thread():
    from queue import Empty as QueueEmptyException
    from sqlite3 import connect as sqlite
    from app_log import wrap_exception
    from app_config import app_config
    import schedule as scheduler


    database = sqlite(app_config.get_path("logger.log_file"))

    database.execute(
        """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT NOT NULL,

                source TEXT NOT NULL,
                category TEXT NOT NULL,

                level INTEGER NOT NULL,
                message TEXT NOT NULL,
                trace TEXT
            );
        """
    )

    scheduler.every().day.at("04:30").do(_cleanup)
    scheduler.every().second.do(database.commit)

    while True:
        scheduler.run_pending()

        if not _running_log_thread:
            break

        try:
            log = _message_queue.get(timeout=1.0)

            try:
                database.execute("INSERT INTO logs (time, level, message, trace, source, category) VALUES (DATETIME('now'), ?, ?, ?, ?, ?);", log)
            except Exception as exception:
                wrap_exception("Exception occured while writing to database", exception)
        except QueueEmptyException:
            pass
    
    database.commit()

def stop():
    from app_log import info
    

    global _running_log_thread

    info("Logging thread is shutting down.")

    _running_log_thread = False

if __name__ != "__main__":
    from threading import Thread
    from app_log import info


    if _running_log_thread:
        raise RuntimeError("Logger reached an illegal state")
    
    info("Logging thread is starting up.")
    
    _running_log_thread = True
    Thread(target=_thread).start()