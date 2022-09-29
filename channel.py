import random
import socket
import select
import time
import requests

MAX_BUF_SIZE = 1024


class Channel:
    def __init__(self, sender_port: int = 10001, receiver_port: int = 10002):
        self.sender_port = sender_port
        self.receiver_port = receiver_port
        self.api = "http://127.0.0.1:8080/action/put"
        self.get_cmd_api = "http://127.0.0.1:8080/cmd/get"
        self.set_cmd_api = "http://127.0.0.1:8080/cmd/set"

        self.sender_serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sender_serv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.receiver_serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.receiver_serv.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def __damage(self, data):
        # 随机破坏帧
        try:
            damage = requests.get(
                f"{self.get_cmd_api}?field=damage", timeout=0.3).content
            if damage == b"true":
                # bits flip
                requests.get(
                    f"{self.set_cmd_api}?field=damage&value=false", timeout=0.3)
                for _round in range(3):
                    damage_pos = random.randint(0, len(data)-1)
                    flip_mask = "0b" + \
                        "".join(["0" if random.randint(0, 1) ==
                                 0 else "1" for _ in range(8)])
                    flip_mask = int(flip_mask, 2)
                    data = data[0:damage_pos] + \
                        bytes([data[damage_pos] ^ flip_mask]) + \
                        data[damage_pos+1:]
                print(f"[Channel] Bits flip!")
                return data
        except Exception as e:
            print(e)
        return data

    def __send_with_timeout(self, target, data):
        # 手动超时
        try:
            timeout = requests.get(
                f"{self.get_cmd_api}?field=timeout", timeout=0.3).content
            if timeout == b"true":
                # timeout
                requests.get(
                    f"{self.set_cmd_api}?field=timeout&value=false", timeout=0.3)
                print(f"[Channel] Doing timeout...")
                time.sleep(5)
        except Exception as e:
            print(e)
        if target == "receiver":
            self.receiver.send(data)
        elif target == "sender":
            self.sender.send(data)

    def __daemon(self):
        self.sender_serv.bind(("127.0.0.1", self.sender_port))
        self.receiver_serv.bind(("127.0.0.1", self.receiver_port))
        self.sender_serv.listen(1)
        self.receiver_serv.listen(1)
        # 等待两端接入信道
        self.sender, _ = self.sender_serv.accept()
        print("[Channel] Sender online!")
        self.receiver, _ = self.receiver_serv.accept()
        print("[Channel] Receiver online!")

        rlist = [self.sender, self.receiver]
        wlist = [self.sender, self.receiver]
        xlist = [self.sender, self.receiver]
        while True:
            s_rlist, s_wlist, _ = select.select(rlist, wlist, xlist)

            # sender forward to receiver
            if self.sender in s_rlist and self.receiver in s_wlist:
                buf = self.sender.recv(MAX_BUF_SIZE)
                if len(buf) > 0:
                    buf = self.__damage(buf)
                    print("[Channel] Forward data to receiver:", buf)
                    self.__send_with_timeout("receiver", buf)
            # receiver forward to sender
            if self.receiver in s_rlist and self.sender in s_wlist:
                buf = self.receiver.recv(MAX_BUF_SIZE)
                if len(buf) > 0:
                    buf = self.__damage(buf)
                    print("[Channel] Forward data to sender:", buf)
                    self.__send_with_timeout("sender", buf)

    def start(self):
        self.__daemon()


def main():
    channel = Channel()
    channel.start()


if __name__ == "__main__":
    main()
