import os
from datetime import datetime

class Slogger:
    log_path = "my_log.txt"

    @classmethod
    def log(cls, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"{timestamp} - {message}\n"

        with open(cls.log_path, "a", encoding="utf-8") as f:
            f.write(full_message)