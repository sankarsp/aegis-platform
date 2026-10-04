"""Request identity and roles.

In AWS, the React app signs users in with Amazon Cognito (hosted UI, PKCE) and sends the Cognito
ID token as a Bearer token. We verify its signature against the user pool's JWKS, plus issuer,
audience and token use. Identity is the verified, unique email address; the display name is only
used for display. Roles come from Cognito groups.

Locally (no user pool configured) the X-User header or AEGIS_DEV_USER stands in for a signed-in
user, who holds every role.
"""

from dataclasses import dataclass, field
from functools import lru_cache

import jwt
from fastapi import Depends, Header, HTTPException

from .config import get_settings

# Cognito group name -> what it allows
ROLES = {
    "aegis-steward": "steward",  # sign off lineage, resolve issues, confirm labels, run tests, assign owners
    "aegis-approver": "approver",  # record approval steps, pause or resume models
    "aegis-admin": "admin",  # change access policies, rebuild the search index
}
ALL_ROLES = frozenset(ROLES.values())


@dataclass(frozen=True)
class User:
    id: str  # verified email; used for ownership and reviewer checks
    name: str
    roles: frozenset[str] = field(default_factory=frozenset)

    @property
    def label(self) -> str:
        """How the user appears in the audit log."""
        return self.name if self.name == self.id else f"{self.name} <{self.id}>"


@lru_cache
def _jwks_client(region: str, pool_id: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/jwks.json", cache_keys=True)


def current_user(authorization: str | None = Header(default=None), x_user: str | None = Header(default=None)) -> User:
    s = get_settings()
    if not s.cognito_user_pool_id:
        if x_user:
            return User(id=x_user, name=x_user, roles=ALL_ROLES)
        return User(id=s.dev_user_email, name=s.dev_user, roles=ALL_ROLES)
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Sign in required.")
    token = authorization.split(" ", 1)[1]
    issuer = f"https://cognito-idp.{s.aws_region}.amazonaws.com/{s.cognito_user_pool_id}"
    try:
        key = _jwks_client(s.aws_region, s.cognito_user_pool_id).get_signing_key_from_jwt(token)
        claims = jwt.decode(token, key.key, algorithms=["RS256"], audience=s.cognito_client_id, issuer=issuer)
    except jwt.PyJWTError as exc:
        raise HTTPException(401, "Your session could not be verified. Sign in again.") from exc
    if claims.get("token_use") != "id" or not claims.get("email_verified") or not claims.get("email"):
        raise HTTPException(401, "Sign in with a verified email address.")
    email = claims["email"].lower()
    roles = frozenset(ROLES[g] for g in claims.get("cognito:groups", []) if g in ROLES)
    return User(id=email, name=claims.get("name") or email, roles=roles)


def require(*roles: str):
    """Dependency: the user must hold at least one of these roles."""

    def check(user: User = Depends(current_user)) -> User:
        if not user.roles.intersection(roles):
            names = " or ".join(roles)
            raise HTTPException(403, f"This action needs the {names} role. Ask an Aegis admin to add you.")
        return user

    return check
