# vim: set ts=8 sw=4 sts=4 et ai:
# Copyright (C) 2011, OSSO B.V., Walter Doekes
import socket
import sys
try:
    from ssl import wrap_socket as ssl_socket
except ImportError:
    class ssl_socket:
        def __init__(self, socket):
            self.socket = socket

        def __getattr__(self, name):
            return getattr(self.socket, name)

        def connect(self, *args, **kwargs):
            self.socket.connect(*args, **kwargs)
            self.ssl = socket.ssl(self.socket)

        def read(self, *args, **kwargs):
            return self.ssl.read(*args, **kwargs)
        recv = read

        def write(self, *args, **kwargs):
            return self.ssl.write(*args, **kwargs)
        send = write


IANA_TCP_PORT = 700  # the default TCP port for EPP


class EppSocket(object):
    def __init__(self, socket, tracefile=None):
        self.socket = socket
        self.tracefile = tracefile

    def close(self):
        assert self.socket is not None
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()
        self.socket = None

    def read(self):
        # FIXME: catch timeout, broken pipe, etc.
        assert self.socket is not None
        length = self.socket.recv(4)
        length = (ord(length[0]) << 24 | ord(length[1]) << 16 | ord(length[2]) << 8 | ord(length[3])) - 4
        # print 'attempting to read %d bytes\n' % length
        data = ''
        while len(data) < length:
            data += self.socket.recv(length - len(data))
        if self.tracefile:
            self.tracefile.write('\x1b[1;35minput[\x1b[0m%s\x1b[1;35m]\x1b[0m\n' % data)
        return data

    def write(self, data):
        # FIXME: catch timeout, broken pipe, etc.
        assert self.socket is not None
        if self.tracefile:
            self.tracefile.write('\x1b[1;34moutput[\x1b[0m%s\x1b[1;34m]\x1b[0m\n' % data)
        l = len(data) + 4
        length = '%c%c%c%c' % (chr((l >> 24) & 0xff), chr((l >> 16) & 0xff), chr((l >> 8) & 0xff), chr(l & 0xff))
        sent = 0
        data = '%s%s' % (length, data)
        while sent < l:
            sent += self.socket.send(data[sent:])


def wrap_socket(socket, tracefile=None):
    '''
    Wrap the socket in an EppSocket. Now you can only read/write/close
    the socket.
    '''
    return EppSocket(socket, tracefile=tracefile)


def tcp_connect(address, ssl=True, tracefile=None):
    '''
    Example connection function.
    '''
    if isinstance(address, basestring):
        address = (str(address), IANA_TCP_PORT)
    else:
        assert len(address) == 2
        address = (str(address[0]), int(address[1]))

    # Lookup addresses
    addresses = socket.getaddrinfo(address[0], address[1])
    addresses = [i for i in addresses if (i[0] == socket.AF_INET or i[0] == socket.AF_INET6) and i[1] == socket.SOCK_STREAM]
    addresses.sort(key=lambda x: x[0], reverse=True)  # AF_INET6 sorts before AF_INET

    for address in addresses:  # should be nonempty, or we have a previous gaierror
        try:
            sock = socket.socket(*address[0:3])
            if ssl:
                ssl_sock = ssl_socket(sock)  # skip certificate checks
                ssl_sock.connect(address[4])
                sock = ssl_sock
            break
        except:
            exc_info = sys.exc_info()
            pass
    else:
        # Re-raise exception
        raise exc_info[1], None, exc_info[2]

    return wrap_socket(sock, tracefile=tracefile)


def main():
    socket = tcp_connect('testdrs.my-domain-registry.nl')
    socket.write("""<?xml version="1.0" encoding="UTF-8" standalone="no"?><epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><hello/></epp>""")
    data = socket.read()
    print data
    data = socket.read()
    socket.close()
    print data


if __name__ == '__main__':
    main()
