import secrets
import string
from typing import Union

from argon2 import PasswordHasher

ph = PasswordHasher()

def get_secret_hash(plain: Union[str, bytes]):
    return ph.hash(plain)

def generate_secure_password(length=12):
    if length < 8:
        raise ValueError("Password length should be at least 8 characters")

    special_characters = "!@#$%^&*_+"
    characters = string.ascii_letters + string.digits + special_characters
    while True:
        password = ''.join(secrets.choice(characters) for i in range(length))
        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in special_characters for c in password)
        ):
            return password