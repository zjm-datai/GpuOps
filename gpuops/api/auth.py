



from typing import Annotated, Optional
from fastapi import Depends, Request

from fastapi.security import HTTPAuthorizationCredentials, HTTPBasicCredentials
from sqlmodel.ext.asyncio.session import AsyncSession

from gpuops.config.config import Config
from gpuops.schemas.users import User
from gpuops.server.db import get_session


async def get_current_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    basic_credentials: Annotated[
        Optional[HTTPBasicCredentials], Depends(basic_auth)
    ] = None,
    bearer_token: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_auth)
    ] = None,
    cookie_token: Annotated[Optional[str], Depends(cookie_auth)] = None,
) -> Optional[User]:
    if hasattr(request.state, "user"):
        user: User = getattr(request.state, "user")
        return user
    api_key: Optional[ApiKey] = None
    user = None
    try:
        server_config: Config = request.app.state.server_config
        if basic_credentials and is_system_user(basic_credentials.username):
            user = await authenticate_system_user(server_config, basic_credentials)
        elif basic_credentials:
            user = await authenticate_basic_user(session, basic_credentials)
        elif cookie_token:
            jwt_manager: JWTManager = request.app.state.jwt_manager
            user = await get_user_from_jwt_token(session, jwt_manager, cookie_token)
        elif bearer_token:
            user, api_key = await get_user_from_bearer_token(session, bearer_token)

        if user is None and client_ip_getter(request=request) == "127.0.0.1":
            if not server_config.force_auth_localhost:
                user = await User.first_by_field(session, "is_admin", True)
        if user:
            if not user.is_active:
                raise UnauthorizedException(message="User account is deactivated")
            request.state.user = user
            if api_key is not None:
                request.state.api_key = api_key
            return user

    except UnauthorizedException:
        raise
    except Exception as e:
        raise InternalServerErrorException(message=f"Failed to authenticate user: {e}")