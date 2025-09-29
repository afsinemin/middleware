import asyncio
import json

class SPDKSocketManager:
    RPC_SOCKET = "/var/tmp/spdk.sock"
    async def rpc_request(self,method, params=None,timeout=3):

        if params is None:
            msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method
                 }
        else:
            msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params
                  }

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_unix_connection(self.RPC_SOCKET),
                timeout=timeout
            )
            writer.write(json.dumps(msg).encode() + b"\n")
            await writer.drain()

            resp = await reader.readline()
            writer.close()
            await writer.wait_closed()
            return json.loads(resp)

        except asyncio.TimeoutError:

            return "Timeout"
        except ConnectionRefusedError:
            print("Socket hazır değil, bağlantı reddedildi")
            return "Socket hazır değil"


        # data = json.dumps(msg).encode("ascii")
        #
        # with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        #     s.connect(self.RPC_SOCKET)
        #     s.sendall(data)
        #     s.shutdown(socket.SHUT_WR)
        #     response = b""
        #     while True:
        #         chunk = s.recv(4096)
        #         if not chunk:
        #             break
        #         response += chunk
        #
        # js = json.loads(response.decode("ascii"))
        # return js


    async def list_subsystems(self):
        """Mevcut subsystemleri listeler"""
        resp = await self.rpc_request("nvmf_get_subsystems")
        subsystems = resp.get("result", [])
        result = []
        for ss in subsystems:
            result.append({
                "nqn": ss.get("nqn", ""),
                "serial_number": ss.get("serial_number", ""),
                "model_number": ss.get("model_number", ""),
                "namespaces": ss.get("namespaces", []),
                "listen_addresses": ss.get("listen_addresses", [],),
            })
        return result

    async def show_all_subsystems(self):
        """Mevcut subsystemleri listeler"""
        resp = await self.rpc_request("nvmf_get_subsystems")
        subsystems = resp.get("result", [])

        return subsystems
    async def create_subsystem(self, nqn, allow_any_host=True, serial_number="12345678954545", model_number="SPDK0000",ana_reporting= False
                         ):
        """Yeni NVMf subsystem oluşturur"""
        params = {
            "nqn": nqn,
            "allow_any_host": allow_any_host,
            "serial_number": serial_number,
            "model_number": model_number,
            "ana_reporting": ana_reporting
        }
        resp = await self.rpc_request("nvmf_create_subsystem", params)

        # Subsystem gerçekten oluştu mu kontrol et
        subs = await self.list_subsystems()
        if len(subs) == 0:
            return False

        for ss in subs:
            if ss["nqn"] == nqn:
                return True
        return False
    async def set_subsystem_allow_any_host(self, nqn:str, allow_any_host= False):
        """
        Verilen NQN'e sahip subsystem'i siler.
        """
        params = {"nqn": nqn, "allow_any_host": allow_any_host}
        resp = await self.rpc_request("nvmf_subsystem_allow_any_host", params)

        if "error" in resp:
            return False
        subs = await self.list_subsystems()
        still_exists = any(ss["nqn"] == nqn for ss in subs)
        if still_exists:
            return False

        return True

    async def subsystem_remove_host(self, nqn: str, host:str):

       try:
           params = {"nqn": nqn, "host": host}
           resp = await self.rpc_request("nvmf_subsystem_remove_host", params)
           print(resp)
           if "error" in resp:
               return False

           return True

       except:
           return False



    async def delete_subsystem(self, nqn):
        """
        Verilen NQN'e sahip subsystem'i siler.
        """
        params = {"nqn": nqn}
        resp = await self.rpc_request("nvmf_delete_subsystem", params)

        if "error" in resp:
            return False
        subs = await self.list_subsystems()
        still_exists = any(ss["nqn"] == nqn for ss in subs)
        if still_exists:
            return False

        return True
    async def delete_namespace(self, nqn:str,nsid:int):
        """
        Verilen NQN'e sahip subsystem'i siler.
        """
        params = {"nqn": nqn, "nsid": nsid}
        resp = await self.rpc_request("nvmf_subsystem_remove_ns", params)

        if "error" in resp:
            return False

        return True


    async def add_namespace(self, zvol_path:str, nqn:str, nsid:str,device_uuid:str,device_nguid:str):

        bdev_name = "_".join(zvol_path.strip("/").split("/")[-2:])  # NVME_nvmeof gibi
        await self.create_bdev(zvol_path=zvol_path,bdev_name=bdev_name)
        #NAMESPACE = uuid.NAMESPACE_DNS
        #guid = uuid.uuid5(NAMESPACE, zvol_path)
        #nguid = guid.hex
        device_nguid=device_nguid.replace("-","")
        resp2 = await self.rpc_request("nvmf_subsystem_add_ns", {
            "nqn": nqn,
            "namespace": {
                "bdev_name": bdev_name,
                "nsid": nsid,
                "uuid": device_uuid,
                "nguid": device_nguid,
                "eui64": device_nguid[:16]
            }
        })

        if "error" in resp2:
            return False

        return True


    async def list_bdevs(self):
        resp = await self.rpc_request("bdev_get_bdevs")
        return resp.get("result", [])

    async def create_bdev(self, zvol_path, bdev_name=None):
        if bdev_name is None:
            bdev_name = "_".join(zvol_path.strip("/").split("/")[-2:])

        resp = await self.rpc_request("bdev_uring_create", {
            "name": bdev_name,
            "filename": zvol_path,
            "block_size": 512
        })

        if "error" in resp:
            return False
        return True
    async def check_transport(self,trtype="TCP"):
        try:
            transports = await self.rpc_request("nvmf_get_transports")["result"]
            return any(t["trtype"] == trtype for t in transports)
        except:
            return False
    async def create_transport(self, trtype="TCP", max_queue_depth=8192, in_caps=131072, max_io_qpairs=8192):
        try:
            """
                    SPDK NVMe-oF transport oluşturur.
                    - trtype: TCP veya RDMA
                    - max_queue_depth: -u parametresi
                    - in_caps: -i parametresi
                    - max_io_qpairs: -c parametresi
                    """
            params = {
                "trtype": trtype,
                "max_queue_depth": max_queue_depth,
                "in_caps": in_caps,
                "max_io_qpairs": max_io_qpairs
            }
            return await self.rpc_request("nvmf_create_transport", params)
        except:
            return False
    async def add_listener(self, nqn, trtype="TCP", traddr="10.1.1.201", trsvcid="4420", adrfam="IPv4", max_queue_depth=8192, in_caps=131072, max_io_qpairs=8192):
        """Bir subsystem’e listener ekler"""

        if not await self.check_transport(trtype):
            await self.create_transport(trtype, max_queue_depth, in_caps, max_io_qpairs)

        await asyncio.sleep(1)

        listener = {
            "trtype": trtype,
            "adrfam": adrfam,
            "traddr": traddr,
            "trsvcid": trsvcid
        }
        params={
            "nqn": nqn,
            "listen_address": listener
        }

        resp = await self.rpc_request("nvmf_subsystem_add_listener", params)

        if "error" in resp:
            return False

        return True

    async def remove_listener(self, nqn, trtype="TCP", traddr="10.1.1.201", trsvcid="4420", adrfam="ipv4"):
        """Bir subsystem’den listener siler"""
        listener = {
            "trtype": trtype,
            "adrfam": adrfam,
            "traddr": traddr,
            "trsvcid": trsvcid
        }

        resp = await self.rpc_request("nvmf_subsystem_remove_listener", {
            "nqn": nqn,
            "listen_address": listener
        })

        if "error" in resp:
            return False
        return True

    async def list_listeners(self, nqn):
        """Bir subsystem’de mevcut listener’ları listeler"""
        resp = await self.rpc_request("nvmf_subsystem_get_subsystems")
        subsystems = resp.get("result", [])

        for ss in subsystems:
            if ss["nqn"] == nqn:
                return ss.get("listen_addresses", [])
        return []

    async def wait_for_socket(self, retries=10, delay=0.5):
        for i in range(retries):
            try:
                reader, writer = await asyncio.open_unix_connection(self.RPC_SOCKET)
                writer.close()
                await writer.wait_closed()
                return True
            except (FileNotFoundError, ConnectionRefusedError) as e:
                await asyncio.sleep(delay)
        return False

    async def list_allowed_hosts(self):
        subsystems = await self.rpc_request("nvmf_get_subsystems")
        if not subsystems or "result" not in subsystems:
            print("Subsystem listesi alınamadı")
            return


        for s in subsystems["result"]:
            print(s['hosts'])

    async def remove_all_hosts(self,subsystem_nqn):
        # 1️⃣ Mevcut subsystemleri al
        subsystems = await self.rpc_request("nvmf_get_subsystems")
        if not subsystems or "result" not in subsystems:
            print("Subsystem listesi alınamadı")
            return False

        # 2️⃣ Subsystem bul
        subsystem = None
        for s in subsystems["result"]:
            if s["nqn"] == subsystem_nqn:
                subsystem = s
                break
        if not subsystem:
            print(f"Subsystem bulunamadı: {subsystem_nqn}")
            return False

        # 3️⃣ Tüm hostları sil
        hosts = subsystem.get("hosts", [])
        if not hosts:
            print("Subsystemde silinecek host yok.")
            return True

        for host in hosts:
            host_nqn = host["nqn"]
            params = {"nqn": subsystem_nqn, "host": host_nqn}
            response = await self.rpc_request("nvmf_subsystem_remove_host", params)
            if response and response.get("result") is True:
                print("Host silindi:", host_nqn)
            else:
                print("Host silinemedi:", host_nqn, response)
        return True

    async def subsystem_add_host(self,subsystem_nqn, host_nqn,dhchap_key:str,dhchap_ctrlr_key:str):
        # 1️⃣ Mevcut hostları al
        subsystems = await self.rpc_request("nvmf_get_subsystems")
        if not subsystems or "result" not in subsystems:
            print("Subsystem listesi alınamadı")
            return False

        # 2️⃣ Subsystem bul
        subsystem = None
        for s in subsystems["result"]:
            if s["nqn"] == subsystem_nqn:
                subsystem = s
                break
        if not subsystem:
            print(f"Subsystem bulunamadı: {subsystem_nqn}")
            return False

        # 3️⃣ Host zaten ekli mi kontrol et
        allowed_hosts = [h["nqn"] for h in subsystem.get("hosts", [])]
        print("allowed hosts: ", subsystem)
        if host_nqn in allowed_hosts:
            print("Host zaten eklenmiş:", host_nqn)
            return True

        # 4️⃣ Host ekle
        params = {"nqn": subsystem_nqn, "host": host_nqn}
        if dhchap_key is not None:
            params.update({"dhchap_key":dhchap_key})
        if dhchap_ctrlr_key is not None:
            params.update({"dhchap_ctrlr_key":dhchap_ctrlr_key})

        response = await self.rpc_request("nvmf_subsystem_add_host", params)
        if response and response.get("result") is True:
            print("Host başarıyla eklendi:", host_nqn)
            return True
        else:
            print("Host eklenemedi:", response)
            return False
