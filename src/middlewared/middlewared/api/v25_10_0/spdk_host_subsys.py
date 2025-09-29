from typing import Literal
from .spdk_host import  SPDKHostEntry
from middlewared.api.base import BaseModel, ForUpdateMetaclass
from .spdk_subsys import SPDKSubsysEntry

__all__ = [
    "SPDKHostSubsysEntry",
    "SPDKHostSubsysCreateArgs",
    "SPDKHostSubsysCreateResult",
    "SPDKHostSubsysUpdateArgs",
    "SPDKHostSubsysUpdateResult",
    "SPDKHostSubsysDeleteArgs",
    "SPDKHostSubsysDeleteResult",
]


class SPDKHostSubsysEntry(BaseModel):
    id: int
    host: SPDKHostEntry
    subsys: SPDKSubsysEntry


class SPDKHostSubsysCreate(BaseModel):
    host_id: int
    subsys_id: int


class SPDKHostSubsysCreateArgs(BaseModel):
    SPDK_host_subsys_create: SPDKHostSubsysCreate


class SPDKHostSubsysCreateResult(BaseModel):
    result: SPDKHostSubsysEntry


class SPDKHostSubsysUpdate(SPDKHostSubsysCreate, metaclass=ForUpdateMetaclass):
    pass


class SPDKHostSubsysUpdateArgs(BaseModel):
    id: int
    SPDK_host_subsys_update: SPDKHostSubsysUpdate


class SPDKHostSubsysUpdateResult(BaseModel):
    result: SPDKHostSubsysEntry


class SPDKHostSubsysDeleteArgs(BaseModel):
    id: int


class SPDKHostSubsysDeleteResult(BaseModel):
    result: Literal[True]
