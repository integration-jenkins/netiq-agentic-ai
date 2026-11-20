"""Security tests for circle boundary isolation and access control."""

import pytest
from src.security.circle_access import CircleAccessPolicy, UnauthorizedCircleError


def test_authorized_circle_access_succeeds():
    circle = CircleAccessPolicy.validate_circle_access(
        user_permitted_circles=["DELHI", "MUMBAI"],
        requested_circle="DELHI",
    )
    assert circle == "DELHI"


def test_unauthorized_circle_access_raises():
    with pytest.raises(UnauthorizedCircleError, match="not authorized to access circle 'KOLKATA'"):
        CircleAccessPolicy.validate_circle_access(
            user_permitted_circles=["DELHI", "MUMBAI"],
            requested_circle="KOLKATA",
        )


def test_admin_role_bypasses_circle_restriction():
    circle = CircleAccessPolicy.validate_circle_access(
        user_permitted_circles=["DELHI"],
        requested_circle="PUNJAB",
        user_roles=["admin"],
    )
    assert circle == "PUNJAB"


def test_wildcard_permitted_circle_allows_any_circle():
    circle = CircleAccessPolicy.validate_circle_access(
        user_permitted_circles=["*"],
        requested_circle="BIHAR",
    )
    assert circle == "BIHAR"


def test_single_permitted_circle_auto_defaults_when_none_requested():
    circle = CircleAccessPolicy.validate_circle_access(
        user_permitted_circles=["DELHI"],
        requested_circle=None,
    )
    assert circle == "DELHI"
