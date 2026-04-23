
import logging
import secrets
from typing import Optional
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from gpuops.api.exceptions import NotFoundException
from gpuops.schemas.config import SensitivePredefinedConfig
from gpuops.schemas.workers import WorkerCreate, WorkerPublic, WorkerListParams, WorkerRegistrationPublic
from gpuops.server.db import async_session
from gpuops.server.deps import CurrentUserDep
from gpuops.worker.worker import Worker


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
        all_workers = await Worker.all_by_fields(session, {"deteled_at": None})
        existing_worker = get_existing_worker(cluster_id, worker_in, all_workers)
        check_worker_name_conflict(
            worker_in.name,
            all_workers,
            existing_id=existing_worker.id if existing_worker else None
        )
        if existing_worker is None:
            raise NotFoundException(message="worker not found") # type: ignore
        else:
            existing_worker = await Worker.one_by_id(
                session=session, id=existing_worker.id, for_update=True
            )
        
        cluster = await Cluster.one_by_id(session, cluster_id)
        if cluster is None or cluster.deleted_at is not None:
            raise NotFoundException(message="Cluster not found") # type: ignore
        
        sensitive_fields = set(SensitivePredefinedConfig.model_fields.keys())
        
        worker_config = (
            {}
            if cluster.worker_config is None
            else cluster.worker_config.model_dump(exclude=sensitive_fields)
        )
        cfg = get_global_config()
        if (
            cfg.system_default_container_registry is not None
            and len(cfg.system_default_container_registry) > 0
        ):
            worker_config.setdefault(
                "system_default_container_registry",
                cfg.system_default_container_registry,
            )
            
        hashed_suffix = secrets.token_hex(6)
        access_key = secrets.token_hex(8)
        secret_key = secrets.token_hex(16)
        new_token = f"{API_KEY_PREFIX}_{access_key}_{secret_key}"
        
        new_worker = update_worker_data(
            worker_in,
            existing=existing_worker,
            # following args are only used when creating a new worker
            provider=cluster.provider,
            cluster=cluster,
            token=new_token,
        )
        if new_worker.worker_uuid == "":
            new_worker.worker_uuid = retry_create_unique_worker_uuid(all_workers)

        # determine if existing worker already has an user and api key
        existing_user = (
            await User.one_by_field(
                session=session, field="worker_id", value=existing_worker.id
            )
            if existing_worker
            else None
        )
        
        to_create_user = (
            User(
                username=f'{system_name_prefix}-{hashed_suffix}',
                is_system=True,
                role=UserRole.Worker,
                hashed_password="",
                cluster=cluster,
            )
            if not existing_user
            else None
        )
        
        existing_api_key = (
            existing_user.api_keys[0]
            if existing_user
            and existing_user.api_keys
            and len(existing_user.api_keys) > 0
            else None
        )

        to_create_apikey = (
            ApiKey(
                name=f'{system_name_prefix}-{hashed_suffix}',
                access_key=access_key,
                hashed_secret_key=get_secret_hash(secret_key),
            )
            if not existing_api_key
            else None
        )

        try:
            worker = None
            if existing_worker is not None:
                if to_create_apikey is not None:
                    new_worker.token = new_token
                await WorkerService(session).update(
                    existing_worker, new_worker, auto_commit=False
                )
                worker = existing_worker
            else:
                worker = await retry_create_worker(session, new_worker, all_workers)
            created_user = None
            if to_create_user is not None:
                to_create_user.worker = worker
                created_user = await User.create(
                    session=session, source=to_create_user, auto_commit=False
                )
            if to_create_apikey is not None:
                to_create_apikey.user = existing_user or created_user
                to_create_apikey.user_id = (existing_user or created_user).id
                await ApiKey.create(
                    session=session, source=to_create_apikey, auto_commit=False
                )
            if cluster.state != ClusterStateEnum.READY:
                cluster.state = ClusterStateEnum.READY
                await cluster.update(session=session, auto_commit=False)
            await session.commit()
            worker_dump = worker.model_dump()
            worker_dump["token"] = worker.token
            worker_dump["worker_config"] = (
                PredefinedConfigNoDefaults.model_validate(worker_config)
            )

            return WorkerRegistrationPublic.model_validate(worker_dump)
        except Exception as e:
            await session.rollback()
            raise InternalServerErrorException(
                message=f"Failed to create worker: {e}"
            )
