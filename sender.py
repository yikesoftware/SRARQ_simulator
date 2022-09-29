import socket
import string
import random
import struct
import zlib
import time
import sys
import requests, json
from threading import Timer, Event, Thread, Lock

ESC = 0x1b & 0xff  # ESC char
FLAG = 0x7e & 0xff  # 0b01111110
MAX_FRAME_DATA = 16
MIN_FRAME_SIZE = 6
FRAME_TYP_DATA = 0x0
FRAME_TYP_ACK = 0x1
FRAME_TYP_NAK = 0x2
MAX_SEQ_BITS = 8

EVENT_HANGING = 0
EVENT_REQ_TO_SEND = 1
EVENT_ARRIVAL_NOTIFICATION = 2
EVENT_TIMEOUT = 3

MAX_TIMEOUT = 6

class Sender:
    def __init__(self, seq_bits: int = 4, sender_interface: tuple = ("127.0.0.1", 10001)):
        seq_bits = MAX_SEQ_BITS if seq_bits > MAX_SEQ_BITS else seq_bits

        self.window_size = 2**(seq_bits-1)
        self.seq_range = 2**seq_bits
        self.sender_interface = sender_interface
        self.put_api = "http://127.0.0.1:8080/action/put"
        self.get_cmd_api = "http://127.0.0.1:8080/cmd/get"
        self.set_cmd_api = "http://127.0.0.1:8080/cmd/set"

        self.Sw = self.window_size
        self.frame_queue = [b"" for _ in range(self.seq_range)]
        self.timers = [None for _ in range(self.seq_range)]
        self.is_online = 0
        self.Sf = 0
        self.Sn = 0

        self.new_event = Event()
        self.event_lock = Lock()
        self.event = EVENT_HANGING
        self.timeout_seq = 0
        
        self.recv_frame_buf = b""

    def __get_data(self) -> bytes:
        '''
        生成随机长度的上层数据（最大长度不超过MAX_FRAME_DATA）
        '''
        ch_table = string.digits + string.ascii_letters
        rand_str = "".join([ch_table[random.randint(0, len(ch_table)-1)]
                            for _ in range(random.randint(1, MAX_FRAME_DATA))])
        return rand_str.encode()

    def __make_data_frames(self, data: bytes):
        '''
        将上层数据成帧
        '''
        # frame:
        # FLAG |
        # TYPE | SEQ |
        # DATA |
        # CRC32 |
        # FLAG |
        frame_fmt_header = "!BB"
        frame_fmt_tail = "!I"

        # 单个帧最大携带MAX_FRAME_DATA字节数据，传入多余的会被截断
        frame = struct.pack(
            frame_fmt_header, FRAME_TYP_DATA, self.Sn % self.seq_range)  # 头部字段
        frame += data  # Payload
        u32crc = zlib.crc32(frame) & 0xffffffff
        frame += struct.pack(frame_fmt_tail, u32crc)  # 尾部crc32
        print("[Sender] Make a frame from data:", data)
        self.__report_make_frame_action(self.Sn % self.seq_range, data.hex(), u32crc)
        return frame

    def __get_frame_type(self, frame:bytes)->int:
        return frame[0]

    def __get_frame_seq(self, frame:bytes)->int:
        return frame[1]

    def __seq_sent(self, seq):
        for i in range(self.Sf, self.Sn+1):
            if i % self.seq_range == seq:
                return True
        return False

    def __check_frame(self, frame:bytes):
        # 检查长度
        if len(frame) < MIN_FRAME_SIZE or len(frame) > MIN_FRAME_SIZE+MAX_FRAME_DATA:
            self.__report_bad_frame_action(frame.hex(), "Bad Length")
            return False
        # 检查CRC32
        if zlib.crc32(frame[:-4]) & 0xffffffff != struct.unpack("!I", frame[-4:])[0]:
            self.__report_bad_frame_action(frame.hex(), "CRC32 Error Type")
            return False
        # 检查类型
        if self.__get_frame_type(frame) not in (FRAME_TYP_DATA, FRAME_TYP_ACK, FRAME_TYP_NAK):
            self.__report_bad_frame_action(frame.hex(), "Bad Type")
            return False
        return True

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
            sys.exit(0)
        

    def __send_data_frame(self, frame:bytes):
        # 检查是否有强制loss，一个loss信号起效一次
        try:
            loss = requests.get(f"{self.get_cmd_api}?field=loss", timeout=0.3).content
            if loss == b"true":
                # 发送数据帧并丢失
                requests.get(f"{self.set_cmd_api}?field=loss&value=false", timeout=0.3)
                self.__report_sendloss_action(self.__get_frame_seq(frame))
                print(f"[Sender] Loss frame! (seq: {self.__get_frame_seq(frame)})")
                return False                
        except Exception as e:
            print(e)
            return False
        # 发送数据帧
        self.__media_send_frame(frame)
        print(f"[Sender] Send frame. (seq: {self.__get_frame_seq(frame)})")
        return True
        

    def __resend_frame(self, Sn):
        # 重发帧
        frame = self.frame_queue[Sn % self.seq_range]
        # 检查是否有强制loss，一个loss信号起效一次
        try:
            loss = requests.get(f"{self.get_cmd_api}?field=loss", timeout=0.3).content
            if loss == b"true":
                # 发送数据帧并丢失
                requests.get(f"{self.set_cmd_api}?field=loss&value=false", timeout=0.3)
                self.__report_sendloss_action(self.__get_frame_seq(frame))
                print(f"[Sender] Loss frame! (seq: {Sn % self.seq_range})")
                return False
        except Exception as e:
            print(e)
            return False
        # 发送数据帧
        self.__media_send_frame(frame)
        print(f"[Sender] Resend frame. (seq: {Sn % self.seq_range})")
        return True
        

    def __network_layer_monitor(self):
        while True:
            # 网络层的发送速度是随机的
            time.sleep(random.uniform(1.5, 5.0)) 
            self.event_lock.acquire()
            self.event = EVENT_REQ_TO_SEND
            self.new_event.set()

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

    def __time_out_event(self, Sn):
        self.event_lock.acquire()
        self.event = EVENT_TIMEOUT
        self.timeout_seq = Sn
        self.new_event.set()

    def __set_timer(self, Sn):
        old_timer = self.timers[Sn]
        if isinstance(old_timer, Timer) and old_timer.is_alive():
            # 停止旧定时器
            old_timer.cancel()
        # 设置新定时器
        self.timers[Sn] = Timer(MAX_TIMEOUT, self.__time_out_event, args=(Sn, ))
        self.timers[Sn].setDaemon(True)
        self.timers[Sn].start()
        return self.timers[Sn]

    def __stop_timer(self, Sn):
        timer = self.timers[Sn]
        if isinstance(timer, Timer):
            # 停止旧定时器
            timer.cancel()

    def __main_loop(self):
        def do_release():
            # 清除事件信号
            self.new_event.clear()
            # 释放事件锁
            self.event_lock.release()
        # 监听网络层&物理层事件，线程动作通过EVENT反馈
        network_layer_monitor = Thread(target=self.__network_layer_monitor)
        physical_layer_monitor = Thread(target=self.__physical_layer_monitor)
        network_layer_monitor.setDaemon(True)
        physical_layer_monitor.setDaemon(True)
        network_layer_monitor.start()
        physical_layer_monitor.start()

        while True:
            # 等待事件
            self.new_event.wait()
            # 有来自网络层的数据要发送
            if self.event == EVENT_REQ_TO_SEND:
                if self.Sn-self.Sf >= self.Sw:
                    # 窗口满，无法发送
                    do_release()
                    continue
                # 取得网络层的数据
                data = self.__get_data()
                # 成帧
                frame = self.__make_data_frames(data)
                # 缓存
                self.frame_queue[self.Sn % self.seq_range] = frame
                # 发送
                if self.__send_data_frame(frame):
                    self.__report_send_action(self.Sn % self.seq_range) # api
                # 设置定时器
                self.__set_timer(self.Sn % self.seq_range)
                # Seq递增
                self.Sn = self.Sn + 1
            
            # 有来自物理层的帧到达
            if self.event == EVENT_ARRIVAL_NOTIFICATION:
                frame = self.recv_frame_buf
                if not self.__check_frame(frame):
                    print("[Sender] Bad frame, drop it!")
                    do_release()
                    continue
                #print(f"[Sender] New frame received (seq: {self.__get_frame_seq(frame)}, type: {self.__get_frame_type(frame)})")

                frame_type = self.__get_frame_type(frame)
                # 收到NAK帧
                if frame_type == FRAME_TYP_NAK:
                    nak_no = self.__get_frame_seq(frame)
                    print(f"[Sender] Receive NAK({nak_no})")
                    if self.__resend_frame(nak_no):
                        self.__report_resend_action(nak_no, "For nak") # api
                    self.__set_timer(nak_no)
                # 收到ACK帧
                if frame_type == FRAME_TYP_ACK:
                    ack_no = self.__get_frame_seq(frame)
                    print(f"[Sender] Receive ACK({ack_no})")
                    if self.__seq_sent(ack_no):
                        # 循环清除帧缓存并取消定时器
                        while self.Sf % self.seq_range != ack_no:
                            self.frame_queue[self.Sf % self.seq_range] = b""
                            self.__stop_timer(self.Sf % self.seq_range)
                            print("[Sender] Stop timer:", self.Sf % self.seq_range)
                            self.Sf = self.Sf + 1

            if self.event == EVENT_TIMEOUT:
                print(f"[Sender] Timout({self.timeout_seq})")
                self.__set_timer(self.timeout_seq)
                if self.__resend_frame(self.timeout_seq):
                    self.__report_resend_action(self.timeout_seq, "For timeout") # api

            print(f"[Sender] Window state: (Sf: {self.Sf % self.seq_range}, Sn: {self.Sn % self.seq_range})")
            # 释放资源
            do_release()

    def __report_make_frame_action(self, seq, payload, crc32):
        data = {
            "time": time.time(),
            "role": "sender",
            "action": "makeframe",
            "data":{
                "seq": seq,
                "payload": payload,
                "crc32": crc32,
                "Sf": self.Sf,
                "Sn": self.Sn,
                "Sw": self.Sw
            }
        }
        try:
            requests.post(self.put_api, json=data, timeout=0.3)
        except:
            pass   

    def __report_bad_frame_action(self, raw_data, reason):
        data = {
            "time": time.time(),
            "role": "sender",
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

    def __report_send_action(self, seq):
        data = {
            "time": time.time(),
            "role": "sender",
            "action": "send",
            "data":{
                "seq": seq,
                "Sf": self.Sf,
                "Sn": self.Sn,
                "Sw": self.Sw
            }
        }
        try:
            requests.post(self.put_api, json=data, timeout=0.3)
        except:
            pass

    def __report_resend_action(self, seq, reason="None"):
        data = {
            "time": time.time(),
            "role": "sender",
            "action": "resend",
            "data":{
                "seq": seq,
                "reason": reason,
                "Sf": self.Sf,
                "Sn": self.Sn,
                "Sw": self.Sw
            }
        }
        try:
            requests.post(self.put_api, json=data, timeout=0.3)
        except:
            pass

    def __report_sendloss_action(self, seq):
        data = {
            "time": time.time(),
            "role": "sender",
            "action": "loss",
            "data":{
                "seq": seq,
                "Sf": self.Sf,
                "Sn": self.Sn,
                "Sw": self.Sw
            }
        }
        try:
            requests.post(self.put_api, json=data, timeout=1)
        except:
            pass    

    def online(self):
        self.channel = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.channel.connect(self.sender_interface)
            self.is_online = 1
        except:
            print("[Sender] Channel is not accessible, Please wait and try again!")
            sys.exit(-1)

    def work(self):
        if self.is_online:
            self.__main_loop()
        else:
            print("[Sender] Media does not exist!")

    def offline(self):
        if self.is_online:
            if getattr(self.channel, '_closed') == False:
                self.channel.close()
            self.is_online = 0

    def tester(self):
        pass


def main():
    sender = Sender()
    sender.online()
    sender.work()

if __name__ == "__main__":
    main()
