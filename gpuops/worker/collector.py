

import logging
from typing import Callable, Optional
from gpuops.client.generated_clientset import ClientSet

from gpuops.detectors.base import GPUDetectExepction
from gpuops.detectors.custom.custom import Custom
from gpuops.detectors.detector_factory import DetectorFactory

from gpuops.config.config import Config
from gpuops.schemas.workers import WorkerStatus, WorkerStatusPublic
from gpuops.utils.profiling import time_decorator
from gpuops.envs import WORKER_STATUS_COLLECTION_LOG_SLOW_SECONDS

logger = logging.getLogger(__name__)

class WorkerStatusCollector:
    _cfg: Config
    
    def __init__(
        self,
        cfg: Config,
        worker_ip_getter: Callable[[], str],
        worker_ifname_getter: Callable[[], str],
        worker_id_getter: Callable[[], int],
        worker_uuid_getter: Callable[[], str],
    ):
        self._cfg = cfg
        self._worker_ip_getter = worker_ip_getter
        self._worker_ifname_getter = worker_ifname_getter
        self._worker_id_getter = worker_id_getter
        self._worker_uuid_getter = worker_uuid_getter
        
        self._gpu_devices = cfg.get_gpu_devices()
        self._system_info = cfg.get_system_info()
        if self._gpu_devices and self._system_info:
            self._detector_factory = DetectorFactory(
                device="custom",
                gpu_detectors={"custom": [Custom(gpu_devices=self._gpu_devices)]},
                system_info_detector=Custom(system_info=self._system_info),
            )
        elif self._gpu_devices:
            self._detector_factory = DetectorFactory(
                device="custom",
                gpu_detectors={"custom": [Custom(gpu_devices=self._gpu_devices)]},
            )
        elif self._system_info:
            self._detector_factory = DetectorFactory(
                system_info_detector=Custom(system_info=self._system_info)
            )
        else:
            self._detector_factory = DetectorFactory()
    
    """A class for collecting worker status information."""
    @time_decorator(log_slow_seconds=WORKER_STATUS_COLLECTION_LOG_SLOW_SECONDS)
    def timed_collect(self, clientset: ClientSet = None, initial: bool = False): # type: ignore
        return self.collect(clientset=clientset, initial=initial)

    def collect(
        self, clientset: Optional[ClientSet] = None, initial: bool = False
    ) -> WorkerStatusPublic:
        """Collect worker status information."""
        status = WorkerStatus.get_default_status()
        state_message = None
        
        try:
            system_info = self._detector_factory.detect_system_info()
            status = WorkerStatus.model_validate({**system_info.model_dump()})
        except Exception as e:
            logger.error(f"Failed to detect system info: {e}")
            
        if not initial:
            try:
                gpu_devices = self._detector_factory.detect_gpus()
                status.gpu_devices = gpu_devices
            except GPUDetectExepction as e:
                state_message = str(e)
            except Exception as e:
                logger.error(f"Failed to detect GPU devices: {e}")
        self._inject_unified_memory(status)
        self._inject_computed_filesystem_usage(status)
        self._inject_allocated_resource(clientset, status)
        
        return WorkerStatusPublic(
            advertise_address=self._cfg.advertise_address or self._worker_ip_getter(),
            hostname=socket.gethostname(),
            ip=self._worker_ip_getter(),
            ifname=self._worker_ifname_getter(),
            port=self._cfg.worker_port,
            metrics_port=metrics_port,
            system_reserved=SystemReserved(**self._cfg.get_system_reserved()),
            state_message=state_message,
            status=status,
            worker_uuid=self._worker_uuid_getter(),
        )
        