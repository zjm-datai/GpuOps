
from typing import Annotated

from fastapi import Depends

from gpuops.schemas.common import ListParams
# from gpuops.schemas.users import User


# CurrentUserDep = Annotated[User, Depends(get_current_user)]
ListParamsDep = Annotated[ListParams, Depends(ListParams)]