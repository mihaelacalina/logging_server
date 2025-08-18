__all__ = ["app_config"]

class Config:
    def __init__(self, file_path: str):
        self.dictionary = {}

        with open(file_path, "r") as file_handle:
            for line in file_handle.readlines():
                line = line.strip()

                if len(line) < 1:
                    continue

                if line[0] == "#":
                    continue

                [name, value] = line.split("=")

                self.dictionary[name] = value

    def get_string(self, name: str):
        if name not in self.dictionary:
            raise KeyError(f"Configuration file is missing an entry for \"{name}\".")
         
        return self.dictionary[name]
    
    def get_int(self, name: str):
        if name not in self.dictionary:
            raise KeyError(f"Configuration file is missing an entry for \"{name}\".")
        
        return int(self.dictionary[name])
    
    def get_path(self, name: str):
        from os.path import abspath

        if name not in self.dictionary:
            raise KeyError(f"Configuration file is missing an entry for \"{name}\".")
        
        return abspath(self.dictionary[name])
    
    def get_bool(self, name: str):
        from os.path import abspath

        if name not in self.dictionary:
            raise KeyError(f"Configuration file is missing an entry for \"{name}\".")
        
        return str.lower(self.dictionary[name]) == "true"

app_config = Config("files/config.cfg")