from middlewared.api.base import BaseModel, Excluded, ForUpdateMetaclass,  excluded_field, single_argument_args
from middlewared.api.base.types.spdk import NQN

__all__ = [
    "SPDKGlobalEntry",
    "SPDKGlobalUpdateArgs",
    "SPDKGlobalUpdateResult",
    "SPDKGlobalAnaEnabledArgs",
    "SPDKGlobalAnaEnabledResult",
    "SPDKGlobalRdmaEnabledArgs",
    "SPDKGlobalRdmaEnabledResult",
    "SPDKGlobalSessionsItem"
]


class SPDKGlobalEntry(BaseModel):
    id: int
    basenqn: str
    worker_cores: str
    """
    NQN to be used as the prefix on the creation of a subsystem, if a subnqn is not supplied to `SPDK.subsys.create`.

    Modifying this value will *not* change the subnqn of any existing subsystems.
    """
    kernel: bool
    """Select the NVMe-oF backend."""
    ana: bool
    """Asymmetric Namespace Access (ANA) enabled."""
    rdma: bool
    """
    RDMA is enabled for NVMe-oF.

    Enabling is limited to TrueNAS Enterprise-licensed systems and requires the system and network environment have \
    Remote Direct Memory Access (RDMA)-capable hardware.

    Once enabled one or more `ports` may be configured with RDMA selected as the transport. See `SPDK.port.create`.
    """
    xport_referral: bool
    """
    Controls whether cross-port referrals will be generated for ports on this TrueNAS.

    If ANA is active then referrals will always be generated between the peer ports on each TrueNAS controller node.
    """
    max_queue_depth: int
    max_io_qpairs: int
    in_caps: int
    num_shared_buffers: int

    huge_page_size: int


@single_argument_args('SPDK_update')
class SPDKGlobalUpdateArgs(SPDKGlobalEntry, metaclass=ForUpdateMetaclass):
    id: Excluded = excluded_field()
    basenqn: NQN
    worker_cores: str
    max_queue_depth: int
    max_io_qpairs: int
    in_caps: int
    num_shared_buffers: int
    huge_page_size: int

class SPDKGlobalUpdateResult(BaseModel):
    result: SPDKGlobalEntry


class SPDKGlobalAnaEnabledArgs(BaseModel):
    pass


class SPDKGlobalAnaEnabledResult(BaseModel):
    result: bool
    """ `True` if Asymmetric Namespace Access (ANA) is enabled. """


class SPDKGlobalRdmaEnabledArgs(BaseModel):
    pass


class SPDKGlobalRdmaEnabledResult(BaseModel):
    result: bool
    """ `True` if Remote Direct Memory Access (RDMA) is enabled for NVMe-oF. """


class SPDKGlobalSessionsItem(BaseModel):
    host_traddr: str
    """ Address of the connected host. For example an IP address."""
    hostnqn: str
    """ NQN of the connected host. """
    subsys_id: int
    """ `id` of the subsystem on this TrueNAS that the host is connected to. """
    port_id: int
    """ `id` of the port on this TrueNAS through which the host is connected. """
    ctrl: int
    """ NVMe controller number. """
