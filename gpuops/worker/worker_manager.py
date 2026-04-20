


from typing import Optional, Tuple

from gpuops.config.config import Config
from gpuops.client import ClientSet
from gpuops.client.worker_manager_clients import (
    WorkerStatusClient,
    WorkerRegistrationClient,
)
from gpuops.config.registration import read_worker_token


class WorkerManager:
    
    _is_embedded: bool
    _clientset: Optional[ClientSet] = None
    
    def __init__(
        self,
        cfg: Config,
        is_embedded: bool,
    ):
        
        self._cfg = cfg
        self._is_embedded = is_embedded
        worker_token = read_worker_token(self._cfg.data_dir)
        if worker_token:
            self._prepare_clients(worker_token)
            
    def _prepare_clients(self, token: str):
        self._clientset = ClientSet(
            base_url=self._cfg.get_server_url(),
            api_key=token,
        )
        self._status_client = WorkerStatusClient(self._clientset.http_client)
    
    async def register_with_server(
        self
    ) -> Tuple[ClientSet, Optional[PredefinedConfigNoDefaults]]:
        # always re-register the worker and retrive the token and config
        