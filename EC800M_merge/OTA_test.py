import utime
import usocket as socket
import umqtt
import ujson as json
from usr import uuid
import request
import _thread

class OTA(object):
    def __init__(self,mac):
        self.uuid = str(uuid.uuid4())
        self.head = {
            'Accept-Language': 'zh-CN',
            'Content-Type': 'application/json',
            'User-Agent': 'kevin-box-2/1.0.1',
            'Device-Id': mac,
            'Client-Id': self.uuid
        }
        self.ota_data = {
            "application": {
                "version": "1.0.1",
                "elf_sha256": "c8a8ecb6d6fbcda682494d9675cd1ead240ecf38bdde75282a42365a0e396033"
            },
            "board": {
                "type": "kevin-box",
                "name": "kevin-box-2",
                "carrier": "CHINA UNICOM",
                "csq": "22",
                "imei": "****",
                "iccid": "89860125801125426850"
            }
        }
        self.url = "http://139.196.33.144:8003/xiaozhi/ota/"
        # 云服务器 OTA 会返回实际 websocket 地址与 token
        self.response = None
        self.UDP_IP = None
        self.UDP_PORT = None
        self.run()

    def run(self):
        # 通过OTA得到mqtt的连接参数
        resp = request.post(self.url, data=json.dumps(self.ota_data), headers=self.head)
        self.response = resp.json()
        # print(self.response)
        return self.response




