"""Local authentication password hashing infrastructure adapters."""

import asyncio

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from argon2.low_level import Type

from docmind_api.domain.auth.local_accounts import PasswordHash, PasswordHashParameter

_FALLBACK_PASSWORD_HASH = PasswordHash(
    algorithm="argon2id",
    parameters=(
        PasswordHashParameter(name="time_cost", value="3"),
        PasswordHashParameter(name="memory_cost", value="65536"),
        PasswordHashParameter(name="parallelism", value="4"),
        PasswordHashParameter(name="hash_len", value="32"),
        PasswordHashParameter(name="salt_len", value="16"),
    ),
    hash_value=(
        "$argon2id$v=19$m=65536,t=3,p=4$Dl/7w+NGuV0k2cDL301KGA"
        "$4tW09hsXPLT4keCGl1DywNXlfDG5KD62r+aitUexnoE"
    ),
)


class Argon2idPasswordHasher:
    """Password hasher that persists Argon2id parameters with each hash."""

    algorithm = "argon2id"

    def __init__(
        self,
        *,
        time_cost: int = 3,
        memory_cost: int = 65536,
        parallelism: int = 4,
        hash_len: int = 32,
        salt_len: int = 16,
    ) -> None:
        self._hasher = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=hash_len,
            salt_len=salt_len,
            type=Type.ID,
        )
        self._parameters = (
            PasswordHashParameter(name="time_cost", value=str(time_cost)),
            PasswordHashParameter(name="memory_cost", value=str(memory_cost)),
            PasswordHashParameter(name="parallelism", value=str(parallelism)),
            PasswordHashParameter(name="hash_len", value=str(hash_len)),
            PasswordHashParameter(name="salt_len", value=str(salt_len)),
        )

    async def hash_password(self, plaintext_password: str) -> PasswordHash:
        """Hash a plaintext password using Argon2id."""

        hash_value = await asyncio.to_thread(self._hasher.hash, plaintext_password)

        return PasswordHash(
            algorithm=self.algorithm,
            parameters=self._parameters,
            hash_value=hash_value,
        )

    async def verify_password(self, plaintext_password: str, password_hash: PasswordHash) -> bool:
        """Return whether a plaintext password matches a stored hash."""

        if password_hash.algorithm != self.algorithm:
            return False

        try:
            return await asyncio.to_thread(
                self._hasher.verify,
                password_hash.hash_value,
                plaintext_password,
            )
        except InvalidHashError, VerificationError, ValueError:
            return False

    def verification_fallback_hash(self) -> PasswordHash:
        """Return a constant hash for failed local-login verification paths."""

        return _FALLBACK_PASSWORD_HASH
