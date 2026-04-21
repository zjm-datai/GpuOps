


import asyncio
import logging
from typing import Optional

import tenacity
import setproctitle

from gpuops import envs
from gpuops.config.config import Config
from gpuops.client import ClientSet
from gpuops.logging import setup_logging
from gpuops.utils.process import add_signal_handlers_in_loop
from gpuops.utils.uuid import get_worker_name
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
    
    def worker_name(self) -> Optional[str]:
        return (
            self._config.worker_name
            or self._worker_name
            or get_worker_name(self._config.data_dir) # type: ignore
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
        
    def start(self):
        setup_logging(self._config.debug)
        
        if self._is_embedded:
            setproctitle.setproctitle("gpuops_worker")
            
        try:
            asyncio.run(self.start_async())
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        except Exception as e:
            logger.error(f"Error serving worker APIs: {e}")
        finally:
            logger.info("Worker has shut down.")
            
    async def start_async(self):
        """
        Start the worker.
        """
        
        logger.info("Starting GPUOps worker.")
        
        add_signal_handlers_in_loop()
        
        await self._register()
        self._config.reload_worker_config(self._default_config)
        self.log_worker_config()
        
        # Send heartbeat to the server every WORKER_HEARTBEAT_INTERVAL seconds.
        run_periodically_in_thread(self._heartbeat, envs.WORKER_HEARTBEAT_INTERVAL)
        
        logger.info("GPUOps worker startup completed.")

        await asyncio.gather(*self._async_tasks)
        
    def _heartbeat(self):
        """
        Send heartbeat to the server to indicate the worker is alive.
        """
        
        if self._worker_ip is None:
            logger.debug("Worker ID is not set, skipping hearbeat.")
            return 
        try:
            resp = self._clientset.http_client.get_httpx_client().post(
                "/worker-heartbeat", json={}
            )
            if resp.status_code != 204:
                logger.error(
                    f"Failed to send heartbeat to server, status code: {resp.status_code}"
                )
        except Exception as e:
            logger.error(f"Failed to send heartbeat to server: {e}")