# from middlewared.service import Service
# import subprocess
#
# class SPDKService(Service):
#     class Config:
#         namespace = "spdk.info"
#         cli_namespace = "storage.spdk"
#         private=True
#
#     def _run_command(self, cmd):
#         try:
#             result = subprocess.run(
#                 cmd, shell=True, check=True,
#                 stdout=subprocess.PIPE, stderr=subprocess.PIPE
#             )
#             return result.stdout.decode().strip()
#         except subprocess.CalledProcessError as e:
#             raise RuntimeError(f"Command failed: {e.stderr.decode()}")
#
#     async def start(self, s= 1024, m=  "0x1"):
#         """
#         nvmf_tgt servisini başlatır.
#         s: hugepage sayısı (2MB bazlı). +100MB otomatik eklenir.
#         m: core mask
#         """
#         # +100MB = +50 hugepages
#         extra_pages = (100 * 1024 * 1024) // (2 * 1024 * 1024)
#         required = s + extra_pages
#
#         # Hugepage ayarı
#         self._run_command(f"echo {required} > /proc/sys/vm/nr_hugepages")
#
#         # nvmf_tgt başlat (arka planda)
#         proc = subprocess.Popen(
#             ["/opt/spdk/usr/bin/nvmf_tgt", "-s", str(s), "-m", str(m),"-r","/var/tmp/spdk.sock"]
#         )
#         return {"pid": proc.pid, "hugepages": required}
#
#     async def reload(self):
#         """nvmf_tgt konfigürasyonunu reload eder (signal tabanlı)"""
#         return self._run_command("pkill -HUP -f nvmf_tgt")
#
#     async def stop(self):
#         """nvmf_tgt servisinin çalışmasını durdurur"""
#         result = subprocess.run(
#             "pkill -f nvmf_tgt",
#             shell=True,
#             check=False,
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE
#         )
#
#         # pkill returncode 0=process öldürüldü, 1=process yok → ikisi de OK
#         if result.returncode in (0, 1):
#             return {"stopped": True, "msg": "nvmf_tgt stopped (or not running)"}
#
#         # sadece başka returncode varsa hata
#         raise RuntimeError(f"pkill failed: returncode={result.returncode}, stderr={result.stderr.decode().strip()}")
#
#     async def status(self) -> dict:
#         """nvmf_tgt çalışıyor mu diye kontrol eder"""
#         proc = subprocess.run(["pgrep", "-f", "nvmf_tgt"], capture_output=True)
#         if proc.returncode == 0:
#             pids = proc.stdout.decode().strip().split()
#             return {"running": True, "pids": pids}
#         return {"running": False}
