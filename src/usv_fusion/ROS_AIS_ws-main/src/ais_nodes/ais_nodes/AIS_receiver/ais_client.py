import socket
from pyais import decode
from .fsm_nmea import NMEA


class AIS_Client():
    def __init__(
            self,
            host,
            port,
    ):
        self.addr = (host, port)
        self.client = socket.socket()
        self.nmea_handler = NMEA()
        self.seq_buffer = []
        # int <ais_report_type> : func(ais_report)
        self.encrypted_handlers = dict()
        # unencrypted msg parser
        self.unencrypted_handler = None

    def start(self):
        try:
            self.client.connect(self.addr)
            print("AIS connection complete!")
            return True
        except Exception as e:
            print("Connecting to {} failed.".format(self.addr))
            print(e)
            return False
    
    def handle_encrypted_msg(self, ais_report):
        msg_type = ais_report.msg_type
        if msg_type and msg_type in self.encrypted_handlers.keys():
            msg_handle_func = self.encrypted_handlers[msg_type]
            msg_handle_func(ais_report)

    def handle_unencrypted_msg(self, nmea_msg_dict):
        if self.unencrypted_handler is None:
            pass
        else:
            self.unencrypted_handler(nmea_msg_dict)

    def update_encrypted_handlers(self, msg_type, handle_func):
        self.encrypted_handlers.update({msg_type: handle_func})

    def update_unencrypted_handler(self, handle_func):
        self.unencrypted_handler = handle_func

    def is_encrypted_msg(self, nmea_msg):
        # encrypted_msg starts with ! while plain msg with $
        return nmea_msg["head"][0] == "!"

    def is_sequential_msg(self, nmea_msg):
        # if sequence total is not 1
        return nmea_msg["content"][0] != "1"

    def handle_sequence_msg(self, nmea_msg):
        # stores and return msg seq if they emerge in a seq
        msg_total = int(nmea_msg["content"][0])
        msg_num = int(nmea_msg["content"][1])
        seq_id = int(nmea_msg["content"][2])
        # if first msg
        if msg_num == 1:
            self.seq_buffer = [nmea_msg]
            return

        # if not first msg, seq_buffer should not be empty
        if len(self.seq_buffer) == 0:
            return

        last_msg = self.seq_buffer[-1]
        last_msg_total = int(last_msg["content"][0])
        last_msg_num = int(last_msg["content"][1])
        last_seq_id = int(last_msg["content"][2])


        # if repeated msg from AIS, do nothing
        if last_msg["raw"] == nmea_msg["raw"]:
            print("Received repeated seq msg")
        # if msgs are not in same seq
        elif last_msg_total != msg_total or last_seq_id != seq_id:
            print("Received conflict seq msg, abandon new frame")
            return
        # if same seq msg, but not the 'next' msg
        elif last_msg_num+1 != msg_num:
            print("Received a seq msg, but discontinous tag, abandon new frame")
            return
        # store seq msg
        else:
            self.seq_buffer.append(nmea_msg)
            # group formed
            if msg_num == msg_total:
                # return seq, clear buffer
                msg_seq = [msg["raw"] for msg in self.seq_buffer]
                self.seq_buffer = []
                return msg_seq
            # awaiting further seq msgs
            else:
                return

    def handle_nmea_msg(self, nmea_msg):
        # handle encrypted msg
        if self.is_encrypted_msg(nmea_msg):
            if self.is_sequential_msg(nmea_msg):
                #print(nmea_msg["content"])
                msg_seq = self.handle_sequence_msg(nmea_msg)
                if msg_seq is not None:
                    #print(msg_seq)
                    try:
                        msg_info = decode(*msg_seq)
                        #print(msg_info)
                    except Exception as e:
                        print(f"Decode ais report failed: {e}")
                        return
                # msg_seq is None
                else:
                    return
            # single msg
            else:
                try:
                    msg_info = decode(nmea_msg["raw"])
                except Exception as e:
                    print(f"Decode ais report failed: {e}")
                    return
                #print(msg_info.msg_type)
                #print(msg_info)
            if msg_info:
                self.handle_encrypted_msg(msg_info)
        else:
            # $ here
            self.handle_unencrypted_msg(nmea_msg)

    def listen(self):
        while True:
            msg = self.client.recv(1024).decode("utf-8").strip()
            parsed_results = self.nmea_handler.parse_chs(msg)
            for nmea_msg in parsed_results:
                self.handle_nmea_msg(nmea_msg)
