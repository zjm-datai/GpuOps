
from enum import Enum
from typing import List, Optional

from pydantic_settings import BaseSettings

from gpuops.config.registration import read_registration_token
from gpuops.schemas.config import GatewayModeEnum, PredefinedConfig

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
    
    database_port: Optional[int] = 5432
    database_url: Optional[str] = None
    
    disable_worker: Optional[bool] = None
    enable_worker: bool = False
    
    enable_cors: bool = False
    allow_origins: Optional[List[str]] = ['*']
    allow_credentials: bool = False
    allow_methods: Optional[List[str]] = ['GET', 'POST']
    allow_headers: Optional[List[str]] = ['Authorization', 'Content-Type']
    
    bootstrap_password: Optional[str] = None
    
    def get_server_url(self) -> str:
        # returns server if not None else returns embedded server url
        return (
            self.server_url or f"http://127.0.0.1:{self.api_port}"
            if self.api_port
            else "http://127.0.0.1"
        )
        
    def _is_worker(self):
        return self.server_url is not None
    
    class ServerRole(Enum):
        SERVER = "server"
        WORKER = "worker"
        BOTH = "both"
        
    def server_role(self) -> ServerRole:
        if self._is_worker():
            return self.ServerRole.WORKER
        elif self._is_both_role():
            return self.ServerRole.BOTH
        else:
            return self.ServerRole.SERVER
        
    def _is_both_role(self) -> bool:
        """
        Determine if the server is running in both server and worker mode. If the
        `enable_worker` flag is set to True, the server is running in both modes. If the
        `disable_worker` flag is set to True, the server is running in server-only mode.
        If neither flag is set, the presence of a `bootstrap_version` file in the data
        directory is checked. If the file does not exist, it indicates that the server was
        installed using a version that defaults to running in both modes.

        Returns:
            bool: True if running in both server and worker mode, False otherwise.
        """
        if self._is_worker():
            return False
        elif self.enable_worker:
            return True
        elif self.disable_worker:
            return False
        
        return True
    
    def get_api_port(self, embedded_worker: bool = False):
        if embedded_worker:
            return self.worker_port
        if self.server_role() != self.ServerRole.WORKER:
            return self.api_port
        else:
            return self.worker_port
        
    def reload_token(self):
        token = read_registration_token(self.data_dir) # type: ignore   
        if token:
            self.token = token
        
    def get_database_url(self) -> str:
        if self.database_url is not None:
            return self.database_url
        return (
            f"postgresql://root@127.0.0.1:{self.database_port}/gpustack?sslmode=disable"
        )