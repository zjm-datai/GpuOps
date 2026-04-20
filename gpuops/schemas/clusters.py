

from enum import Enum
from typing import Dict, List, Optional
import sqlalchemy as sa
from sqlmodel import Field, ForeignKey, Integer, Relationship, SQLModel, Column, JSON

from gpuops.mixins import BaseModelMixin

class WorkerPoolUpdate(SQLModel):
    name: str
    batch_size: Optional[int] = Field(default=None, ge=1)
    replicas: int = Field(default=1, ge=0)
    labels: Optional[Dict[str, str]] = Field(sa_column=Column(JSON), default={})

    
class WorkerPoolCreate(WorkerPoolUpdate):
    instance_type: str
    os_image: str
    image_name: str
    zone: Optional[str] = None

class WorkerPoolBase(WorkerPoolCreate):
    cluster_id: int = Field(
        sa_column=Column(Integer, ForeignKey("clusters.id", ondelete="CASCADE"))
    )

class WorkerPool(WorkerPoolBase, BaseModelMixin, table=True):
    __tablename__ = "worker_pools"
    __table_args__ = (
        sa.Index("idx_worker_pools_deleted_at_created_at", "deleted_at", "created_at"),
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    cluster: Optional["Cluster"] = Relationship(
        back_populates="cluster_worker_pools",
        sa_relationship_kwargs={"lazy": "noload"},
    )

class ClusterProvider(Enum):
    Docker = "Docker"
    Kubernetes = "Kubernetes"

class ClusterUpdate(SQLModel):
    
    name: str
    description: Optional[str] = None
    gateway_endpoint: Optional[str] = None
    server_url: Optional[str] = None
    
class ClusterCreateBase(ClusterUpdate):
    provider: ClusterProvider = Field(default=ClusterProvider.Docker)
    region: Optional[str] = None
    
class ClusterCreate(ClusterCreateBase):
    worker_pools: Optional[List[WorkerPoolCreate]] = Field(default=None)
    