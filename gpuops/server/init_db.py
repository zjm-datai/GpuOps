

import re

from urllib.parse import urlparse, parse_qs, urlunparse

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine
)
from sqlmodel import SQLModel

from gpuops import envs
from gpuops.server import db


async def init_db(db_url: str):
    if db.engine is None:
        db.engine = await init_db_engine(db_url)
        # TODO: add listen_events(db.engine) to drop some views in db
    
    await create_db_and_tables(db.engine)
    
async def init_db_engine(db_url: str):
    connect_args = {}
    if db_url.startswith("postgresql://"):
        db_url = re.sub(r'^postgresql://', 'postgresql+asyncpg://', db_url)
        parsed = urlparse(db_url)
        # rewrite the parameters to use asyncpg with custom database schema
        query_params = parse_qs(parsed.query)
        qoptions = query_params.pop('options', None)
        schema_name = None
        if qoptions is not None and len(qoptions) > 0:
            option = qoptions[0]
            if option.startswith('-csearch_path='):
                schema_name = option[len('-csearch_path=') :]
        if schema_name:
            connect_args['server_settings'] = {'search_path': schema_name}
        new_parsed = parsed._replace(query={})
        db_url = urlunparse(new_parsed)
    elif db_url.startswith("mysql://"):
        db_url = re.sub(r'^mysql://', 'mysql+asyncmy://', db_url)
    else:
        raise Exception(f"Unsupported database URL: {db_url}")

    engine = create_async_engine(
        db_url,
        echo=envs.DB_ECHO,
        pool_size=envs.DB_POOL_SIZE,
        max_overflow=envs.DB_MAX_OVERFLOW,
        pool_timeout=envs.DB_POOL_TIMEOUT,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    
    return engine

async def create_db_and_tables(engine: AsyncEngine):
    async with engine.begin() as conn:
        await conn.run_sync(
            SQLModel.metadata.create_all,
            tables=[
                
            ]
        )