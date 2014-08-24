
from scapy.all import sniff
from .eap import *
from rpyutils import check_root, get_frequency, if_hwaddr
from .callbacks import Callbacks
from .tint import TunInterface
from .conf import Conf
from time import time, sleep
from scapy.layers.dot11 import RadioTap, conf as scapyconf


class FakeAccessPoint(object):
    class FakeBeaconTransmitter(threading.Thread):
        def __init__(self, ap):
            threading.Thread.__init__(self)
            self.ap = ap
            self.setDaemon(True)
            self.interval = 0.1

        def run(self):
            while True:
                for ssid in self.ap.ssids:
                    self.ap.callbacks.cb_dot11_beacon(ssid)

                # Sleep
                sleep(self.interval)

    @classmethod
    def from_file(cls, path):
        conf = Conf(path)

        # Required
        interface = conf.get('interface', 'mon0')
        channel = int(conf.get('channel', 1))
        wpa = conf.get('wpa', False)

        # Optional
        mac = conf.get('mac', if_hwaddr(interface))
        bpffilter = conf.get('filter', "")

        # Apply required settings
        ap = FakeAccessPoint(interface, channel, mac, wpa=wpa, bpffilter=bpffilter)
        ap.ieee8021x = conf.get('ieee8021x', 0)

        return ap

    def __init__(self, interface, channel, mac, wpa=False, bpffilter=""):
        self.ssids = []
        self.current_ssid_index = 0

        self.interface = interface
        self.channel = channel
        self.mac = mac
        self.wpa = wpa
        self.ieee8021x = 0
        self.lfilter = None
        if bpffilter == "":
            self.bpffilter = "not ( wlan type mgt subtype beacon ) and ((ether dst host " + self.mac + ") or (ether dst host ff:ff:ff:ff:ff:ff))"
        self.ip = "10.0.0.1"
        self.boottime = time()
        self.sc = 0
        self.aid = 0
        self.mutex = threading.Lock()
        self.eap_manager = EAPManager()

        self.beaconTransmitter = self.FakeBeaconTransmitter(self)
        self.beaconTransmitter.start()

        self.tint = None

        self.callbacks = Callbacks(self)

    def add_ssid(self, ssid):
        if not ssid in self.ssids and ssid != '':
            self.ssids.append(ssid)

    def remove_ssid(self, ssid):
        if ssid in self.ssids:
            self.ssids.remove(ssid)

    def get_ssid(self):
        if len(self.ssids) > 0:
            return self.ssids[self.current_ssid_index]

    def cycle_ssid(self):
        maxidx = len(self.ssids)
        self.current_ssid_index = ((self.current_ssid_index + 1) % maxidx)

    def current_timestamp(self):
        return (time() - self.boottime) * 1000000

    def next_sc(self):
        self.mutex.acquire()
        self.sc = (self.sc + 1) % 4096
        temp = self.sc
        self.mutex.release()

        return temp * 16  # Fragment number -> right 4 bits

    def next_aid(self):
        self.mutex.acquire()
        self.aid = (self.aid + 1) % 2008
        temp = self.aid
        self.mutex.release()

        return temp

    def get_radiotap_header(self):
        radiotap_packet = RadioTap(len=18, present='Flags+Rate+Channel+dBm_AntSignal+Antenna', notdecoded='\x00\x6c' + get_frequency(self.channel) + '\xc0\x00\xc0\x01\x00\x00')
        return radiotap_packet

    def run(self):
        check_root()
        self.tint = TunInterface(self)
        self.tint.start()
        scapyconf.iface = self.interface
        sniff(iface=self.interface, prn=self.callbacks.cb_recv_pkt, store=0, filter=self.bpffilter)