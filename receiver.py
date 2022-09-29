import socket
import string
import random
import struct
import zlib
import time
import sys
import copy
import requests, json
from threading import Timer, Event, Thread, Lock

ESC = 0x1b & 0xff  # ESC char
FLAG = 0x7e & 0xff  # 0b01111110
MAX_FRAME_DATA = 32
MIN_FRAME_SIZE = 6
FRAME_TYP_DATA = 0x0
FRAME_TYP_ACK = 0x1
FRAME_TYP_NAK = 0x2
MAX_SEQ_BITS = 8

EVENT_HANGING = 0
EVENT_ARRIVAL_NOTIFICATION = 1

MAX_TIMEOUT = 3.0

class Receiver:
    def __init__(self, seq_bits:int=4, receiver_interface: tuple = ("127.0.0.1", 10002)):
        self.window_size = 2**(seq_bits-1)
        self.seq_range = 2**seq_bits

        self.frame_queue = [b"" for _ in range(self.seq_range)]
        self.slots = [False for _ in range(self.seq_range)]
        self.Rn = 0
        self.Sw = self.window_size
        self.is_online = 0
        self.receiver_interface = receiver_interface
        self.put_api = "http://127.0.0.1:8080/action/put"
        self.get_cmd_api = "http://127.0.0.1:8080/cmd/get"
        self.set_cmd_api = "http://127.0.0.1:8080/cmd/set"

        self.nak_send = False
        self.ack_needed = False

        self.recv_frame_buf = b""

        self.new_event = Event()
        self.event_lock = Lock()
        self.event = EVENT_HANGING

    def __get_frame_type(self, frame:bytes)->int:
        return frame[0]

    def __get_frame_seq(self, frame:bytes)->int:
        return frame[1]

    def __extract_frame_payload(self, frame:bytes)->bytes:
        return frame[2:-4]

    def __check_frame(self, frame:bytes):
        # 检查长度
        if len(frame) < MIN_FRAME_SIZE or len(frame) > MIN_FRAME_SIZE+MAX_FRAME_DATA:
            self.__report_bad_frame_action(frame.hex(), "Bad Length")
            return False
        # 检查CRC32
        if zlib.crc32(frame[:-4]) & 0xffffffff != struct.unpack("!I", frame[-4:])[0]:
            self.__report_bad_frame_action(frame.hex(), "CRC32 Error!")
            return False
        # 检查类型
        if self.__get_frame_type(frame) != FRAME_TYP_DATA:
            self.__report_bad_frame_action(frame.hex(), "Bad Type")
            return False
        return True

    def __seq_in_window(self, seq):
        for i in range(self.Sw):
            if (self.Rn+i) % self.seq_range == seq:
                return True
        return False

    def __marked_seq(self, seq):
        for i in range(self.Sw):
            if (self.Rn+i) % self.seq_range == seq:
                return self.slots[seq]
        return False

    def __media_send_frame(self, frame: bytes):
        # 插入转义字符
        def pre_process(data: bytes):
            new_data = b""
            for byte in data:
                if byte == ESC or byte == FLAG:
                    new_data += struct.pack("!BB", ESC, byte)
                else:
                    new_data += struct.pack("!B", byte)
            return new_data
        # 尝试在信道上发送帧
        frame = pre_process(frame)
        data = struct.pack("!B", FLAG) + frame + struct.pack("!B", FLAG)  # 加上起止标志字节
        try:
            self.channel.send(data)
        except Exception as e:
            print("[Sender] Channel is not accessible:", e)
            sys.exit(-1)

    def __make_nak_frame(self, seq):
        frame_fmt_header = "!BB"
        frame_fmt_tail = "!I"
        frame = struct.pack(frame_fmt_header, FRAME_TYP_NAK, seq % self.seq_range)  # 头部字段
        frame += struct.pack(frame_fmt_tail, zlib.crc32(frame) & 0xffffffff)  # 尾部crc32
        return frame

    def __make_ack_frame(self, seq):
        frame_fmt_header = "!BB"
        frame_fmt_tail = "!I"
        frame = struct.pack(frame_fmt_header, FRAME_TYP_ACK, seq % self.seq_range)  # 头部字段
        frame += struct.pack(frame_fmt_tail, zlib.crc32(frame) & 0xffffffff)  # 尾部crc32
        return frame

    def __send_nak(self, Rn):
        # 随机传输延迟
        time.sleep(random.uniform(0.5, 3))
        seq = Rn % self.seq_range
        # 检查是否有强制loss，一个loss信号起效一次
        try:
            loss = requests.get(f"{self.get_cmd_api}?field=loss", timeout=0.3).content
            if loss == b"true":
                # 发送nak帧并丢失
                requests.get(f"{self.set_cmd_api}?field=loss&value=false", timeout=0.3)
                self.__report_nakloss_action(seq)
                print(f"[Receiver] Loss frame! (nakNo: {seq})")
                return False
        except Exception as e:
            print(e)
            return False
        # 发送nak帧
        frame = self.__make_nak_frame(seq)
        self.__media_send_frame(frame)
        print(f"[Receiver] send NAK({seq})")
        return True

    def __send_ack(self, Rn):
        # 随机传输延迟
        time.sleep(random.uniform(0.5, 3))
        seq = Rn % self.seq_range
        # 检查是否有强制loss，一个loss信号起效一次
        try:
            loss = requests.get(f"{self.get_cmd_api}?field=loss", timeout=0.3).content
            if loss == b"true":
                # 发送ack帧并丢失
                requests.get(f"{self.set_cmd_api}?field=loss&value=false", timeout=0.3)
                self.__report_ackloss_action(seq)
                print(f"[Receiver] Loss frame! (ackNo: {seq})")
                return False
        except Exception as e:
            print(e)
            return False
        # 发送ack帧
        frame = self.__make_ack_frame(seq)
        self.__media_send_frame(frame)
        print(f"[Receiver] send ACK({seq})")
        return True

    def __physical_layer_monitor(self):
        while True:
            frame = b""
            # 寻找帧起始标志
            while True:
                if self.channel.recv(1) == struct.pack("!B", FLAG):
                    break
            # 同步
            while True:
                byte = self.channel.recv(1)
                if byte == struct.pack("!B", FLAG):
                    continue
                else:
                    frame += byte
                    break
            # 寻找帧结束标志
            while True:
                byte = self.channel.recv(1)
                if byte == struct.pack("!B", ESC):
                    frame += self.channel.recv(1)
                elif byte == struct.pack("!B", FLAG):
                    break
                else:
                    frame += byte
            self.event_lock.acquire()
            self.event = EVENT_ARRIVAL_NOTIFICATION
            self.recv_frame_buf = frame
            self.new_event.set()

    def __deliver_data(self, seq):
        seq = seq % self.seq_range
        data = self.__extract_frame_payload(self.frame_queue[seq])
        print(f"[Receiver] Deliver Data (seq: {seq}, len: {len(data)}): {data}")
        self.__report_deliver_data_action(seq, data.hex())

    def __main_loop(self):
        def do_release():
            # 清除事件信号
            self.new_event.clear()
            # 释放事件锁
            self.event_lock.release()
        # 监听物理层事件，线程动作通过EVENT反馈
        physical_layer_monitor = Thread(target=self.__physical_layer_monitor)
        physical_layer_monitor.setDaemon(True)
        physical_layer_monitor.start()

        while True:
            # 等待事件
            self.new_event.wait()
            # 帧到达事件
            if(self.event == EVENT_ARRIVAL_NOTIFICATION):
                frame = self.recv_frame_buf
                if not self.__check_frame(frame):
                    # 丢弃损坏的帧
                    print("[Receiver] Bad frame, drop it!")
                    if not self.nak_send:
                        # 如果没发送过NAK，则发送NAK
                        if self.__send_nak(self.Rn):
                            self.__report_nak_action(self.Rn % self.seq_range)
                        self.nak_send = True
                    do_release()
                    continue
                #print(f"[Receiver] New frame received (seq: {self.__get_frame_seq(frame)})")

                seq = self.__get_frame_seq(frame)
                if seq != (self.Rn % self.seq_range) and not self.nak_send:
                    # 处理seq和当前Rn不匹配
                    print(f"[Receiver] Seq not match! (Seq: {seq}, Rn: {self.Rn % self.seq_range})")
                    if self.__send_nak(self.Rn):
                        self.__report_nak_action(self.Rn % self.seq_range)
                    self.nak_send = True

                if self.__seq_in_window(seq) and not self.__marked_seq(seq):
                    # 如果接收到的seq在window中，且没有被标记过，则缓存下来并标记
                    self.frame_queue[seq] = frame
                    self.slots[seq] = True
                    tmp_slots = copy.deepcopy(self.slots)
                    while self.__marked_seq(self.Rn % self.seq_range):
                        # 向网络层传递数据
                        self.__deliver_data(self.Rn % self.seq_range)
                        # 清空缓存
                        self.frame_queue[self.Rn % self.seq_range] = b""
                        self.slots[self.Rn % self.seq_range] = False
                        self.Rn = self.Rn + 1
                        self.ack_needed = True
                    # 判断是否需要发送ACK
                    if self.ack_needed:
                        if self.__send_ack(self.Rn % self.seq_range):
                            self.__report_ack_action(self.Rn % self.seq_range, tmp_slots)
                        self.ack_needed = False
                        self.nak_send = False

            print(f"[Receiver] Window state: (Rn: {self.Rn % self.seq_range})")
            # 释放资源
            do_release()

    def __report_deliver_data_action(self, seq, payload):
        data = {
            "time": time.time(),
            "role": "receiver",
            "action": "deliver",
            "data":{
                "seq": seq,
                "Rn": self.Rn,
                "payload": payload
            }
        }
        try:
            requests.post(self.put_api, json=data, timeout=0.5)
        except:
            pass   


    def __report_bad_frame_action(self, raw_data, reason):
        data = {
            "time": time.time(),
            "role": "receiver",
            "action": "badframe",
            "data":{
                "reason": reason,
                "raw_data": raw_data
            }
        }
        try:
            requests.post(self.put_api, json=data, timeout=0.5)
        except:
            pass      

    def __report_ack_action(self, seq, slots=None):
        data = {
            "time": time.time(),
            "role": "receiver",
            "action": "ack",
            "data":{
                "seq": seq,
                "Rn": self.Rn,
                "slots": self.slots if slots != None else slots
            }
        }
        try:
            requests.post(self.put_api, json=data, timeout=0.5)
        except:
            pass

    def __report_nak_action(self, seq):
        data = {
            "time": time.time(),
            "role": "receiver",
            "action": "nak",
            "data":{
                "seq": seq,
                "Rn": self.Rn,
                "slots": self.slots
            }
        }
        try:
            requests.post(self.put_api, json=data, timeout=0.5)
        except:
            pass

    def __report_nakloss_action(self, seq):
        data = {
            "time": time.time(),
            "role": "receiver",
            "action": "nakloss",
            "data":{
                "seq": seq,
                "Rn": self.Rn,
                "slots": self.slots
            }
        }
        try:
            requests.post(self.put_api, json=data, timeout=0.5)
        except:
            pass

    def __report_ackloss_action(self, seq):
        data = {
            "time": time.time(),
            "role": "receiver",
            "action": "ackloss",
            "data":{
                "seq": seq,
                "Rn": self.Rn,
                "slots": self.slots
            }
        }
        try:
            requests.post(self.put_api, json=data, timeout=0.5)
        except:
            pass

    def online(self):
        self.channel = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.channel.connect(self.receiver_interface)
            self.is_online = 1
        except:
            print("[Receiver] Channel is not accessible, Please wait and try again!")
            sys.exit(-1)

    def work(self):
        if self.is_online:
            self.__main_loop()
        else:
            print("[Receiver] Media does not exist!")

def main():
    receiver = Receiver()
    receiver.online()
    receiver.work()

if __name__ == "__main__":
    main()
