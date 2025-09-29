from typing import Literal, TypeAlias

from pydantic import Field, Secret, model_validator

from middlewared.api.base import NQN, BaseModel, Excluded, ForUpdateMetaclass, NonEmptyString, excluded_field

__all__ = [
    "SPDKHostEntry",
    "SPDKHostCreateArgs",
    "SPDKHostCreateResult",
    "SPDKHostUpdateArgs",
    "SPDKHostUpdateResult",
    "SPDKHostDeleteArgs",
    "SPDKHostDeleteResult",
    "SPDKHostGenerateKeyArgs",
    "SPDKHostGenerateKeyResult",
    "SPDKHostDhchapDhgroupChoicesArgs",
    "SPDKHostDhchapDhgroupChoicesResult",
    "SPDKHostDhchapHashChoicesArgs",
    "SPDKHostDhchapHashChoicesResult",
]

DHChapHashType: TypeAlias = Literal['SHA-256', 'SHA-384', 'SHA-512']
DHChapDHGroupType: TypeAlias = Literal['2048-BIT', '3072-BIT', '4096-BIT', '6144-BIT', '8192-BIT']


class SPDKHostEntry(BaseModel):
    id: int
    hostnqn: NonEmptyString
    """ NQN of the host that will connect to this TrueNAS. """
    dhchap_key: Secret[NonEmptyString | None] = None
    """
    If set, the secret that the host must present when connecting.

    A suitable secret can be generated using `nvme gen-dhchap-key`, or by using the `SPDK.host.generate_key` API.
    """
    dhchap_ctrl_key: Secret[NonEmptyString | None] = None
    """
    If set, the secret that this TrueNAS will present to the host when the host is connecting (Bi-Directional \
    Authentication).

    A suitable secret can be generated using `nvme gen-dhchap-key`, or by using the `SPDK.host.generate_key` API.
    """
    dhchap_dhgroup: DHChapDHGroupType | None = None
    """If selected, the DH (Diffie-Hellman) key exchange built on top of CHAP to be used for authentication."""
    dhchap_hash: DHChapHashType = 'SHA-256'
    """HMAC (Hashed Message Authentication Code) to be used in conjunction if a `dhchap_dhgroup` is selected."""


class SPDKHostCreate(SPDKHostEntry):
    id: Excluded = excluded_field()
    hostnqn: NQN

    @model_validator(mode='after')
    def validate_attrs(self):
        if self.dhchap_ctrl_key and not self.dhchap_key:
            raise ValueError('Cannot configure bi-directional authentication without setting dhchap_key')

        return self


class SPDKHostCreateArgs(BaseModel):
    SPDK_host_create: SPDKHostCreate


class SPDKHostCreateResult(BaseModel):
    result: SPDKHostEntry


class SPDKHostUpdate(SPDKHostCreate, metaclass=ForUpdateMetaclass):
    pass


class SPDKHostUpdateArgs(BaseModel):
    id: int
    SPDK_host_update: SPDKHostUpdate


class SPDKHostUpdateResult(BaseModel):
    result: SPDKHostEntry


class SPDKHostDeleteOptions(BaseModel):
    force: bool = False
    """ Force host deletion, even if currently associated with one or more subsystems. """


class SPDKHostDeleteArgs(BaseModel):
    id: int
    options: SPDKHostDeleteOptions = Field(default_factory=SPDKHostDeleteOptions)


class SPDKHostDeleteResult(BaseModel):
    result: Literal[True]


class SPDKHostGenerateKeyArgs(BaseModel):
    dhchap_hash: DHChapHashType = 'SHA-256'
    """ Hash to be used with the generated key.  """
    nqn: str | None = None
    """ NQN to be used for the transformation. """


class SPDKHostGenerateKeyResult(BaseModel):
    result: str


class SPDKHostDhchapDhgroupChoicesArgs(BaseModel):
    pass


class SPDKHostDhchapDhgroupChoicesResult(BaseModel):
    result: list[DHChapDHGroupType]


class SPDKHostDhchapHashChoicesArgs(BaseModel):
    pass


class SPDKHostDhchapHashChoicesResult(BaseModel):
    result: list[DHChapHashType]
