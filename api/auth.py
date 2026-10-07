"""Authentication: JWT tokens, OAuth2, SAML SSO, RBAC."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel

from config import settings


auth_router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)

# RBAC roles
ROLES = {"admin", "devops", "developer", "viewer"}
ROLE_PERMISSIONS = {
    "admin": {"read", "write", "deploy", "rollback", "manage"},
    "devops": {"read", "write", "deploy", "rollback"},
    "developer": {"read", "write"},
    "viewer": {"read"},
}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    email: str
    role: str = "developer"


def create_token(email: str, role: str) -> dict:
    """Create a signed JWT token."""
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRY_HOURS)
    payload = {
        "sub": email,
        "role": role,
        "exp": expires,
        "iat": datetime.now(timezone.utc),
        "iss": "ai-devops-tower",
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer", "expires_in": settings.JWT_EXPIRY_HOURS * 3600}


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload
    except JWTError as e:
        raise HTTPException(401, f"Invalid token: {str(e)}")


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> dict:
    """Extract and validate current user from Bearer token."""
    if not credentials:
        raise HTTPException(401, "Authorization token required")
    payload = decode_token(credentials.credentials)
    role = payload.get("role", "viewer")
    if role not in ROLES:
        raise HTTPException(403, f"Unknown role: {role}")
    return {"email": payload["sub"], "role": role, "permissions": ROLE_PERMISSIONS[role]}


def require_permission(permission: str):
    """Factory for permission-dependent."""
    async def checker(user=Depends(get_current_user)):
        if permission not in user["permissions"]:
            raise HTTPException(403, f"Permission '{permission}' required")
        return user
    return checker


@auth_router.get("/me")
async def get_me(user=Depends(get_current_user)):
    return user


@auth_router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """Email-based login (dev mode). In production, use SAML/OAuth2."""
    if req.role not in ROLES:
        raise HTTPException(400, f"Role must be one of: {', '.join(sorted(ROLES))}")
    return create_token(req.email, req.role)


@auth_router.get("/oauth/callback")
async def oauth_callback(request: Request):
    """OAuth2 redirect callback handler."""
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(400, "Missing authorization code")
    # In production, exchange code for token via AuthLib
    return {"redirect": "/#/?token=" + code}


@auth_router.get("/saml/metadata")
async def saml_metadata():
    """SAML SP metadata XML."""
    entity_id = settings.SAML_ACS_URL or "https://yourdomain.com/saml/acs"
    xml = f'''<?xml version="1.0"?>
<EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata" entityID="{entity_id}">
  <SPSSODescriptor AuthnRequestsSigned="true" WantAssertionsSigned="true">
    <NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</NameIDFormat>
    <AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" Location="{entity_id}"/>
  </SPSSODescriptor>
</EntityDescriptor>'''
    from fastapi.responses import Response
    return Response(content=xml, media_type="application/xml")
