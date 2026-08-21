"""Role-based access control (RBAC) dependencies.

Maps ``UserRole`` to ``Permission`` sets and exposes ``require_role`` /
``require_permission`` dependency factories for endpoint protection.
"""

from __future__ import annotations

import enum
from collections.abc import Callable, Coroutine
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.auth import get_current_user
from app.auth.models import UserAuth, UserRole


class Permission(str, enum.Enum):
    """Fine-grained permissions checked by endpoints."""

    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    MODERATE = "moderate"


ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.ADMIN: frozenset(Permission),
    UserRole.MODERATOR: frozenset({Permission.READ, Permission.WRITE, Permission.MODERATE}),
    UserRole.USER: frozenset({Permission.READ, Permission.WRITE}),
}


def get_role_permissions(role: UserRole) -> frozenset[Permission]:
    """Return the permission set granted to a role."""
    return ROLE_PERMISSIONS.get(role, frozenset())


def require_role(
    *roles: UserRole,
) -> Callable[..., Coroutine[None, None, UserAuth]]:
    """Dependency factory: allow only users whose role is one of ``roles``.

    Usage::

        @router.post("/admin/action", dependencies=[Depends(require_role(UserRole.ADMIN))])
        async def admin_action(): ...
    """

    async def checker(current_user: Annotated[UserAuth, Depends(get_current_user)]) -> UserAuth:
        if current_user.role not in roles:
            allowed = ", ".join(sorted(r.value for r in roles))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires role [{allowed}], but user has '{current_user.role.value}'",
            )
        return current_user

    return checker


def require_permission(
    permission: Permission,
) -> Callable[..., Coroutine[None, None, UserAuth]]:
    """Dependency factory: allow only users whose role grants ``permission``.

    Usage::

        @router.delete("/items/{id}", dependencies=[Depends(require_permission(Permission.ADMIN))])
        async def delete_item(id: int): ...
    """

    async def checker(current_user: Annotated[UserAuth, Depends(get_current_user)]) -> UserAuth:
        if permission not in get_role_permissions(current_user.role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission '{permission.value}'",
            )
        return current_user

    return checker


# Convenience singletons
require_admin = require_role(UserRole.ADMIN)
require_moderator = require_role(UserRole.ADMIN, UserRole.MODERATOR)
