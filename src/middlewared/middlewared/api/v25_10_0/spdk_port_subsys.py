from typing import Literal

from middlewared.api.base import BaseModel, ForUpdateMetaclass
from .spdk_port import SPDKPortEntry
from .spdk_subsys import SPDKSubsysEntry

__all__ = [
    "SPDKPortSubsysEntry",
    "SPDKPortSubsysCreateArgs",
    "SPDKPortSubsysCreateResult",
    "SPDKPortSubsysUpdateArgs",
    "SPDKPortSubsysUpdateResult",
    "SPDKPortSubsysDeleteArgs",
    "SPDKPortSubsysDeleteResult",
]


class SPDKPortSubsysEntry(BaseModel):
    id: int
    port: SPDKPortEntry
    subsys: SPDKSubsysEntry


class SPDKPortSubsysCreate(BaseModel):
    port_id: int
    subsys_id: int


class SPDKPortSubsysCreateArgs(BaseModel):
    SPDK_port_subsys_create: SPDKPortSubsysCreate


class SPDKPortSubsysCreateResult(BaseModel):
    result: SPDKPortSubsysEntry


class SPDKPortSubsysUpdate(SPDKPortSubsysCreate, metaclass=ForUpdateMetaclass):
    pass


class SPDKPortSubsysUpdateArgs(BaseModel):
    id: int
    SPDK_port_subsys_update: SPDKPortSubsysUpdate


class SPDKPortSubsysUpdateResult(BaseModel):
    result: SPDKPortSubsysEntry


class SPDKPortSubsysDeleteArgs(BaseModel):
    id: int


class SPDKPortSubsysDeleteResult(BaseModel):
    result: Literal[True]
