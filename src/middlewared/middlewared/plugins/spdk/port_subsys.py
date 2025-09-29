import json

import middlewared.sqlalchemy as sa
from middlewared.api import api_method
from middlewared.api.current import (SPDKPortSubsysCreateArgs,
                                     SPDKPortSubsysCreateResult,
                                     SPDKPortSubsysDeleteArgs,
                                     SPDKPortSubsysDeleteResult,
                                     SPDKPortSubsysEntry,
                                     SPDKPortSubsysUpdateArgs,
                                     SPDKPortSubsysUpdateResult)
from middlewared.service import CRUDService, ValidationErrors, private
from middlewared.service_exception import MatchNotFound
from .mixin import SPDKStandbyMixin
from .SPDKServiceManager import SPDKServiceManager
from .SPDKSocketManager import  SPDKSocketManager

spdkSocketManager = SPDKSocketManager()


class SPDKPortSubsysModel(sa.Model):
    __tablename__ = 'services_spdk_port_subsys'

    id = sa.Column(sa.Integer(), primary_key=True)
    spdk_port_subsys_port_id = sa.Column(sa.ForeignKey('services_spdk_port.id'), index=True)
    spdk_port_subsys_subsys_id = sa.Column(sa.ForeignKey('services_spdk_subsys.id'), index=True)


class SPDKPortSubsysService(CRUDService, SPDKStandbyMixin):

    class Config:
        namespace = 'spdk.port_subsys'
        datastore = 'services.spdk_port_subsys'
        datastore_prefix = 'spdk_port_subsys_'
        datastore_extend_fk = ['port', 'subsys']
        cli_private = True
        role_prefix = 'SHARING_NVME_TARGET'
        entry = SPDKPortSubsysEntry

    @api_method(
        SPDKPortSubsysCreateArgs,
        SPDKPortSubsysCreateResult,
        audit='Create NVMe target port to subsystem mapping',
        audit_extended=lambda data: f"Port ID: {data['port_id']} Subsys ID: {data['subsys_id']}"
    )
    async def do_create(self, data):

        # {
        #     "id": 3,
        #     "index": 3,
        #     "addr_trtype": "TCP",
        #     "addr_trsvcid": 4420,
        #     "addr_traddr": "10.1.1.201",
        #     "addr_adrfam": "IPV4",
        #     "inline_data_size": null,
        #     "max_queue_size": null,
        #     "pi_enable": null,
        #     "enabled": true
        # }

        """
        Create an association between a `port` and a subsystem (`subsys`).

        This will make the subsystem accessible on that port (subject to access
        control by either the  `allow_any_host` subsystem attribute, or `hosts`
        associated with the subsystem).
        """
        verrors = ValidationErrors()
        await self.__validate(verrors, data, 'spdk_port_subsys_create')
        verrors.check()

        async with self._handle_standby_service_state(await self.middleware.call('spdk.global.running')):
            data['id'] = await self.middleware.call(
                'datastore.insert', self._config.datastore, data,
                {'prefix': self._config.datastore_prefix})

        portInfo= await self.middleware.call('spdk.port.get_port_by_id',data['port_id'])
        if await SPDKServiceManager.status():
            spdkConfigs = await self.middleware.call('spdk.global.config')
            subsystem = await self.middleware.call('spdk.subsys.get_subsystem_by_id',data['subsys_id'])
            await spdkSocketManager.add_listener(subsystem["subnqn"], portInfo["addr_trtype"],portInfo["addr_traddr"],str(portInfo["addr_trsvcid"]),portInfo["addr_adrfam"],spdkConfigs["max_queue_depth"],spdkConfigs["in_caps"],spdkConfigs["max_io_qpairs"])


        await self.middleware.call('spdk.global.reload')
        return await self.get_instance(data['id'])

    @private
    def flatten(self, data: dict):
        if port_id := data.get('port', {}).get('id'):
            data['port_id'] = port_id
            del data['port']
        if subsys_id := data.get('subsys', {}).get('id'):
            data['subsys_id'] = subsys_id
            del data['subsys']
        return data

    @api_method(
        SPDKPortSubsysUpdateArgs,
        SPDKPortSubsysUpdateResult,
        audit='Update NVMe target port to subsystem mapping',
        audit_callback=True
    )
    async def do_update(self, audit_callback, id_, data):
        """
        Update `port`/`subsys` association of `id`.
        """
        old = await self.get_instance(id_)
        audit_callback(self.__audit_summary(old))
        old = self.flatten(old)
        new = old.copy()
        new.update(data)

        verrors = ValidationErrors()
        await self.__validate(verrors, new, 'spdk_port_subsys_update', old=old)
        verrors.check()

        async with self._handle_standby_service_state(await self.middleware.call('spdk.global.running')):
            await self.middleware.call(
                'datastore.update', self._config.datastore, id_, new,
                {'prefix': self._config.datastore_prefix}
            )

        #await self.middleware.call('spdk.global.reload')
        return await self.get_instance(id_)

    @api_method(
        SPDKPortSubsysDeleteArgs,
        SPDKPortSubsysDeleteResult,
        audit='Delete NVMe target port to subsystem mapping',
        audit_callback=True
    )
    async def do_delete(self, audit_callback, id_):
        """
        Delete `port`/`subsys` association of `id`.

        The specified subsystem will no longer be accessible on the `port`.
        """
        data = await self.get_instance(id_)
        audit_callback(self.__audit_summary(data))
        # with open("/data/portdelete.txt", "w") as f:
        #     json.dump(data, f, indent=4)
        async with self._handle_standby_service_state(await self.middleware.call('spdk.global.running')):
            rv = await self.middleware.call('datastore.delete', self._config.datastore, id_)

        await spdkSocketManager.remove_listener(data["subsys"]["subnqn"],data["port"]["addr_trtype"],data["port"]["addr_traddr"],str(data["port"]["addr_trsvcid"]),data["port"]["addr_adrfam"])

        #await self.middleware.call('spdk.global.reload')
        return rv

    @private
    async def delete_ids(self, to_remove):
        # This is called internally (from spdk.port.delete).  Does not require
        # a reload, because the caller will perform one
        return await self.middleware.call('datastore.delete', self._config.datastore, [['id', 'in', to_remove]])

    async def __validate(self, verrors, data, schema_name, old=None):
        port_id = data.get('port_id')
        subsys_id = data.get('subsys_id')

        # Ensure port_id exists
        try:
            await self.middleware.call('spdk.port.query', [['id', '=', port_id]], {'get': True})
        except MatchNotFound:
            verrors.add(f'{schema_name}.port_id', f"No port with ID {port_id}")

        # Ensure subsys_id exists
        try:
            await self.middleware.call('spdk.subsys.query', [['id', '=', subsys_id]], {'get': True})
        except MatchNotFound:
            verrors.add(f'{schema_name}.subsys_id', f"No subsystem with ID {subsys_id}")

        # Ensure we're not making a duplicate
        _filter = [('port_id', '=', port_id), ('subsys_id', '=', subsys_id)]
        if old:
            _filter.append(('id', '!=', data['id']))
        if await self.query(_filter, {'force_sql_filters': True}):
            verrors.add(f'{schema_name}.port_id',
                        f"This record already exists (Host ID: {port_id}/Subsystem ID: {subsys_id})")

    def __audit_summary(self, data):
        port = data['port']
        port_summary = (f'{port["addr_trtype"]}:{port["addr_traddr"]}:{port["addr_trsvcid"]}')
        return f'{port_summary}/{data["subsys"]["name"]}'
