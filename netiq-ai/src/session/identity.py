"""Who is asking: the logged-in NETIQ user behind a chat request.

The login session itself belongs to src/security/netiq_login.py (not changed here). That
module keeps each user's NETIQ login reply under a session id and ends the session after
SESSION_IDLE_TIMEOUT seconds without activity (set to 1800 = 30 minutes in .env). This
module only reads that session and turns the login reply into a SessionUser.

Circle rule (same as NETIQ, confirmed by the team): ALL / PAN INDIA, or an empty or missing
circle list, means the user may see every circle. Circle names are turned into NETIQ's
2-letter codes first (UPE -> UE, KARNATAKA -> KK ...).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from fastapi import HTTPException, Request

from src.schemas.user import UserContext
from src.security import netiq_login

ALL_CIRCLES = "*"
_ALL_TOKENS = {"*", "ALL", "ALL CIRCLES", "ALL_CIRCLES", "PAN INDIA", "PAN-INDIA", "PAN_INDIA"}
# Copied from NETIQ's SecurityUtils.CIRCLE_ALIASES so the chatbot reads circle names the same way.
_ALIASES = {
    "UPE": "UE", "UP-E": "UE", "UP EAST": "UE", "UTTAR PRADESH EAST": "UE", "UTTAR PRADESH (EAST)": "UE",
    "UPW": "UW", "UP-W": "UW", "UP WEST": "UW", "UTTAR PRADESH WEST": "UW", "UTTAR PRADESH (WEST)": "UW",
    "KA": "KK", "KAR": "KK", "KARNATAKA": "KK", "OD": "OR", "ORI": "OR", "ORISSA": "OR", "ODISHA": "OR",
    "CH": "CN", "CHN": "CN", "CHENNAI": "CN", "MUM": "MU", "MUMBAI": "MU", "KOL": "KO", "CAL": "KO",
    "KOLKATA": "KO", "ROM": "MH", "MAH": "MH", "MAHARASHTRA": "MH", "MPCG": "MP", "MADHYA PRADESH": "MP",
    "NESA": "NE", "NORTH EAST": "NE", "J&K": "JK", "JAMMU AND KASHMIR": "JK", "JAMMU & KASHMIR": "JK",
    "BIH": "BR", "BIHAR": "BR", "GUJ": "GJ", "GUJARAT": "GJ", "RAJ": "RJ", "RAJASTHAN": "RJ",
    "HAR": "HR", "HARYANA": "HR", "PUN": "PB", "PUNJAB": "PB", "ASM": "AS", "ASSAM": "AS",
    "KER": "KL", "KERALA": "KL", "TAM": "TN", "TAMIL NADU": "TN", "DEL": "DL", "DELHI": "DL",
    "WBG": "WB", "WEST BENGAL": "WB", "ANDHRA PRADESH": "AP", "HIMACHAL PRADESH": "HP", "UTTAR PRADESH": "UP",
}


def normalize_circle(name: str) -> str:
    """One circle name or alias -> NETIQ code ("Delhi" -> "DL", "MH - Maharashtra" -> "MH")."""
    code = name.strip().upper().split(" - ")[0].strip()
    return _ALIASES.get(code, code)


# Circle names found inside a question. Only names of 4+ characters: short aliases such as
# HAR, DEL, CAL are everyday words ("har circle ka count" = every circle). Longest first, so
# "Uttar Pradesh East" is UE and not UP.
_NAME_IN_TEXT = re.compile(
    r"(?<![A-Za-z0-9])("
    + "|".join(r"\s+".join(map(re.escape, name.split())) for name in sorted(_ALIASES, key=len, reverse=True)
               if len(name) >= 4)
    + r")(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_CODES = frozenset(_ALIASES.values())
_CODE_THEN_CIRCLE = re.compile(r"\b([A-Za-z]{2})\s+circles?\b", re.IGNORECASE)  # "GJ circle", "br circle"


def circles_in_text(text: str) -> list[str]:
    """NETIQ circle codes named in a question: full names, or a 2-letter code followed by "circle".

    ponytail: word rules until entity extraction (task 3.3) can replace them.
    """
    found = [normalize_circle(" ".join(m.group(1).split())) for m in _NAME_IN_TEXT.finditer(text or "")]
    found += [m.group(1).upper() for m in _CODE_THEN_CIRCLE.finditer(text or "") if m.group(1).upper() in _CODES]
    return list(dict.fromkeys(found))


def allowed_circles(raw: list[str] | str | None) -> tuple[str, ...]:
    """The user's circle list as NETIQ codes; ("*",) means every circle."""
    items = raw.split(",") if isinstance(raw, str) else (raw or [])
    codes: list[str] = []
    for item in items:
        for part in str(item).split(","):
            if not part.strip():
                continue
            if part.strip().upper() in _ALL_TOKENS:
                return (ALL_CIRCLES,)
            code = normalize_circle(part)
            if code not in codes:
                codes.append(code)
    return tuple(codes) or (ALL_CIRCLES,)  # empty list = all circles, as in NETIQ


@dataclass(frozen=True)
class SessionUser:
    session_id: str
    username: str
    role: str | None
    permissions: frozenset[str]
    circles: tuple[str, ...]

    @classmethod
    def from_login(cls, session_id: str, login: dict) -> "SessionUser":
        username = str(login.get("username") or login.get("id") or "").strip()
        if not username:
            raise HTTPException(401, "Login reply has no username.")
        return cls(
            session_id=session_id,
            username=username,
            role=login.get("role"),
            permissions=frozenset(p["authority"] for p in login.get("permissions") or [] if p.get("authority")),
            circles=allowed_circles(login.get("circleList")),
        )

    @property
    def all_circles(self) -> bool:
        return self.circles == (ALL_CIRCLES,)

    def user_context(self) -> UserContext:
        """The same user in the shape the agents and access checks use."""
        return UserContext(username=self.username, roles=[self.role] if self.role else [],
                           permitted_circles=list(self.circles))


def current_user(request: Request) -> SessionUser:
    """FastAPI dependency: the logged-in user of this request, or 401.

    The session id comes from the same cookie / header that netiq_login uses. Reading it
    through netiq_login.get_user_info also resets that session's idle timer.
    """
    session_id = request.headers.get(netiq_login.SESSION_HEADER) or request.cookies.get(netiq_login.SESSION_COOKIE)
    login = netiq_login.get_user_info(session_id)
    if not login:
        raise HTTPException(401, "Not logged in or session expired. Please log in to NETIQ again.")
    return SessionUser.from_login(session_id, login)
