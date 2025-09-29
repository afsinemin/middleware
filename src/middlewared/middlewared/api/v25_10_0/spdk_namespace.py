from typing import Annotated, Literal, TypeAlias

from pydantic import Field

from middlewared.api.base import BaseModel, Excluded, ForUpdateMetaclass, NormalPath, NonEmptyString, excluded_field
from .spdk_subsys import SPDKSubsysEntry

__all__ = [
    "SPDKNamespaceEntry",
    "SPDKNamespaceCreateArgs",
    "SPDKNamespaceCreateResult",
    "SPDKNamespaceUpdateArgs",
    "SPDKNamespaceUpdateResult",
    "SPDKNamespaceDeleteArgs",
    "SPDKNamespaceDeleteResult",
]


DeviceType: TypeAlias = Literal['ZVOL', 'FILE']


class SPDKNamespaceEntry(BaseModel):
    id: int
    nsid: Annotated[int, Field(ge=1, lt=0xFFFFFFFF)] | None = None
    """ Namespace ID (NSID).

    Each namespace within a subsystem has an associated NSID, unique within that subsystem.

    If not supplied during `namespace` creation then the next available NSID will be used.
    """
    subsys: SPDKSubsysEntry
    device_type: DeviceType
    """ Type of device (or file) used to implement the namespace. """
    device_path: NonEmptyString
    """
    Path to the device or file being used to implement the namespace.

    When `device_type` is:

    * "ZVOL": `device_path` is e.g. "zvol/poolname/zvolname"
    * "FILE": `device_path` is e.g. "/mnt/poolmnt/path/to/file". The file will be created if necessary.
    """
    filesize: int | None = None
    """When `device_type` is "FILE" then this will be the size of the file in bytes."""
    device_uuid: NonEmptyString
    device_nguid: NonEmptyString
    enabled: bool = True
    """
    If `enabled` is `False` then the namespace will not be accessible.

    Some namespace configuration changes are blocked when that namespace is enabled.
    """
    locked: bool | None
    """
    Reflect the locked state of the namespace.

    The underlying `device_path` could be an encrypted ZVOL, or a file on an encrypted dataset. In either case \
    `locked` will be `True` if the underlying entity is locked.
    """


class SPDKNamespaceCreate(SPDKNamespaceEntry):
    id: Excluded = excluded_field()
    subsys: Excluded = excluded_field()
    device_uuid: Excluded = excluded_field()
    device_nguid: Excluded = excluded_field()
    locked: Excluded = excluded_field()
    subsys_id: int
    device_path: NormalPath


class SPDKNamespaceCreateArgs(BaseModel):
    SPDK_namespace_create: SPDKNamespaceCreate


class SPDKNamespaceCreateResult(BaseModel):
    result: SPDKNamespaceEntry


class SPDKNamespaceUpdate(SPDKNamespaceCreate, metaclass=ForUpdateMetaclass):
    pass


class SPDKNamespaceUpdateArgs(BaseModel):
    id: int
    SPDK_namespace_update: SPDKNamespaceUpdate


class SPDKNamespaceUpdateResult(BaseModel):
    result: SPDKNamespaceEntry


class SPDKNamespaceDeleteOptions(BaseModel):
    remove: bool = False
    """Remove file underlying namespace if `device_type` is FILE."""


class SPDKNamespaceDeleteArgs(BaseModel):
    id: int
    options: SPDKNamespaceDeleteOptions = Field(default_factory=SPDKNamespaceDeleteOptions)


class SPDKNamespaceDeleteResult(BaseModel):
    result: Literal[True]
