from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class UserIdentity:
    issuer: str
    subject: str

    @property
    def owner_id(self) -> str:
        identity = f"{self.issuer}\0{self.subject}".encode("utf-8")
        return sha256(identity).hexdigest()
