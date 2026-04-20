


import logging

import tenacity

from gpuops.config.config import Config
from gpuops.client import ClientSet
from gpuops.worker.worker_manager import WorkerManager


logger = logging.getLogger(__name__)

class Worker:
    
    _clientset: ClientSet
    
    _worker_manager: WorkerManager
    
    def __init__(self, cfg: Config):
        
        self._config = cfg
        self._is_embedded = cfg.server_role() == Config.ServerRole.BOTH
        self._log_dir = cfg.log_dir
        self._address = "0.0.0.0"
        self._exporter_enabled = not cfg.disable_worker_metrics
        self._async_tasks = []
        self._worker_ip, self._worker_ifname = self._detect_worker_ip_and_ifname()
        
        self._worker_manager = WorkerManager(
            cfg=cfg,
            is_embedded=self._is_embedded,
            collector=self._status_collector,
        )
        
    @tenacity.retry(
        
    )
    async def _register(self):
        self._clientset, self._default_config = (
            await self._worker_manager.register_with_server()
        )
        # Worker ID is available after the worker registration.
        worker_list = self._clientset.workers.list(
            params={"me": 'true'}
        )
        name = self.worker_name() or "<not specified>"
        if len(worker_list.items) != 1:
            raise Exception(f"Worker {name} not registered.")
        
        self._worker_id = worker_list.items[0].id
        self._cluster_id = worker_list.items[0].cluster_id
        self._worker_name = worker_list.items[0].name
        self._worker_uuid = worker_list.items[0].worker_uuid