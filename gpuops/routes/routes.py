


from fastapi import APIRouter

from gpuops.api.exceptions import error_responses
from gpuops.routes import (
    workers
)

cluster_client_router = APIRouter()
cluster_client_router.add_api_route(
    path="/workers",
    endpoint=workers.create_worker,
    methods=["POST"],
)

model_routers = [
    
]

# worker client have full access to model and model instances
worker_client_router = APIRouter()
for model_router in model_routers:
    worker_client_router.include_router(**model_router)



admin_routers = model_routers + [
    
]

api_router = APIRouter(responses=error_responses) # type: ignore

# Following routes should not check api scope as it is publicly accessible 
# and used for authentication by external services.
