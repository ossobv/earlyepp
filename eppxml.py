# vim: set ts=8 sw=4 sts=4 et ai:
# Copyright (C) 2011, OSSO B.V., Walter Doekes
from lxml import etree
import eppsocket


class UnexpectedData(Exception):
    def __init__(self, output, input, xpath):
        self.output, self.input, self.xpath = output, input, xpath

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u'Expected %s xpath on %s command.' % (self.xpath, self.output.__class__.__name__)


class EppXml(object):
    def __init__(self, eppsocket):
        self.eppsocket = eppsocket

    def close(self):
        assert self.eppsocket is not None
        self.eppsocket.close()
        self.eppsocket = None

    def expect(self, write, xpath_read_check):
        if write is not None:
            self.write(write)
        xml = self.read()
        if xpath_read_check is not None:
            try:
                xpath(xml, xpath_read_check)[0]
            except IndexError:
                raise UnexpectedData(write, xml, xpath_read_check)
        return xml

    def read(self):
        assert self.eppsocket is not None
        return etree.XML(self.eppsocket.read())

    def write(self, xml):
        assert self.eppsocket is not None
        return self.eppsocket.write(fromdom(xml))


def fromdom(instance):
    if isinstance(instance, etree._Element):
        return etree.tostring(instance)
    return str(instance)

def todom(instance):
    if not isinstance(instance, etree._Element):
        return etree.XML(str(instance))
    return instance

def pp(dom):
    return etree.tostring(todom(dom), pretty_print=True)

def wrap_socket(socket):
    return EppXml(socket)

def xpath(dom, expr):
    '''Use as xpath(dom, '//epp:epp/epp:greeting').'''
    return dom.xpath(expr, namespaces={
        'epp': 'urn:ietf:params:xml:ns:epp-1.0',
        'contact': 'urn:ietf:params:xml:ns:contact-1.0',
        'domain': 'urn:ietf:params:xml:ns:domain-1.0',
    })

def main():
    xml = wrap_socket(eppsocket.tcp_connect('testdrs.my-domain-registry.nl'))
    x = xml.read()
    xml.close()
    print etree.tostring(x, pretty_print=True)


if __name__ == '__main__':
    main()
