import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_db
from app.models import User

bearer = HTTPBearer(auto_error=False)
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600_000)
    return 'pbkdf2_sha256$600000$' + base64.b64encode(salt).decode() + '$' + base64.b64encode(digest).decode()

def verify_password(password: str, stored: str) -> bool:
    try:
        alg, rounds, salt, expected = stored.split('$')
        if alg != 'pbkdf2_sha256': return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), base64.b64decode(salt), int(rounds))
        return hmac.compare_digest(actual, base64.b64decode(expected))
    except (ValueError, TypeError): return False

def issue_token(user: User) -> str:
    s = get_settings()
    return jwt.encode({'sub': user.id, 'exp': datetime.now(timezone.utc) + timedelta(minutes=s.jwt_minutes)}, s.jwt_secret, algorithm=s.jwt_algorithm)

def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid or missing credentials', headers={'WWW-Authenticate':'Bearer'})
    if not credentials: raise error
    try:
        claims = jwt.decode(credentials.credentials, get_settings().jwt_secret, algorithms=[get_settings().jwt_algorithm])
        subject = claims.get('sub')
        if not isinstance(subject, str): raise error
        user = db.get(User, subject)
        if user is None or not user.active: raise error
        return user
    except jwt.PyJWTError: raise error
