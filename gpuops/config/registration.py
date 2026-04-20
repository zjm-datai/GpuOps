
import os
from typing import Optional

worker_token_filename = "worker_token"

def read_token(data_dir: str, filename) -> Optional[str]:
    token_path = os.path.join(data_dir, filename)
    if os.path.exists(token_path):
        with open(token_path, "r") as f:
            return f.read().strip()
    return None

def read_worker_token(data_dir: str) -> Optional[str]:
    return read_token(data_dir, worker_token_filename)