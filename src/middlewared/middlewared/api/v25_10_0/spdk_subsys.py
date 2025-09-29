from typing import Literal, Optional

from pydantic import Field

from middlewared.api.base import NQN, BaseModel, Excluded, ForUpdateMetaclass, NonEmptyString, excluded_field

__all__ = [
    "SPDKSubsysEntry",
    "SPDKSubsysCreateArgs",
    "SPDKSubsysCreateResult",
    "SPDKSubsysUpdateArgs",
    "SPDKSubsysUpdateResult",
    "SPDKSubsysDeleteArgs",
    "SPDKSubsysDeleteResult",
]


class SPDKSubsysEntry(BaseModel):
    id: int
    name: NonEmptyString
    """
    Human readable name for the subsystem.

    If `subnqn` is not provided on creation, then this name will be appended to the `basenqn` from \
    `SPDK.global.config` to generate a subnqn.
    """
    subnqn: NonEmptyString | None = None
    serial: str
    allow_any_host: bool = False
    """Any host can access the storage associated with this subsystem (i.e. no access control)."""
    pi_enable: bool | None = None
    qid_max: int | None = None
    ieee_oui: str | None = None
    ana: bool | None = None
    """
    If set to either `True` or `False`, then *override* the global `ana` setting from `SPDK.global.config` for this \
    subsystem only.

    If `null`, then the global `ana` setting will take effect.
    """
    hosts: Optional[list[int]] = []
    """
    List of host ids which have access to this subsystem.

    Only populated on query if `extra.options.verbose` is set.
    """
    namespaces: Optional[list[int]] = []
    """
    List of namespaces ids in this subsystem.

    Only populated on query if `extra.options.verbose` is set.
    """
    ports: Optional[list[int]] = []
    """
    List of ports ids on which this subsystem is available.

    Only populated on query if `extra.options.verbose` is set.
    """

class SPDKSubsysCreate(SPDKSubsysEntry):
    id: Excluded = excluded_field()
    serial: Excluded = excluded_field()
    hosts: Excluded = excluded_field()
    namespaces: Excluded = excluded_field()
    ports: Excluded = excluded_field()
    subnqn: NQN | None = None


class SPDKSubsysCreateArgs(BaseModel):
    SPDK_subsys_create: SPDKSubsysCreate


class SPDKSubsysCreateResult(BaseModel):
    result: SPDKSubsysEntry


class SPDKSubsysUpdate(SPDKSubsysCreate, metaclass=ForUpdateMetaclass):
    pass


class SPDKSubsysUpdateArgs(BaseModel):
    id: int
    SPDK_subsys_update: SPDKSubsysUpdate


class SPDKSubsysUpdateResult(BaseModel):
    result: SPDKSubsysEntry


class SPDKSubsysDeleteOptions(BaseModel):
    force: bool = False
    """ Force subsystem deletion, even if currently associated with one or more namespaces or ports. """


class SPDKSubsysDeleteArgs(BaseModel):
    id: int
    options: SPDKSubsysDeleteOptions = Field(default_factory=SPDKSubsysDeleteOptions)


class SPDKSubsysDeleteResult(BaseModel):
    result: Literal[True]
