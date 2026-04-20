
from contextlib import asynccontextmanager

import aiohttp
from fastapi import FastAPI

from gpuops import __version__
from gpuops import envs
from gpuops.config import Config
from gpuops.routes.routes import api_router

def create_app(cfg: Config) -> FastAPI:
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        connector = aiohttp.TCPConnector(
            limit=envs.TCP_CONNECTOR_LIMIT,
            force_close=True,
        )
        app.state.http_client = aiohttp.ClientSession(
            connector=connector, trust_env=True
        )
        app.state.http_client_no_proxy = aiohttp.ClientSession(connector=connector)
        yield
        await app.state.http_client.close()
        await app.state.http_client_no_proxy.close()
    
    app = FastAPI(
        title="GPUOps",
        lifespan=lifespan,
        response_model_exclude_unset=True,
        version=__version__,
    )
    
    app.include_router(api_router)
    
    return app