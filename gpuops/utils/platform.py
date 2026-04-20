
import os
import logging
import platform

logger = logging.getLogger(__name__)

def system() -> str:
    """
    Get the current operating system name in lowercase.
    """
    return platform.uname().system.lower()