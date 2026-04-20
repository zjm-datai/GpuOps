


import asyncio
import logging
from multiprocessing import Process

from gpuops.config.config import Config
from gpuops.utils.process import add_signal_handlers_in_loop

logger = logging.getLogger(__name__)

class Server:
    
    def __init__(self, config: Config, worker_process: Process):
        self._config: Config = config
        self._sub_processes = []
        self._async_tasks = []
        self._worker_process = worker_process
        
    @property
    def all_processes(self):
        return self._sub_processes

    def _create_async_task(self, coro):
        self._async_tasks.append(asyncio.create_task(coro))
        
    async def start(self):
        logger.info("Starting GPUOps server.")
        
        add_signal_handlers_in_loop()
        
        