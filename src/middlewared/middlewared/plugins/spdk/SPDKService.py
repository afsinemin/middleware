# import asyncio
# import middlewared.sqlalchemy as sa
# from middlewared.api.v25_10_0.spdk_global import SPDKGlobalEntry
# from middlewared.plugins.spdk_.utils import uuid_nqn
# from middlewared.service import SystemServiceService, private
#
# SPDK_SERVICE_NAME = 'spdk'
#
# class SPDKGlobalModel(sa.Model):
#     __tablename__ = 'services_spdk_global'
#
#     id = sa.Column(sa.Integer(), primary_key=True)
#     spdk_global_basenqn = sa.Column(sa.String(255), default=uuid_nqn)
#     spdk_global_kernel = sa.Column(sa.Boolean(), default=True)
#     spdk_global_ana = sa.Column(sa.Boolean(), default=False)
#     spdk_global_rdma = sa.Column(sa.Boolean(), default=False)
#     spdk_global_xport_referral = sa.Column(sa.Boolean(), default=True)
#
#
#
# class SPDKGlobalService(SystemServiceService):
#
#     class Config:
#         namespace = 'test.global'
#         service = SPDK_SERVICE_NAME
#         cli_private = True
#         entry = SPDKGlobalEntry
#         datastore = "services.spdk_global"
#         datastore_prefix = 'spdk_global_'
#         role_prefix = 'SHARING_NVME_TARGET'
#
#     @private
#     async def start(self):
#         """
#         SPDK daemon başlat.
#         """
#         self.logger.info("SPDK service starting...")
#         # Örnek: spdk_tgt çalıştırmak için asyncio subprocess
#         # Gerçek path ve parametreleri burada değiştir
#         self._spdk_proc = await asyncio.create_subprocess_exec(
#             '/usr/local/bin/spdk_tgt',
#             '-m', '0x1', '-s', '512',
#             stdout=asyncio.subprocess.PIPE,
#             stderr=asyncio.subprocess.PIPE,
#         )
#         await asyncio.sleep(1)  # Proc biraz zaman alsın
#         self.logger.info("SPDK daemon started.")
#
#     @private
#     async def stop(self):
#         """
#         SPDK daemon durdur.
#         """
#         if hasattr(self, '_spdk_proc') and self._spdk_proc.returncode is None:
#             self._spdk_proc.terminate()
#             try:
#                 await asyncio.wait_for(self._spdk_proc.wait(), timeout=5)
#             except asyncio.TimeoutError:
#                 self._spdk_proc.kill()
#                 await self._spdk_proc.wait()
#         self.logger.info("SPDK daemon stopped.")
#
#     @private
#     async def running(self):
#         """
#         Servisin çalışıp çalışmadığını kontrol et.
#         """
#         return hasattr(self, '_spdk_proc') and self._spdk_proc.returncode is None
#
#     @private
#     async def reload(self):
#         """
#         Servisi reload et.
#         """
#         if await self.running():
#             await self.stop()
#             await self.start()
#
#     @private
#     async def system_ready(self):
#         """
#         TrueNAS açıldığında servis start edilsin.
#         """
#         service = await self.middleware.call(
#             'service.query', [['service', '=', SPDK_SERVICE_NAME]], {'get': True}
#         )
#         if service['enable'] and service['state'] != 'RUNNING':
#             await self.start()