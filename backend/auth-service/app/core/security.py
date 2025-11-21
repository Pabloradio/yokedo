import bcrypt

def hash_password(password: str) -> str:
    """
    Hashes the given password using bcrypt.

    Returns:
        str: The hashed password as a UTF-8 string.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verifies a plaintext password against a hashed password.

    Returns:
        bool: True if the password matches the hash, False otherwise.
    """
    return bcrypt.checkpw(
        password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )
