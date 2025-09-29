from middlewared.common.attachment import LockableFSAttachmentDelegate
from middlewared.plugins.spdk.namespace import SPDKNamespaceService


class SPDKNamespaceAttachmentDelegate(LockableFSAttachmentDelegate):
    name = 'spdk'
    title = 'NVMe-oF Namespace'
    service = 'spdk'
    service_class = SPDKNamespaceService
    resource_name = 'device_path'

    async def restart_reload_services(self, attachments):
        await self.middleware.call('spdk.global.reload')

    async def toggle(self, attachments, enabled):
        for attachment in attachments:
            action = 'start' if enabled else 'stop'
            try:
                await self.middleware.call(f'spdk.namespace.{action}', attachment['id'])
            except Exception as e:
                self.middleware.logger.warning('Unable to %s %r: %s', action, attachment['id'], e)

    async def stop(self, attachments):
        await self.toggle(attachments, False)

    async def start(self, attachments):
        await self.toggle(attachments, True)


async def setup(middleware):
    await middleware.call('pool.dataset.register_attachment_delegate', SPDKNamespaceAttachmentDelegate(middleware))
