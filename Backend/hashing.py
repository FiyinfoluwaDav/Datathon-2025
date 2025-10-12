from passlib.context import CryptContext

# Simple wrapper used by routers/phc_auth.py
class Hash:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    @staticmethod
    def hashing(password: str) -> str:
        # Ensure caller trims to 72 chars if needed
        return Hash.pwd_context.hash(password)

    @staticmethod
    def verifying(plain_password: str, hashed_password: str) -> bool:
        return Hash.pwd_context.verify(plain_password, hashed_password)