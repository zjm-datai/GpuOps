
from typing import Optional

from pydantic_settings import BaseSettings

from gpuops.schemas.config import PredefinedConfig

class WorkerConfig(PredefinedConfig):
    # common config which should be dynamic or not configurable
    data_dir: Optional[str] = None
    advertise_address: Optional[str] = None
    # Worker options which are different for each worker
    token: Optional[str] = None
    server_url: Optional[str] = None
    worker_ip: Optional[str] = None
    worker_ifname: Optional[str] = None
    worker_name: Optional[str] = None

class Config(WorkerConfig, BaseSettings):
    
    # The api_port is used in server/worker serving API requests.
    api_port: Optional[int] = 30080
    
    
    def get_server_url(self) -> str:
        # returns server if not None else returns embedded server url
        return (
            self.server_url or f"http://127.0.0.1:{self.api_port}"
            if self.api_port
            else "http://127.0.0.1"
        )