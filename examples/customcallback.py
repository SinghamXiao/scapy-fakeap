# This example demonstrates how to create a new callback for a specific Callbacks() instance.
# The callback will trigger each time an EAPOL packet is sniffed.

from types import MethodType
from scapy.layers.dot11 import EAPOL
from fakeap import *


def do_something(self):  # Our custom callback
    print("Got EAPOL packet!")


def my_recv_pkt(self, pkt):  # We override recv_pkt to include a trigger for our callback
    if EAPOL in pkt:
        self.cb_do_something()
    self.recv_pkt(pkt)

ap = FakeAccessPoint('mon0', 1, '10:fe:ed:1d:ae:ca', AP_WLAN_TYPE_OPEN)
my_callbacks = Callbacks(ap)
my_callbacks.cb_recv_pkt = MethodType(my_recv_pkt, my_callbacks)
my_callbacks.cb_do_something = MethodType(do_something, my_callbacks)
ap.callbacks = my_callbacks

ap.add_ssid('My first callback!')
ap.run()