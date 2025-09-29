from abc import ABC
from typing import Literal, TypeAlias

from pydantic import Field, field_validator

from middlewared.api.base import IPvAnyAddress, BaseModel, Excluded, ForUpdateMetaclass, NonEmptyString, excluded_field

__all__ = [
    "SPDKPortEntry",
    "SPDKPortCreateArgs",
    "SPDKPortCreateResult",
    "SPDKPortUpdateArgs",
    "SPDKPortUpdateResult",
    "SPDKPortDeleteArgs",
    "SPDKPortDeleteResult",
    "SPDKPortTransportAddressChoicesArgs",
    "SPDKPortTransportAddressChoicesResult"
]


FabricTransportType: TypeAlias = Literal['TCP', 'RDMA', 'FC']
AddressFamily: TypeAlias = Literal['IPV4', 'IPV6', 'FC']


class SPDKPortEntry(BaseModel):
    id: int
    index: int
    """ Index of the port, for internal use. """
    addr_trtype: FabricTransportType
    """ Fabric transport technology name. """
    addr_trsvcid: int | NonEmptyString | None
    """ Transport-specific TRSVCID field.  When configured for TCP/IP or RDMA this will be the port number. """
    addr_traddr: str
    """
    A transport-specific field identifying the NVMe host port to use for the connection to the controller.

    For TCP or RDMA transports, this will be an IPv4 or IPv6 address.
    """
    addr_adrfam: AddressFamily
    """ Address family."""
    inline_data_size: int | None = None
    max_queue_size: int | None = None
    pi_enable: bool | None = None
    # Not supported at this time
    # addr_tsas: str | None = None
    # """ Transport Specific Address Subtype. """
    # addr_treq: Literal['Not specified', 'Required', 'Not Required'] = 'Not specified'
    # """ Transport Requirements codes for Discovery Log Page entry TREQ field. """
    enabled: bool = True
    """ Port enabled.  When NVMe target is running, cannot make changes to an enabled port. """


class SPDKPortCreateTemplate(SPDKPortEntry, ABC):
    id: Excluded = excluded_field()
    index: Excluded = excluded_field()
    addr_adrfam: Excluded = excluded_field()


class SPDKPortCreateRDMATCP(SPDKPortCreateTemplate):
    addr_trtype: Literal['TCP', 'RDMA']
    addr_trsvcid: int = Field(ge=1024, le=65535)
    addr_traddr: IPvAnyAddress

    @field_validator('addr_traddr')
    @classmethod
    def normalize_addr_traddr(cls, value: str) -> str:
        if not value:
            raise ValueError('addr_traddr is required')
        return value


class SPDKPortCreateFC(SPDKPortCreateTemplate):
    addr_trtype: Literal['FC']
    addr_traddr: NonEmptyString
    addr_trsvcid: Excluded = excluded_field()


class SPDKPortCreateArgs(BaseModel):
    SPDK_port_create: SPDKPortCreateRDMATCP | SPDKPortCreateFC = Field(discriminator='addr_trtype')


class SPDKPortCreateResult(BaseModel):
    result: SPDKPortEntry


class SPDKPortUpdateRDMATCP(SPDKPortCreateRDMATCP, metaclass=ForUpdateMetaclass):
    pass


class SPDKPortUpdateFC(SPDKPortCreateFC, metaclass=ForUpdateMetaclass):
    pass


class SPDKPortUpdateArgs(BaseModel):
    id: int
    SPDK_port_update: SPDKPortUpdateRDMATCP | SPDKPortUpdateFC


class SPDKPortUpdateResult(BaseModel):
    result: SPDKPortEntry


class SPDKPortDeleteOptions(BaseModel):
    force: bool = False
    """ Optional `boolean` to force port deletion, even if currently associated with one or more subsystems. """


class SPDKPortDeleteArgs(BaseModel):
    id: int
    options: SPDKPortDeleteOptions = Field(default_factory=SPDKPortDeleteOptions)


class SPDKPortDeleteResult(BaseModel):
    result: Literal[True]


class SPDKPortTransportAddressChoicesArgs(BaseModel):
    addr_trtype: FabricTransportType
    """ Fabric transport technology name.  """
    force_ana: bool = False
    """ Return information as if ANA was enabled. """


class SPDKPortTransportAddressChoicesResult(BaseModel):
    result: dict[str, str]
