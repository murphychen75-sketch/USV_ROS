# encoding: utf-8
r"""
  ____   _____   ____ _____   
 /    \ /     \_/ __ \\__  \  
|   |  \  Y Y  \  ___/ / __ \_
|___|  /__|_|  /\___  >____  /
     \/      \/     \/     \/ 
___________.__       .__  __                     
\_   _____/|__| ____ |__|/  |_  ____             
 |    __)  |  |/    \|  \   __\/ __ \            
 |     \   |  |   |  \  ||  | \  ___/            
 \___  /   |__|___|  /__||__|  \___  >           
     \/            \/              \/            
  _________ __          __                       
 /   _____//  |______ _/  |_  ____               
 \_____  \\   __\__  \\   __\/ __ \              
 /        \|  |  / __ \|  | \  ___/              
/_______  /|__| (____  /__|  \___  >             
        \/           \/          \/              
   _____                .__    .__               
  /     \ _____    ____ |  |__ |__| ____   ____  
 /  \ /  \\__  \ _/ ___\|  |  \|  |/    \_/ __ \ 
/    Y    \/ __ \\  \___|   Y  \  |   |  \  ___/ 
\____|__  (____  /\___  >___|  /__|___|  /\___  >
        \/     \/     \/     \/        \/     \/ 

this module provides a nmea finite state machine
"""
"""
author: vectorwang@hotmail.com
change_history:
    20230106    remastered by vectorwang
    20230415    implemented comments by vectorwang
    20241101    now detects msgs starting with !
"""

from transitions import Machine


class NMEA():
    """
    NMEA is a finite state machine for parsing nmea message
    each nmea message starts with '$', divides each data with ',',
    divides tail crc check with '*'
    a standard nmea string may look like this:
    $header,data1,data2,data3*[2 chars of crc]
    """
    # states setup
    states = ['waitingStart', 'receivingData', 'waitingCRC1', 'waitingCRC2']

    def __init__(self):
        """
        init states, transitions etc.
        """
        self.message = ""

        # finite state machine set up
        self.machine = Machine(model=self, states=NMEA.states, initial='waitingStart')
        self.machine.add_transition(trigger='dollarIn', source='*', dest='receivingData', before='_clear_message')
        self.machine.add_transition('dataIn', 'receivingData', 'receivingData')
        self.machine.add_transition('dataIn', 'waitingCRC1', 'waitingCRC2')
        self.machine.add_transition('dataIn', 'waitingCRC2', 'waitingStart')
        self.machine.add_transition('asteriskIn', 'receivingData', 'waitingCRC1')

    def _clear_message(self):
        """
        clear cache
        """
        self.message = ""

    def parse_ch(self, ch):
        """
        feed a char into finite state machine
        will return a parsed dict of data
        if this char is the last char of a complete message
        params:
            ch, char, string with length 1
        returns:
            none or list[dict] with length 1, parsed data
        """
        try:
            if ch=="$" or ch=="!":
                self.dollarIn()
            elif ch=="*":
                self.asteriskIn()
            else:
                self.dataIn()
            self.message += ch
        except:
            self.state = 'waitingStart'


        if self.state == 'waitingStart' and len(self.message) > 0:
            msg_dict = self.parse_nmea_msg(self.message)
            if self.crc_check(msg_dict):
                return [msg_dict]
        return None

    def parse_chs(self, chs):
        """
        feed a string into finite state machine
        will return a list of parsed dicts
        if this string contains one or more complete message
        params:
            chs, chars, string
        returns:
            none or dict, parsed data
        """
        results = []
        for ch in chs:
            msg = self.parse_ch(ch)
            if msg:
                results.append(msg[0])

        return results

    def parse_nmea_msg(self, msg_str):
        """
        parse a complete string of nmea message
        returns a dict
        """
        msg_lst = msg_str.split('*')

        msg_content_str = msg_lst[0]
        msg_crc = msg_lst[1]

        msg_content_lst = msg_content_str.split(',')
        msg_head = msg_content_lst[0]
        msg_content_lst = msg_content_lst[1:]

        return {"head":msg_head, "content":msg_content_lst, "crc":msg_crc, "raw":msg_str}

    def crc_check(
        self,
        msg_dict,
    ) -> bool:
        """
        override this func to enable crc check
        """
        return True


class __ExampleGPS():
    """
    !!! example class
    this class contains methods to parse gps nmea msg
    """
    def __init__(self):
        self.state_machine = NMEA()

    def parse_gps(self, raw_data):
        content = raw_data['content']
        if raw_data['head'] == '$GTIMU':
            return {
                'GPSWeek': content[0],
                'GPSTime': content[1],
                'GyroX': content[2],
                'GyroY': content[3],
                'GyroZ': content[4],
                'AccX': content[5],
                'AccY': content[6],
                'AccZ': content[7],
                'Tpr': content[8],
            }
        elif raw_data['head'] == '$GPFPD':
            return {
                'GPSWeek': content[0],
                'GPSTime': content[1],
                'Heading': content[2],
                'Pitch': content[3],
                'Roll': content[4],
                'Lati': content[5],
                'Longi': content[6],
                'Alti': content[7],
                'VE': content[8],
                'VN': content[9],
                'VU': content[10],
                'Baseline': content[11],
                'NSV1': content[12],
                'NSV2': content[13],
                'Status': content[14],
            }

    def parse_chs(self, chs):
        result = self.state_machine.parse_chs(chs)
        if result:
            return [self.parse_gps(msg) for msg in result]
