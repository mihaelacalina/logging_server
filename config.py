from json import load

config = {
    "local_log_file": "files/local.log",
    "dedicated_log_file": "files/dedicated.sqlite",
    
    "dedicated_log_storage_period": 10,

    "host": "127.0.0.1",
    "port": 64000,
    "debug": True
}

with open("files/config.json") as handle:
    config = load(handle)