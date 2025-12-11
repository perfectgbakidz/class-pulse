from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    # bcrypt only supports passwords up to 72 bytes
    password = password[:72]
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    # truncate plain password too, just in case
    plain = plain[:72]
    return pwd_context.verify(plain, hashed)
