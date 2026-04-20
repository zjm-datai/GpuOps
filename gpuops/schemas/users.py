

from enum import Enum
import re
from typing import List, Optional

from pydantic import field_validator
from sqlalchemy import Enum as SQLEnum, Text, Integer, ForeignKey

from sqlmodel import (
    Field,
    Column,
    Relationship, 
    SQLModel
)

from gpuops.mixins import BaseModelMixin
from gpuops.worker.worker import Worker


class UseRole(Enum):
    Worker = "Worker"
    Cluster = "Cluster"
    
class AuthProviderEnum(str, Enum):
    Local = "Local"
    OIDC = "OIDC"
    SAML = "SAML"
    
class UserBase(SQLModel):
    username: str
    is_admin: bool = False
    is_active: bool = True
    full_name: Optional[str] = None
    avatar_url: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    source: Optional[str] = Field(
        default=AuthProviderEnum.Local, sa_type=SQLEnum(AuthProviderEnum) # type: ignore
    )
    require_password_change: bool = Field(default=False)
    
    is_system: bool = False
    role: Optional[UserRole] = Field( # type: ignore
        default=None, description="Role of the user, e.g., worker or cluster"
    )
    cluster_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("clusters.id", ondelete="CASCADE")),
    )
    worker_id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("workers.id", ondelete="CASCADE")),
    )
    
class UserCreate(UserBase):
    password: str
    
    @field_validator('password')
    def validate_password(cls, value):
        if not re.search(r'[A-Z]', value):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', value):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', value):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*_+]', value):
            raise ValueError('Password must contain at least one special character')
        return value
    
class UserUpdate(UserBase):
    password: Optional[str] = None
    
class User(UserBase, BaseModelMixin, table=True):
    __tablename__ = 'users' # type: ignore
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    
    cluster: Optional[Cluster] = Relationship(
        back_populates="cluster_users", sa_relationship_kwargs={"lazy": "noload"}
    )
    worker: Optional[Worker] = Relationship(sa_relationship_kwargs={"lazy": "noload"})

    api_keys: List["ApiKey"] = Relationship( # type: ignore
        back_populates='user',
        sa_relationship_kwargs={"cascade": "delete", "lazy": "noload"},
    )
    routes: List["ModelRoute"] = Relationship( # type: ignore
        back_populates="users",
        link_model=UserModelRouteLink,
        sa_relationship_kwargs={"lazy": "noload"},
    )