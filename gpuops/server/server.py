


import asyncio
import logging
from multiprocessing import Process
import os
import re

import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel.ext.asyncio.session import AsyncSession

from gpuops.config.config import Config
from gpuops.logging import setup_logging

from gpuops.schemas.users import User
from gpuops.security import generate_secure_password, get_secret_hash
from gpuops.server.db import async_session
from gpuops.server.init_db import init_db
from gpuops.server.app import create_app
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
        
        self._run_migrations()
        await self._prepare_data()
        
        if self._config.server_role() == Config.ServerRole.BOTH:
            self._sub_processes.append(self._worker_process)
            
        # Start FastAPI server
        app = create_app(self._config)
        app.state.server_config = self._config
        
        if self._config.enable_cors:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=self._config.allow_origins, # type: ignore
                allow_credentials=self._config.allow_credentials,
                allow_methods=self._config.allow_methods, # type: ignore
                allow_headers=self._config.allow_headers, # type: ignore
            )
        
        serving_host = (
            "127.0.0.1"
        )
        
        config = uvicorn.Config(
            app,
            host=serving_host,
            port=self._config.get_api_port(), # type: ignore
            access_log=False,
            log_level="error"
        )
        
        setup_logging()

        serving_api_message = f"Serving GPUStack API on {config.host}:{config.port}."
        
        logger.info(serving_api_message)

        server = uvicorn.Server(config)
        self._create_async_task(server.serve())

        await asyncio.gather(*self._async_tasks)
        
    def _run_migrations(self):
        logger.info("Running database migration.")
        from alembic import command
        from alembic.config import Config as AlembicConfig
        import importlib.util

        spec = importlib.util.find_spec("gpuops")
        if spec is None:
            raise ImportError("The 'gpuops' package is not found.")

        pkg_path = spec.submodule_search_locations[0] # type: ignore
        alembic_cfg = AlembicConfig()
        alembic_cfg.set_main_option(
            "script_location", os.path.join(pkg_path, "migrations")
        )

        db_url = self._config.get_database_url()
        # Use the pymysql driver to execute migrations to avoid compatibility issues between asynchronous drivers and Alembic.
        if db_url.startswith("mysql://"):
            db_url = re.sub(r'^mysql://', 'mysql+pymysql://', db_url)
        db_url_escaped = db_url.replace("%", "%%")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url_escaped)
        try:
            command.upgrade(alembic_cfg, "head")
        except Exception as e:
            raise RuntimeError(f"Database migration failed: {e}") from e
        logger.info("Database migration completed.")

    async def _prepare_data(self):
        self._setup_data_dir(self._config.data_dir) # type: ignore

        await init_db(self._config.get_database_url())

        # async with async_session() as session:
        #     await self._init_data(session)

        logger.debug("Data initialization completed.")
        
    @staticmethod
    def _setup_data_dir(data_dir: str):
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
    async def _init_data(self, session: AsyncSession):
        init_data_funcs = [
            self._init_user,
        ]
        
        for init_data_func in init_data_funcs:
            await init_data_func(session)
    
    async def _init_user(self, session: AsyncSession):
        user = await User.first_by_field(
            session=session, field="username", value="admin"
        )
        if not user:
            bootstrap_password = self._config.bootstrap_password
            require_password_change = False
            if not bootstrap_password:
                require_password_change = True
                bootstrap_password = generate_secure_password()
                bootstrap_password_file = os.path.join(self._config.data_dir, "initial_admin_password") # type: ignore
                with open(bootstrap_password_file, "w") as file:
                    file.write(bootstrap_password + "\n")
                logger.info(
                    "Generated initial admin password. "
                    f"You can get it from {bootstrap_password_file}"
                )

            user = User(
                username="admin",
                full_name="Default System Admin",
                hashed_password=get_secret_hash(bootstrap_password),
                is_admin=True,
                require_password_change=require_password_change,
            )
            await User.create(session, user)