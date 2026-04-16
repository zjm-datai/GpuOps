
import logging
from fastapi import APIRouter

from gpuops.server.db import async_session


router = APIRouter()
system_name_prefix = "system/worker"
logger = logging.getLogger(__name__)

@router.post("", response_model=WorkerRegistrationPublic)
async def create_worker(user: CurrentUserDep, worker_in: WorkerCreate):
    
    async with async_session() as session:
        cluster_id = (
            
        )