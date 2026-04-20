

import argparse
import asyncio
import logging
import multiprocessing
import sys

from gpuops.config.config import Config
from gpuops.worker.worker import Worker

logger = logging.getLogger(__name__)


def setup_start_cmd(subparsers: argparse._SubParsersAction):
    parser_server: argparse.ArgumentParser = subparsers.add_parser(
        "start",
        help="Run GPUOps server or worker.",
        description="Run GPUOps server or worker.",
    )
    
    start_cmd_options(parser_server)

def start_cmd_options(parser_server: argparse.ArgumentParser):
    common_group = parser_server.add_argument_group("Common settings")
    
    common_group.add_argument(
        "--advertise-address",
        type=str,
        help="The IP address to expose for external access. If not set, the system will auto-detect a suitable local IP address.",
        default=get_gpuops_env("ADVERTISE_ADDRESS"),
    )
    
    common_group.add_argument(
        "--port",
        type=int,
        help="Port to bind the server to.",
        default=get_gpuops_env("PORT"),
    )
    
    common_group.add_argument(
        "--api-port",
        type=int,
        help="Port to bind the GPUOps API server to.",
        default=get_gpuops_env("API_PORT"),
    )
    common_group.add_argument(
        "--config-file",
        type=str,
        help="Path to the YAML config file.",
        default=get_gpuops_env("CONFIG_FILE"),
    )
    common_group.add_argument(
        "-d",
        "--debug",
        action=OptionalBoolAction,
        help="Enable debug mode.",
        default=get_gpuops_env_bool("DEBUG"),
    )
    common_group.add_argument(
        "--data-dir",
        type=str,
        help="Directory to store data. The default is OS specific.",
        default=get_gpuops_env("DATA_DIR"),
    )
    common_group.add_argument(
        "--cache-dir",
        type=str,
        help="Directory to store cache (e.g., model files). The default is <data-dir>/cache.",
        default=get_gpuops_env("CACHE_DIR"),
    )
    common_group.add_argument(
        "--bin-dir",
        type=str,
        help="Directory to store additional binaries, e.g., versioned backend executables.",
        default=get_gpuops_env("BIN_DIR"),
    )
    
    server_group = parser_server.add_argument_group("Server settings")
    
    server_group.add_argument(
        "--database-url",
        type=str,
        help="URL of the database. Example: postgresql://user:password@hostname:port/db_name.",
        default=get_gpuops_env("DATABASE_URL"),
    )
    
    # Embedded worker settings
    server_group.add_argument(
        "--disable-worker",
        action=OptionalBoolAction,
        help="(DEPRECATED) Disable the embedded worker for the GPUOps server. New installations will not have the embedded worker by default. Use '--enable-worker' to enable the embedded worker if needed. If neither flag is set, for backward compatibility, the embedded worker will be enabled by default for legacy installations prior to v2.0.1.",
        default=get_gpuops_env_bool("DISABLE_WORKER"),
    )
    server_group.add_argument(
        "--enable-worker",
        action=OptionalBoolAction,
        help="Enable the embedded worker for the GPUOps server.",
        default=get_gpuops_env_bool("ENABLE_WORKER"),
    )
    
    worker_group = parser_server.add_argument_group("Worker settings")
    
    worker_group.add_argument(
        "-t",
        "--token",
        type=str,
        help="Shared secret used to add a worker.",
        default=get_gpuops_env("TOKEN"),
    )
    worker_group.add_argument(
        "-s",
        "--server-url",
        type=str,
        help="Server to connect to.",
        default=get_gpuops_env("SERVER_URL"),
    )
    worker_group.add_argument(
        "--worker-ip",
        type=str,
        help="IP address of the worker node. Auto-detected by default.",
        default=get_gpuops_env("WORKER_IP"),
    )
    worker_group.add_argument(
        "--worker-ifname",
        type=str,
        help="Network interface name of the worker node. Auto-detected by default.",
        default=get_gpuops_env("WORKER_IFNAME"),
    )
    worker_group.add_argument(
        "--worker-name",
        type=str,
        help="Name of the worker node. Use the hostname by default.",
        default=get_gpuops_env("WORKER_NAME"),
    )
    worker_group.add_argument(
        "--worker-port",
        type=int,
        help="Port to bind the worker to.",
        default=get_gpuops_env("WORKER_PORT"),
    )
    worker_group.add_argument(
        "--service-port-range",
        type=str,
        help="Port range for inference services, specified as a string in the form 'N1-N2'. Both ends of the range are inclusive. The default is '40000-40063'.",
        default=get_gpuops_env("SERVICE_PORT_RANGE"),
    )
    
    worker_group.add_argument(
        "--log-dir",
        type=str,
        help="Directory to store logs.",
        default=get_gpuops_env("LOG_DIR"),
    )
    
    parser_server.set_defaults(func=run)
    
def run(args: argparse.Namespace):
    try:
        cfg = parse_args(args)
        setup_logging(cfg.debug)
        
        logger.info(f"GPUOps version: {__version__} ({__git_commit__})")
        
        if cfg.server_url:
            run_worker(cfg)
        else:
            run_server(cfg)
    except Exception as e:
        logger.exception(e)
        sys.exit(1)
        
def run_server(cfg: Config):
    worker = Worker(cfg)
    
    server = Server(
        config=cfg, worker_process=multiprocessing.Process(target=worker.start)
    )
    
    try:
        asyncio.run(server.start())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    except Exception:
        raise
    finally:
        logger.info("Server has shut down.")
        
def run_worker(cfg: Config):
    worker = Worker(cfg)

    worker.start()
    
def parse_args(args: argparse.Namespace) -> Config:
    config_data = []
    if args.config_file:
        config_data.update(load_config_from_yaml(args.config_file))
    
    # CLI args have higher priority than config file
    set_common_options(args, config_data)
    set_server_options(args, config_data)
    set_worker_options(args, config_data)

    try:
        cfg = Config(**config_data)
    except Exception as e:
        raise Exception(f"Config error: {e}")

    set_global_config(cfg)
    return cfg