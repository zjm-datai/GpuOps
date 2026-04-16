

from typing import Optional
from sqlmodel import SQLModel


class ClusterUpdate(SQLModel):
    
    name: str
    description: Optional[str] = None
    gateway_endpoint: Optional[str] = None
    server_url: Optional[str] = None
    
    