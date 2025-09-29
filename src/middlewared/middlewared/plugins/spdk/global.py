import asyncio
import os
import pathlib
import json
from middlewared.service import  CallError
import middlewared.sqlalchemy as sa
from .SPDKServiceManager import SPDKServiceManager
from .SPDKSocketManager import SPDKSocketManager
from middlewared.api import api_method
from middlewared.api.current import (SPDKGlobalAnaEnabledArgs,
                                     SPDKGlobalAnaEnabledResult,
                                     SPDKGlobalEntry,
                                     SPDKGlobalRdmaEnabledArgs,
                                     SPDKGlobalRdmaEnabledResult,
                                     SPDKGlobalUpdateArgs,
                                     SPDKGlobalUpdateResult,
                                     SPDKGlobalSessionsItem)
from middlewared.plugins.rdma.constants import RDMAprotocols
from middlewared.service import SystemServiceService, ValidationErrors, filterable_api_method, private
from middlewared.utils import filter_list
from .constants import SPDK_SERVICE_NAME
from .mixin import SPDKStandbyMixin
from .utils import uuid_nqn
SPDK_DEBUG_DIR = '/sys/kernel/debug/nvmet'
spdkServiceManager = SPDKServiceManager()
spdkSocketManager = SPDKSocketManager()

class SPDKGlobalModel(sa.Model):
    __tablename__ = 'services_spdk_global'

    id = sa.Column(sa.Integer(), primary_key=True)
    spdk_global_basenqn = sa.Column(sa.String(255), default=uuid_nqn)
    spdk_global_worker_cores = sa.Column(sa.String(255), default="0xFF")
    spdk_global_kernel = sa.Column(sa.Boolean(), default=True)
    spdk_global_ana = sa.Column(sa.Boolean(), default=False)
    spdk_global_rdma = sa.Column(sa.Boolean(), default=False)
    spdk_global_xport_referral = sa.Column(sa.Boolean(), default=True)
    spdk_global_max_queue_depth = sa.Column(sa.Integer(), default=8192)
    spdk_global_max_io_qpairs = sa.Column(sa.Integer(), default=8192)
    spdk_global_in_caps = sa.Column(sa.Integer(), default=131072)
    spdk_global_num_shared_buffers = sa.Column(sa.Integer(), default=8192)
    spdk_global_huge_page_size = sa.Column(sa.Integer(), default=1024)


class SPDKGlobalService(SystemServiceService, SPDKStandbyMixin):

    class Config:
        namespace = 'spdk.global'
        datastore = 'services.spdk_global'
        datastore_prefix = 'spdk_global_'
        service = SPDK_SERVICE_NAME
        cli_private = True
        role_prefix = 'SHARING_NVME_TARGET'
        entry = SPDKGlobalEntry

    @api_method(
        SPDKGlobalUpdateArgs,
        SPDKGlobalUpdateResult,
        audit='Update NVMe target global'
    )
    async def do_update(self, data):
        """
        Update NVMe target global config.
        """
        old = await self.config()

        new = old.copy()
        new.update(data)

        verrors = ValidationErrors()
        await self.__validate(verrors, new, 'spdk_global_update', old=old)
        verrors.check()

        #async with self._handle_standby_service_state(old['ana'] != new['ana'] and await self.running()):
        await self._update_service(old, new)

        return await self.config()


    async def __validate(self, verrors, data, schema_name, old=None):


        if data['rdma'] and old['rdma'] != data['rdma']:
            available_rdma_protocols = await self.middleware.call('rdma.capable_protocols')
            if RDMAprotocols.NVMET.value not in available_rdma_protocols:
                verrors.add(
                    f'{schema_name}.rdma',
                    'This platform cannot support NVMe-oF(RDMA) or is missing a RDMA capable NIC.'
                )



    @api_method(
        SPDKGlobalAnaEnabledArgs,
        SPDKGlobalAnaEnabledResult,
        roles=['SHARING_NVME_TARGET_READ']
    )
    async def ana_enabled(self):

        return (await self.middleware.call('spdk.global.config'))['ana']

    @private
    async def ana_active(self):

        if (await self.middleware.call('spdk.global.config'))['ana']:
            return True

        if (await self.middleware.call('spdk.port.usage'))['ana_port_ids']:
            return True

        return False

    @api_method(
        SPDKGlobalRdmaEnabledArgs,
        SPDKGlobalRdmaEnabledResult,
        roles=['SHARING_NVME_TARGET_READ']
    )
    async def rdma_enabled(self):
        """
        Returns whether RDMA is enabled or not.
        """
        # if not await self.middleware.call('system.is_enterprise'):
        #     return False

        return (await self.middleware.call('spdk.global.config'))['rdma']

    @filterable_api_method(item=SPDKGlobalSessionsItem, roles=['SHARING_NVME_TARGET_READ'])
    async def sessions(self, filters, options):
        sessions = []
        subsys_id = None
        for filter in filters:
            if len(filter) == 3 and filter[0] == 'subsys_id' and filter[1] == '=':
                subsys_id = filter[2]
                break
        sessions = await self.middleware.call('spdk.global.local_sessions', subsys_id)
        if await self.ana_enabled():
            sessions.extend(await self.middleware.call('failover.call_remote',
                                                       'spdk.global.local_sessions',
                                                       [subsys_id]))

        return filter_list(sessions, filters, options)

    def __parse_session_dir(self, path: pathlib.Path, port_index_to_id: dict):
        """
        Parse the session directory, e.g.
        /sys/kernel/debug/spdk/<SUBSYS_NQN>/ctrl<NUMBER>
        """
        # For example
        # /sys/kernel/debug/spdk/nqn.2011-06.com.truenas:uuid:cef24057-8050-4fc7-ab87-773e19b32b0e:foo1/ctrl2
        # /sys/kernel/debug/spdk/nqn.2011-06.com.truenas:uuid:cef24057-8050-4fc7-ab87-773e19b32b0e:foo1/ctrl2/host_traddr
        # /sys/kernel/debug/spdk/nqn.2011-06.com.truenas:uuid:cef24057-8050-4fc7-ab87-773e19b32b0e:foo1/ctrl2/state
        # /sys/kernel/debug/spdk/nqn.2011-06.com.truenas:uuid:cef24057-8050-4fc7-ab87-773e19b32b0e:foo1/ctrl2/kato
        # /sys/kernel/debug/spdk/nqn.2011-06.com.truenas:uuid:cef24057-8050-4fc7-ab87-773e19b32b0e:foo1/ctrl2/hostnqn
        # /sys/kernel/debug/spdk/nqn.2011-06.com.truenas:uuid:cef24057-8050-4fc7-ab87-773e19b32b0e:foo1/ctrl2/port
        if path.name.startswith('ctrl'):
            result = {}
            result['ctrl'] = int(path.name[4:])
            result['hostnqn'] = pathlib.Path(path, 'hostnqn').read_text().strip()
            result['host_traddr'] = pathlib.Path(path, 'host_traddr').read_text().strip()
            port_index = int(pathlib.Path(path, 'port').read_text().strip())
            result['port_id'] = port_index_to_id[port_index]
            return result

    @private
    def local_sessions(self, subsys_id=None):
        sessions = []
        global_info = self.middleware.call_sync('spdk.global.config')
        subsystems = self.middleware.call_sync('spdk.subsys.query')

        if global_info['kernel']:
            spdk_debug_path = pathlib.Path(SPDK_DEBUG_DIR)
            if not spdk_debug_path.exists():
                return sessions

        port_index_to_id = {port['index']: port['id'] for port in self.middleware.call_sync('spdk.port.query')}

        if subsys_id is None:
            basenqn = global_info['basenqn']
            subsys_name_to_subsys_id = {f'{basenqn}:{subsys["name"]}': subsys['id'] for subsys in subsystems}
            for subsys in spdk_debug_path.iterdir():
                if subsys_id := subsys_name_to_subsys_id.get(subsys.name):
                    for ctrl in subsys.iterdir():
                        if session := self.__parse_session_dir(ctrl, port_index_to_id):
                            session['subsys_id'] = subsys_id
                            sessions.append(session)
        else:
            for subsys in subsystems:
                if subsys['id'] == subsys_id:
                    subnqn = f'{global_info["basenqn"]}:{subsys["name"]}'
                    path = spdk_debug_path / subnqn
                    if path.is_dir():
                        for ctrl in path.iterdir():
                            if session := self.__parse_session_dir(ctrl, port_index_to_id):
                                session['subsys_id'] = subsys_id
                                sessions.append(session)

        return sessions






    @private
    async def running(self):
        # if (await self.config())['kernel']:
        #     return await self.middleware.run_in_thread(spdk_kernel_module_loaded)
        # else:
        #     return False
        return await spdkServiceManager.status()

    @private
    async def reload(self):
        if await self.running():
            await self._service_change('spdk', 'reload')



    @private
    async def start(self):
        nvmet_state = await self.middleware.call('service.query', [['service', '=', 'nvmet']])
        if nvmet_state and nvmet_state[0]['state'] == 'RUNNING':
            raise CallError('Cannot start SPDK: nvmet service is running.')

        # await self.middleware.call("etc.generate", "spdk")
        # await asyncio.sleep(1)
        # config_path = "/data/spdk.json"
        # for _ in range(10):  # en fazla 1 saniye bekle
        #     if os.path.exists(config_path):
        #         break
        #     await asyncio.sleep(0.1)
        # else:
        #     raise RuntimeError("spdk.json generation timeout")
        # # Dosyayı aç ve yükle
        # with open(config_path, "r") as f:
        #     subsystems = json.load(f)


        subsystems = []

        # Önce subsystem dictleri
        for subsys in await self.middleware.call('spdk.subsys.query'):
            subsys_id = subsys['id']
            subsys_dict = {
                "subsys": subsys,
                "namespaces": [],
                "ports": [],
                "hosts": []
            }

            # Namespace ekle
            for ns in await self.middleware.call('spdk.namespace.query'):
                if ns['subsys']['id'] == subsys_id:
                    subsys_dict["namespaces"].append(ns)

            # Port ekle
            for ps in await self.middleware.call('spdk.port_subsys.query'):
                if ps['subsys']['id'] == subsys_id:
                    subsys_dict["ports"].append(ps['port'])

            # Host ekle
            for hs in await self.middleware.call('spdk.host_subsys.query'):
                if hs['subsys']['id'] == subsys_id:
                    subsys_dict["hosts"].append(hs['host'])

            # Listeye ekle
            subsystems.append(subsys_dict)


        with open("/data/dbtest.json", "w") as outfile:
            json.dump(subsystems,outfile,indent=4)
        spdkConfigs = await self.middleware.call('spdk.global.config')


        await spdkServiceManager.start(spdkConfigs["huge_page_size"], spdkConfigs["worker_cores"])
        for _ in range(10):
            if await spdkSocketManager.wait_for_socket(10, 0.5):
                break
            else:
                continue
        for subsystem in subsystems:

            subsys=subsystem["subsys"]
            subnqn=subsys["subnqn"]

            await spdkSocketManager.create_subsystem(subnqn, subsys["allow_any_host"], subsys["serial"],ana_reporting= spdkConfigs["ana"])
            for namespace in subsystem["namespaces"]:
                await spdkSocketManager.add_namespace("/dev/" + namespace["device_path"], subnqn, namespace["nsid"],namespace["device_uuid"], namespace["device_nguid"])



            for portInfo in subsystem["ports"]:

                await spdkSocketManager.add_listener(subnqn, portInfo["addr_trtype"],portInfo["addr_traddr"],str(portInfo["addr_trsvcid"]),"IPv4",spdkConfigs["max_queue_depth"],spdkConfigs["in_caps"],spdkConfigs["max_io_qpairs"])
            if subsys["allow_any_host"]==False:
                for host in subsystem["hosts"]:
                    await spdkSocketManager.subsystem_add_host(subnqn,
                                                               host["hostnqn"],
                                                               host["dhchap_key"],
                                                               host["dhchap_ctrl_key"])



    @private
    async def stop(self):
        await spdkServiceManager.stop()
        await asyncio.sleep(2)

    @private
    async def system_ready(self):
        # Because the kernel spdk service does not have a systemd unit
        # we need to ensure it gets started (if necessary).
        # service = await self.middleware.call('service.query',
        #                                      [['service', '=', SPDK_SERVICE_NAME]],
        #                                      {'get': True})
        # if not service['enable'] or service['state'] == 'RUNNING':
        #     return
        #
        # if await self.middleware.call('failover.licensed'):
        #     return

            # await self.middleware.call('spdk.global.load_kernel_modules')
        #await self.middleware.call("etc.generate", "spdk")

        await self.middleware.call('spdk.global.start')


async def __event_system_ready(middleware, event_type, args):
    await middleware.call('spdk.global.system_ready')


async def pool_post_import(middleware, pool):
    if pool is None:
        return

    if await middleware.call('spdk.global.running'):
        path = pool.get('path', '')
        name = pool.get('name', '')
        if await middleware.call('spdk.namespace.query', [
            ('OR', [
                ('device_path', '^', f'zvol/{name}/'),
                ('device_path', '^', f'{path}/'),])]):
            await (await middleware.call('service.control', 'RELOAD', SPDK_SERVICE_NAME)).wait(raise_error=True)


async def setup(middleware):
    middleware.register_hook("pool.post_import", pool_post_import, sync=True)
    if await middleware.call('system.ready'):
        await middleware.call('iscsi.auth.load_upgrade_alerts')
    else:
        middleware.event_subscribe('system.ready', __event_system_ready)
