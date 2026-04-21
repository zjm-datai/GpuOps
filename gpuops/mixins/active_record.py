
from typing import Any, List, Optional, Union
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import SQLModel, select

from gpuops.server.bus import Event, EventType, event_bus

class CommitEvent:
    name: str
    event: Event

    def __init__(self, name: str, type: EventType, data: Any):
        self.name = name
        self.event = Event(type=type, data=data)

class ActiveRecordMixin:
    """ActiveRecordMixin provides a set of methods to interact with the database."""
    
    __config__ = None
    
    @property
    def primary_key(self):
        """Return the primary key of the object."""

        return self.__mapper__.primary_key_from_instance(self) # type: ignore
    
    @classmethod
    async def first(cls, session: AsyncSession):
        """Return the first object of the model."""
        
        statement = select(cls)
        result = await session.exec(statement)
        return result.first()
    
    @classmethod
    async def one_by_id(
        cls,
        session: AsyncSession,
        id: int,
        for_update: bool = False,
        options: Optional[List] = None
    ):
        """Return the object with the given id. Return None if not found.
        
        If for `for update` is True, the row will be locked until the end of the transaction.
        If `options` is provided, it will be passed to the query for eager loading relationships.
        """
        
        return await session.get(cls, id, with_for_update=for_update, options=options)
    
    @classmethod
    async def first_by_field(cls, session: AsyncSession, field: str, value: Any):
        """Return the first object with the given field and value. Return None if not found."""

        return await cls.first_by_fields(session, {field: value})
    
    @classmethod
    async def first_by_fields(cls, session: AsyncSession, fields: dict):
        """Return the first object with the given fields and values.
        Return None if not found.
        """
        
        statement = select(cls)
        for key, value in fields.items():
            statement = statement.where(getattr(cls, key) == value)
        
        result = await session.exec(statement)
        
        return result.first()
    
    @classmethod
    async def one_by_fields(
        cls, session: AsyncSession, fields: dict, options: Optional[List] = None
    ):
        """Return the object with the given fields and values. Return None if not found."""
        
        statement = select(cls)
        for key, value in fields.items():
            statement = statement.where(getattr(cls, key) == value)

        if options:
            statement = statement.options(*options)

        result = await session.exec(statement)
        return result.first()
    
    @classmethod
    async def all_by_field(
        cls, session: AsyncSession, field: str, value: Any, for_update: bool = False
    ):
        """
        Return all objects with the given field and value.
        Return an empty list if not found.
        """
        statement = select(cls).where(getattr(cls, field) == value)
        if for_update:
            statement = statement.with_for_update()

        result = await session.exec(statement)
        return result.all()
    
    @classmethod
    def convert_without_saving(
        cls, source: Union[dict, SQLModel], update: Optional[dict] = None
    ) -> SQLModel:
        """
        Convert the source to the model without saving to the database.
        Return None if failed.
        """

        if isinstance(source, cls):
            obj = source
            if update:
                for k, v in update.items():
                    setattr(obj, k, v)
        elif isinstance(source, SQLModel):
            obj = cls.from_orm(source, update=update) # type: ignore
        elif isinstance(source, dict):
            obj = cls.parse_obj(source, update=update) # type: ignore
        return obj # type: ignore
    
    @classmethod
    def _publish_event_after_commit(
        cls, session: AsyncSession, event_type: str, data: Any
    ):
        session.info.setdefault("pending_events", []).append(
            CommitEvent(
                name=cls.__name__.lower(),
                type=event_type, # type: ignore
                data=data,
            )
        )
    
    @classmethod
    async def create(
        cls, session: AsyncSession, source: Union[dict, SQLModel], update: Optional[dict] = None, auto_commit: bool = True
    ):
        obj = cls.convert_without_saving(source, update)
        if obj is None:
            return None

        cls._publish_event_after_commit(session, EventType.CREATED, obj) # type: ignore
        await obj.save(session, auto_commit=auto_commit) # type: ignore
        return obj