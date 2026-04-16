
from fastapi import FastAPI

from gpuops.config import Config

def create_app(cfg: Config) -> FastAPI:
    
    app = FastAPI(
        
    )
    
    return app