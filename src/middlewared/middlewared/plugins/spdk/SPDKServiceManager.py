import subprocess
import asyncio

import os
class SPDKServiceManager:

    def __init__(self):
        pass

    @staticmethod
    async def status() -> bool:
        # """nvmf_tgt çalışıyor mu diye kontrol eder"""
        # proc = subprocess.run(["pgrep", "-f", "nvmf_tgt"], capture_output=True)
        # if proc.returncode == 0:
        #     pids = proc.stdout.decode().strip().split()
        #     return True
        # return False
        path = "/var/tmp/spdk.sock"
        if not os.path.exists(path):
            return False

        try:
            reader, writer = await asyncio.open_unix_connection(path)
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    @staticmethod
    def _run_command(cmd):
        try:
            result = subprocess.run(
                cmd, shell=True, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            return result.stdout.decode().strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Command failed: {e.stderr.decode()}")

    @staticmethod
    async def stop(rpc_socket="/var/tmp/spdk.sock"):
        """
        SPDK nvmf_tgt'yi güvenli şekilde durdurur
        """
        if SPDKServiceManager.status():
            try:

                # Process kill
                result = subprocess.run(
                    ["pkill", "-f", f"nvmf_tgt.*{rpc_socket}"],
                    capture_output=True
                )

                # Eğer returncode 0 veya 15 (SIGTERM) ise hata sayma
                if result.returncode not in [0, 1, 143, -15]:  # 143 = SIGTERM bash exit code
                    raise RuntimeError(
                        f"pkill failed: returncode={result.returncode}, stderr={result.stderr.decode().strip()}"
                    )

            except subprocess.CalledProcessError as e:
                pass

            for _ in range(10):
                try:
                    reader, writer = await asyncio.open_unix_connection("/var/tmp/spdk.sock")
                    writer.close()
                    await writer.wait_closed()
                    await asyncio.sleep(0.2)
                    continue
                except Exception:
                    return True

        return True


    async def reload(self):
        await self.stop()
        await self.start()

    async def start(self, s=1024, m="0xFF"):
        rpc_path="/var/tmp/spdk.sock"

        """
        nvmf_tgt servisini başlatır.
        s: hugepage sayısı (2MB bazlı). +100MB otomatik eklenir.
        m: core mask
        """
        # +100MB = +50 hugepages
        extra_pages = (100 * 1024 * 1024) // (2 * 1024 * 1024)
        required = s + extra_pages

        # Hugepage ayarı
        self._run_command(f"echo {required} > /proc/sys/vm/nr_hugepages")

        # nvmf_tgt başlat (arka planda)
        # proc = subprocess.Popen(
        #     ["/opt/spdk/usr/bin/nvmf_tgt", "-s", str(s), "-m", str(m), "-r", "/var/tmp/spdk.sock", " ", "&"]
        # )
        await asyncio.create_subprocess_exec(
            "/opt/spdk/usr/bin/nvmf_tgt",
            "-s", str(s),
            "-m", str(m),
            "-r", rpc_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )

        # for _ in range(10):
        #     try:
        #         reader, writer = await asyncio.open_unix_connection(rpc_path)
        #         writer.close()
        #         await writer.wait_closed()
        #         return True
        #     except Exception:
        #         await asyncio.sleep(0.2)
        # return False

