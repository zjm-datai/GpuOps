
import logging
from fastapi import APIRouter

from gpuops.schemas.workers import WorkerCreate
from gpuops.server.db import async_session


router = APIRouter()
system_name_prefix = "system/worker"
logger = logging.getLogger(__name__)

@router.post("", response_model=WorkerRegistrationPublic)
async def create_worker(user: CurrentUserDep, worker_in: WorkerCreate):
    
    async with async_session() as session:
        cluster_id = (
            worker_in.cluster_id
            if worker_in.cluster_id is not None
            else user.cluster_id
        )
        if cluster_id is None:
            raise ForbiddenException(
                message="Missing cluster_id for worker registration"
            )
        all_workers = await Worker