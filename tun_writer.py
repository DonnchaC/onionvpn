#!/usr/bin/env python

# External modules
from twisted.internet import main, interfaces, reactor
from zope.interface import implements
import os
from scapy.all import IP, TCP, hexdump
import binascii
from zope.interface import implementer
from twisted.python import log

# Internal modules
from tun_factory import TUNFactory
from tun_reader import TUNPacketProducer, TUN_TestConsumer


@implementer(interfaces.IConsumer, interfaces.IWriteDescriptor)
class TUNPacketConsumer(object):


    def __init__(self, tunDevice):
        self.tunDevice     = tunDevice
        self.fd            = os.dup(tunDevice.fileno())
        self.packets       = []
        self.producer      = None


    def registerProducer(self, producer, streaming):
        log.msg("registerProducer")
        assert streaming is True

        self.producer = producer
        self.producer.start_reading()

    def unregisterProducer(self):
        log.msg("unregisterProducer")
        self.producer.stop_reading()

    def write(self, packet):
        log.msg("write: packet len %s" % len(packet))
        if len(self.packets) == 0:
            log.msg("addWriter")
            reactor.addWriter(self)
        self.packets.append(packet)

    def connectionLost(self, reason):
        log.msg("connectionLost")
        # BUG: we should remove the tun device
        # unless someone is still using it...
        reactor.removeWriter(self)

    def fileno(self):
        return self.fd

    def doWrite(self):
        log.msg("doWrite")

        if len(self.packets) > 0:
            log.msg("doWrite: calling tunDevice.write")
            self.tunDevice.write(self.packets.pop(0))
        if len(self.packets) == 0:
            log.msg("doWrite: calling reactor.removeWriter(self)")
            reactor.removeWriter(self)

    def logPrefix(self):
        return 'TUNPacketConsumer'



# Note: this code below here is for testing... but it is all obsolete
# because i didn't maintain it

class TUN_TestProducer(object):

    implements(interfaces.IPullProducer)

    def __init__(self, consumer=None, packet=None):
        super(TUN_TestProducer, self).__init__()

        self.consumer     = consumer
        self.packet = packet

        consumer.registerProducer(self, streaming=True)


    def resumeProducing(self):
        assert self.consumer is not None

        for x in range(3):
            self.consumer.write(self.packet)

    def stopProducing(self):
        pass

    def start_reading(self):
        self.resumeProducing()


def main():

    ip  = IP(dst="10.1.1.1")
    tcp = TCP(dport   = 2600, 
              flags   = 'S',
              seq     = 32456,
              ack     = 32456,
              window  = 32456,
              options = [('MSS',binascii.unhexlify("DEADBEEFCAFE"))])

    packet = str(ip/tcp)

    tunFactory1   = TUNFactory(remote_ip = '10.1.1.3',
                              local_ip  = '10.1.1.4',
                              netmask   = '255.255.255.0',
                              mtu       = 1500)

    tunDevice1    = tunFactory1.buildTUN()


    tunFactory2   = TUNFactory(remote_ip = '10.1.1.5',
                              local_ip  = '10.1.1.6',
                              netmask   = '255.255.255.0',
                              mtu       = 1500)

    tunDevice2    = tunFactory2.buildTUN()


    # test the tests
    #tun_print_consumer = TUN_TestConsumer()
    #tun_producer = TUN_TestProducer(consumer=tun_print_consumer, packet=packet)

    # and then use the tests
    tun_print_consumer = TUN_TestConsumer()
    tun_reader   = TUNPacketProducer(tunDevice1, tun_print_consumer)

    tun_consumer = TUNPacketConsumer(tunDevice1)
    tun_reader   = TUNPacketProducer(tunDevice2, tun_consumer)

    ###tun_producer = TUN_TestProducer(consumer=tun_consumer, packet=packet)

    reactor.addReader(tun_reader)
    reactor.addWriter(tun_consumer)
    reactor.run()

if __name__ == '__main__':
    main()
