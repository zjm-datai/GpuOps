import hashlib
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from sqlalchemy import JSON
from sqlmodel import Field, SQLModel, Text
from gpuops.mixins import BaseModelMixin
from gpuops.schemas.common import pydantic_column_type

class SourceEnum(str, Enum):
    HUGGING_FACE = "huggingface"
    MODEL_SCOPE = "model_scope"
    LOCAL_PATH = "local_path"
    
class PlacementStrategyEnum(str, Enum):
    SPREAD = "spread"
    BINPACK = "binpack"
    
class GPUSelector(BaseModel):
    # format of each element: "worker_name:device:gpu_index", example: "worker1:cuda:0"
    gpu_ids: Optional[List[str]] = None
    gpus_per_replica: Optional[int] = None

class ModelSource(BaseModel):
    source: SourceEnum
    
    huggingface_repo_id: Optional[str] = None
    huggingface_filename: Optional[str] = None
    
    model_scope_model_id: Optional[str] = None
    model_scope_file_path: Optional[str] = None
    
    local_path: Optional[str] = None
    
    @property
    def model_source_key(self) -> str:
        """Returns a unique identifier for the model, independent of quantization."""
        if self.source == SourceEnum.HUGGING_FACE:
            return self.huggingface_repo_id or ""
        elif self.source == SourceEnum.MODEL_SCOPE:
            return self.model_scope_model_id or ""
        elif self.source == SourceEnum.LOCAL_PATH:
            return self.local_path or ""
        return ""
    
    @property
    def readable_source(self) -> str:
        values = []
        if self.source == SourceEnum.HUGGING_FACE:
            values.extend([self.huggingface_repo_id, self.huggingface_filename])
        elif self.source == SourceEnum.MODEL_SCOPE:
            values.extend([self.model_scope_model_id, self.model_scope_file_path])
        elif self.source == SourceEnum.LOCAL_PATH:
            values.extend([self.local_path])

        return "/".join([value for value in values if value is not None])
    
    @property
    def model_source_index(self) -> str:
        values = []
        if self.source == SourceEnum.HUGGING_FACE:
            values.extend([self.huggingface_repo_id, self.huggingface_filename])
        elif self.source == SourceEnum.MODEL_SCOPE:
            values.extend(
                [self.source, self.model_scope_model_id, self.model_scope_file_path]
            )
        elif self.source == SourceEnum.LOCAL_PATH:
            values.extend([self.local_path])

        # Filter out None values and join
        filtered_values = [v for v in values if v is not None]
        source_string = "/".join(filtered_values)
        return hashlib.sha256(source_string.encode()).hexdigest()
    
class ModelSpecBase(SQLModel, ModelSource):
    name: str = Field(index=True, unique=True)
    description: Optional[str] = Field(
        sa_type=Text, nullable=True, default=None
    )
    meta: Optional[Dict[str, Any]] = Field(sa_type=JSON, default={})
    
    replicas: int = Field(default=1, ge=0)
    ready_replicas: int = Field(default=0, ge=0)
    categories: List[str] = Field(sa_type=JSON, default=[])
    placement_strategy: PlacementStrategyEnum = PlacementStrategyEnum.SPREAD
    cpu_offloading: Optional[bool] = None
    
    worker_selector: Optional[Dict[str, str]] = Field(sa_type=JSON, default={})
    gpu_selector: Optional[GPUSelector] = Field(
        sa_type=pydantic_column_type(GPUSelector), default=None
    )
    
class ModelBase(ModelSpecBase):
    cluster_id: Optional[int] = Field(default=None, foreign_key="clusters.id")

class Model(ModelBase, BaseModelMixin, table=True):
    __tablename__ = 'models' # type: ignore
    
    id: Optional[int] = Field(default=None, primary_key=True)


# Model Instances

class ModelInstanceStateEnum(str, Enum):
    r"""
    Enum for Model Instance State

    Transitions:

       |- - - - - Scheduler - - - - |- - ServeManager - -|- - - - Controller - - - -|- ServeManager -|
       |                            |                    |                          |                |
    PENDING ---> ANALYZING ---> SCHEDULED ---> INITIALIZING ---> DOWNLOADING ---> STARTING ---> RUNNING
                     |            ^  |               |                |               |          ^
                     |            |  |               |                |               |          |(Worker ready)
                     |------------|--|---------------|----------------|---------------|----------|
                     \____________|_____________________________________________________________/|
                                  |                  ERROR                                       |(Worker unreachable)
                                  └--------------------┘                                         v
                                    (Restart on Error)                                       UNREACHABLE
    """

    INITIALIZING = "initializing"
    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    SCHEDULED = "scheduled"
    ERROR = "error"
    DOWNLOADING = "downloading"
    ANALYZING = "analyzing"
    UNREACHABLE = "unreachable"

    def __str__(self):
        return self.value