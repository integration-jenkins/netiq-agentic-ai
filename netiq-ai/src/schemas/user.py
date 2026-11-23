"""User context, role definitions, and access credentials for NETIQ AI."""

from pydantic import BaseModel, ConfigDict, Field


class UserContext(BaseModel):
    """Authenticated user context for API requests and agent authorization."""
    model_config = ConfigDict(frozen=True)

    username: str = Field(..., description="Unique user identifier (e.g. employee ID or service account)")
    roles: list[str] = Field(default_factory=lambda: ["telecom_analyst"], description="Assigned RBAC roles")
    permitted_circles: list[str] = Field(
        default_factory=lambda: ["*"],
        description="List of telecom circles user is authorized to access (e.g. ['DL', 'MH'] or ['*'] for all)"
    )
    is_admin: bool = Field(default=False, description="Whether the user has administrative privileges")
    token: str | None = Field(default=None, description="Active authorization bearer token")

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role (case-insensitive)."""
        lower_roles = {r.lower() for r in self.roles}
        return role.lower() in lower_roles or self.is_admin

    def can_access_circle(self, circle: str | None) -> bool:
        """Check if user has access to a specific circle."""
        if self.is_admin or "*" in self.permitted_circles:
            return True
        if not circle:
            return False
        return circle.strip().upper() in {c.strip().upper() for c in self.permitted_circles}
