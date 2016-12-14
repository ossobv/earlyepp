# vim: set ts=8 sw=4 sts=4 et ai:
# Copyright (C) 2011,2016, OSSO B.V., Walter Doekes
if not hasattr('', 'format'):
    from string import Template
    import re

    def str_format(string, *args, **kwargs):
        tpl = Template(string)
        tpl.pattern = str_format.re
        return tpl.substitute(*args, **kwargs)
    str_format.re = re.compile(r'\{(?P<named>[A-Za-z0-9_]+)\}')
else:
    str_format = (lambda x, **y: x.format(**y))


__all__ = (
    # Login takes (username, password)
    'Hello', 'Login', 'Logout',
    # MessageQueueRemoveFirst takes (msgid)
    'MessageQueueReadFirst', 'MessageQueueRemoveFirst',
    # Contact commands take (handle)
    'ContactCheck', 'ContactCreate', 'ContactDelete', 'ContactInfo', 'ContactUpdate',
    # Domain commands take (domainname)
    'DomainCheck', 'DomainCreate', 'DomainDelete', 'DomainDeleteCancel', 'DomainInfo', 'DomainUpdate',
    'DomainTransfer', 'DomainTransferApprove', 'DomainTransferCancel', 'DomainTransferState',
    # DNSSEC commands
    'DnssecDomainUpdate',
    # Host commands take (domainname) (used for setting up nameserver glue)
    'HostCheck', 'HostCreate', 'HostDelete', 'HostInfo', 'HostUpdate',
)

XPATH_OK = '/epp:epp/epp:response/epp:result[@code="1000"]'


class Base(object):
    template = u''
    variables = {}

    def __init__(self, **kwargs):
        self.variables = self.variables.copy()
        self.variables.update(kwargs)

    def __str__(self):
        return '%s%s%s%s' % (
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
            '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
            self._get_body().encode('UTF-8'),
            '</epp>'
        )

    def toxml(self, encoding='UTF-8'):
        assert encoding == 'UTF-8'
        return str(self)

    def _get_body(self):
        return str_format(self.template, **self.variables)


class Command(Base):
    def _get_custom(self):
        return ''

    def _get_body(self):
        self.variables['__custom__'] = self._get_custom()
        return '<command>%s</command>' % str_format(self.template, **self.variables)


class Hello(Base):
    template = u'<hello/>'


class Login(Command):
    # <clTRID>300100</clTRID><!-- optioneel ... -->
    template = u'''<login>
        <clID>{username}</clID>
        <pw>{password}</pw>
        <options><version>1.0</version><lang>en</lang></options>
        <svcs>
            <objURI>urn:ietf:params:xml:ns:contact-1.0</objURI>
            <objURI>urn:ietf:params:xml:ns:host-1.0</objURI>
            <objURI>urn:ietf:params:xml:ns:domain-1.0</objURI>
            <svcExtension><extURI>http://rxsd.my-domain-registry.nl/sidn-ext-epp-1.0</extURI></svcExtension>
        </svcs>
    </login>'''


class Logout(Command):
    template = u'''<logout/>'''


class MessageQueueBase(Command):
    ''' Message queue polling base. '''
    template = u'''<poll op="{op}"{poll_attrs}/>'''


class MessageQueueReadFirst(MessageQueueBase):
    ''' Poll for new messages in the message queue. '''
    def __init__(self):
        super(MessageQueueReadFirst, self).__init__(op='req', poll_attrs='')


class MessageQueueRemoveFirst(MessageQueueBase):
    ''' Remove the first message in the message queue. '''
    def __init__(self, msgid):
        super(MessageQueueRemoveFirst, self).__init__(
            op='ack', poll_attrs=(' msgID="%s"' % msgid))


class ContactCheck(Command):
    template = u'''<check>
        <contact:check xmlns:contact="urn:ietf:params:xml:ns:contact-1.0">
            <contact:id>{handle}</contact:id>
        </contact:check>
    </check>'''


class ContactCreateUpdateBase(Command):
    # SIDN supports exactly one postalInfo and only type loc.
    template = u'''<{__cmd__}>
        <contact:{__cmd__} xmlns:contact="urn:ietf:params:xml:ns:contact-1.0">
            <contact:id>{handle}</contact:id>
            {__beginchg__}
            <contact:postalInfo type="loc">
                <contact:name>{name}</contact:name>
                <!--<contact:org>afdeling communicatie</contact:org>-->
                <contact:addr>
                    <!-- Door SIDN is hier een minimum van een op
                    gezet. In de eerste street tag mag geen
                    postbus opgenomen worden. -->
                    <contact:street>{street}</contact:street>
                    <contact:street>{housenr}</contact:street>
                    <contact:city>{city}</contact:city>
                    <contact:pc>{zipcode}</contact:pc>
                    <contact:cc>{countrycode}</contact:cc>
                </contact:addr>
            </contact:postalInfo>
            <contact:voice>{phone}</contact:voice>
            <contact:fax>{fax}</contact:fax><!-- opt -->
            <contact:email>{email}</contact:email>
            <contact:authInfo><contact:pw>UNUSED_BY_SIDN</contact:pw></contact:authInfo>
            {__endchg__}
        </contact:{__cmd__}>
    </{__cmd__}>
    {legalform_xml}
    '''

    def __init__(self, legalform=None, legalformno=None, **kwargs):
        if kwargs['__cmd__'] == 'create':
            if legalform is not None:
                assert legalform in (
                    'BGG BRO BV BVI/O COOP CV EENMANSZAAK EESV KERK '
                    'MAATSCHAP NV OWM PERSOON REDR STICHTING '
                    'VERENIGING VOF'.split())
                assert legalformno is not None
                legalform_xml = (
                    '<sidn-ext-epp:legalForm>%s</sidn-ext-epp:legalForm>'
                    '<sidn-ext-epp:legalFormRegNo>%s</sidn-ext-epp:legalFormRegNo>' % (
                        legalform, legalformno))
            else:
                legalform_xml = '<sidn-ext-epp:legalForm>ANDERS</sidn-ext-epp:legalForm>'
            kwargs['legalform_xml'] = ('''
                <extension>
                    <sidn-ext-epp:ext xmlns:sidn-ext-epp="http://rxsd.my-domain-registry.nl/sidn-ext-epp-1.0">
                        <sidn-ext-epp:create>
                            <sidn-ext-epp:contact>
                                {legalform_xml}
                            </sidn-ext-epp:contact>
                        </sidn-ext-epp:create>
                    </sidn-ext-epp:ext>
                </extension>
            ''').format(legalform_xml=legalform_xml)

        # SIDN MUST have a dot in the phone#
        if 'phone' in kwargs:
            kwargs['phone'] = self.sidnify_phonenumber(kwargs['phone'])
        if 'fax' in kwargs:
            kwargs['fax'] = self.sidnify_phonenumber(kwargs['fax'])
        super(Command, self).__init__(**kwargs)

    def sidnify_phonenumber(self, phonenumber):
        if phonenumber is None or phonenumber.strip() == '':
            return ''
        phonenumber = phonenumber.strip()
        if phonenumber[0:2] == '00':
            phonenumber = '+%s' % phonenumber[2:]
        if phonenumber[0] == '0':
            phonenumber = '+31%s' % phonenumber[1:]  # SIDN is Dutch
        phonenumber = phonenumber.replace('-', '.').replace(' ', '.')
        assert phonenumber[0] == '+' and all(i in '0123456789.' for i in phonenumber[1:])
        tmp = phonenumber.split('.', 1)
        if len(tmp) == 2:
            phonenumber = '%s.%s' % (tmp[0], tmp[1].replace('.', ''))
        else:  # for +31 and +46 this works, for +376 it becomes +37.6, but who cares
            phonenumber = '%s.%s' % (phonenumber[0:3], phonenumber[3:])
        return phonenumber


class ContactCreate(ContactCreateUpdateBase):
    def __init__(self, **kwargs):
        super(ContactCreate, self).__init__(__cmd__='create', __beginchg__='', __endchg__='', handle='UNUSED_BY_SIDN', **kwargs)


class ContactDelete(Command):
    template = u'''<delete>
        <contact:delete xmlns:contact="urn:ietf:params:xml:ns:contact-1.0">
            <contact:id>{handle}</contact:id>
        </contact:delete>
    </delete>'''


class ContactInfo(Command):
    template = u'''<info>
        <contact:info xmlns:contact="urn:ietf:params:xml:ns:contact-1.0">
            <contact:id>{handle}</contact:id>
        </contact:info>
    </info>'''


class ContactUpdate(ContactCreateUpdateBase):
    def __init__(self, **kwargs):
        super(ContactUpdate, self).__init__(__cmd__='update', __beginchg__='<contact:chg>', __endchg__='</contact:chg>', **kwargs)


class DomainCheck(Command):
    ''' Query availability of a (or multiple) domain(s). '''
    template = u'''<check>
        <domain:check xmlns:domain="urn:ietf:params:xml:ns:domain-1.0">
            <!-- TODO: allow multiple names here.. -->
            <domain:name>{domainname}</domain:name>
        </domain:check>
    </check>'''


class DomainCreate(Command):
    ''' Create a new domain. '''
    template = u'''<create>
        <domain:create xmlns:domain="urn:ietf:params:xml:ns:domain-1.0">
            <domain:name>{domainname}</domain:name>
            {__custom__}
            <domain:authInfo><domain:pw>OVERRIDDEN_BY_SIDN</domain:pw></domain:authInfo>
        </domain:create>
    </create>'''

    def __init__(self, *args, **kwargs):
        # Note that SIDN wants 1 registrar, 1 admin and 1+ tech.
        super(DomainCreate, self).__init__(*args, **kwargs)
        self.add_list = []
        self.ns_list = []
        self.registrant = None

    def add_nameserver(self, nameserver):
        self.ns_list.append('<domain:hostObj>%s</domain:hostObj>' % nameserver)
        return self

    def add_admin(self, handle):
        self.add_list.append('<domain:contact type="admin">%s</domain:contact>' % handle)
        return self

    def add_tech(self, handle):
        self.add_list.append('<domain:contact type="tech">%s</domain:contact>' % handle)
        return self

    def set_registrant(self, handle):
        assert self.registrant is None
        self.registrant = handle
        return self

    def _get_custom(self):
        custom = []

        if self.ns_list:
            custom.append('<domain:ns>%s</domain:ns>' % ''.join(self.ns_list))
        if self.registrant is not None:
            custom.append('<domain:registrant>%s</domain:registrant>' % self.registrant)
        custom.extend(self.add_list)

        return super(DomainCreate, self)._get_custom() + ''.join(custom)


class DomainDelete(Command):
    ''' Delete a domain. '''
    template = u'''<delete>
        <domain:delete xmlns:domain="urn:ietf:params:xml:ns:domain-1.0">
            <domain:name>{domainname}</domain:name>
        </domain:delete>
    </delete>'''


class DomainDeleteCancel(Base):
    ''' Undelete a domain (within a certain period of time). '''
    template = u'''<extension>
        <sidn-ext-epp:command xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:sidn-ext-epp="http://rxsd.my-domain-registry.nl/sidn-ext-epp-1.0">
            <sidn-ext-epp:domainCancelDelete>
                <sidn-ext-epp:name>{domainname}</sidn-ext-epp:name>
            </sidn-ext-epp:domainCancelDelete>
            <!--<sidn-ext-epp:clTRID>OMVDC10T10</sidn-ext-epp:clTRID>-->
        </sidn-ext-epp:command>
    </extension>'''


class DomainInfo(Command):
    ''' Query info about an owned domain. '''
    # XXX: hosts attrib can be in (all, none, del, sub), what do they do?
    template = u'''<info>
        <domain:info xmlns:domain="urn:ietf:params:xml:ns:domain-1.0">
            <domain:name hosts="all">{domainname}</domain:name>
        </domain:info>
    </info>'''


class DomainUpdate(Command):
    ''' Update domain info. '''
    template = u'''<update>
        <domain:update xmlns:domain="urn:ietf:params:xml:ns:domain-1.0">
            <domain:name>{domainname}</domain:name>
            {__custom__}
        </domain:update>
    </update>
    {__extension__}'''

    def __init__(self, *args, **kwargs):
        super(DomainUpdate, self).__init__(*args, **kwargs)
        self.add_list = []
        self.add_ns_list = []
        self.rem_list = []
        self.rem_ns_list = []
        self.chg_list = []

    def add_nameserver(self, nameserver):
        self.add_ns_list.append('<domain:hostObj>%s</domain:hostObj>' % nameserver)
        return self

    def remove_nameserver(self, nameserver):
        self.rem_ns_list.append('<domain:hostObj>%s</domain:hostObj>' % nameserver)
        return self

    def add_admin(self, handle):
        # Could be called change_admin by a higher level function, as
        # SIDN wants exactly one admin always.
        self.add_list.append('<domain:contact type="admin">%s</domain:contact>' % handle)
        return self

    def remove_admin(self, handle):
        self.rem_list.append('<domain:contact type="admin">%s</domain:contact>' % handle)
        return self

    def add_tech(self, handle):
        self.add_list.append('<domain:contact type="tech">%s</domain:contact>' % handle)
        return self

    def remove_tech(self, handle):
        self.rem_list.append('<domain:contact type="tech">%s</domain:contact>' % handle)
        return self

    def change_registrant(self, handle):
        assert len(self.chg_list) == 0
        self.chg_list.append('<domain:registrant>%s</domain:registrant>' % handle)
        return self

    def _get_custom(self):
        custom = []

        add_list = self.add_list[:]
        if self.add_ns_list:
            add_list.append('<domain:ns>%s</domain:ns>' % ''.join(self.add_ns_list))
        if add_list:
            custom.append('<domain:add>%s</domain:add>' % ''.join(add_list))

        rem_list = self.rem_list[:]
        if self.rem_ns_list:
            rem_list.append('<domain:ns>%s</domain:ns>' % ''.join(self.rem_ns_list))
        if rem_list:
            custom.append('<domain:rem>%s</domain:rem>' % ''.join(rem_list))

        if self.chg_list:
            custom.append('<domain:chg>%s</domain:chg>' % ''.join(self.chg_list))

        self.variables['__extension__'] = self._get_extension()
        return super(DomainUpdate, self)._get_custom() + ''.join(custom)

    def _get_extension(self):
        return ''


class DnssecDomainUpdate(DomainUpdate):
    """
    <extension>
      <secDNS:update xmlns:secDNS="urn:ietf:params:xml:ns:secDNS-1.1">
        <secDNS:rem>
          <secDNS:keyData>
            <secDNS:flags>257</secDNS:flags>
            <secDNS:protocol>3</secDNS:protocol>
            <secDNS:alg>1</secDNS:alg>
            <secDNS:pubKey>AQPJ////4QQQ</secDNS:pubKey>
          </secDNS:keyData>
        </secDNS:rem>
        <secDNS:add>
          <secDNS:keyData>
            <secDNS:flags>257</secDNS:flags>
            <secDNS:protocol>3</secDNS:protocol>
            <secDNS:alg>1</secDNS:alg>
            <secDNS:pubKey>AQPJ////4Q==</secDNS:pubKey>
          </secDNS:keyData>
        </secDNS:add>
      </secDNS:update>
    </extension>
    """
    def __init__(self, *args, **kwargs):
        super(DnssecDomainUpdate, self).__init__(*args, **kwargs)
        self.dnskey_add_list = []
        self.dnskey_remove_list = []

    def dnskey_add(self, flags, proto, algo, pubkey):
        self.dnskey_add_list.append((flags, proto, algo, pubkey))

    def dnskey_remove(self, flags, proto, algo, pubkey):
        self.dnskey_remove_list.append((flags, proto, algo, pubkey))

    def _get_extension(self):
        custom = []

        if self.dnskey_add_list or self.dnskey_remove_list:
            custom.append('<extension>')
            custom.append('<secDNS:update xmlns:secDNS="urn:ietf:params:xml:ns:secDNS-1.1">')
            # custom.append('<secDNS:rem><secDNS:all>true</secDNS:all></secDNS:rem>')
            for remove in self.dnskey_remove_list:
                custom.append('<secDNS:rem><secDNS:keyData>')
                custom.append(
                    '<secDNS:flags>%d</secDNS:flags><secDNS:protocol>%d</secDNS:protocol>'
                    '<secDNS:alg>%d</secDNS:alg><secDNS:pubKey>%s</secDNS:pubKey>' % remove)
                custom.append('</secDNS:keyData></secDNS:rem>')
            for add in self.dnskey_add_list:
                custom.append('<secDNS:add><secDNS:keyData>')
                custom.append(
                    '<secDNS:flags>%d</secDNS:flags><secDNS:protocol>%d</secDNS:protocol>'
                    '<secDNS:alg>%d</secDNS:alg><secDNS:pubKey>%s</secDNS:pubKey>' % add)
                custom.append('</secDNS:keyData></secDNS:add>')
            custom.append('</secDNS:update>')
            custom.append('</extension>')

        return ''.join(custom)


class DomainTransferBase(Command):
    ''' Do various domain transfer operations. '''
    template = u'''<transfer op="{op}">
        <domain:transfer xmlns:domain="urn:ietf:params:xml:ns:domain-1.0">
            <domain:name>{domainname}</domain:name>
            {transfer_xml}
        </domain:transfer>
    </transfer>'''


class DomainTransfer(DomainTransferBase):
    ''' Request transfer of a domain. '''
    def __init__(self, domainname, token):
        super(DomainTransfer, self).__init__(
            domainname=domainname, op='request', transfer_xml=(
                ('<domain:authInfo><domain:pw>%s</domain:pw>'
                 '</domain:authInfo>' % token)))


class DomainTransferApprove(DomainTransferBase):
    ''' Approve an away transfer. '''
    def __init__(self, domainname):
        super(DomainTransferApprove, self).__init__(domainname=domainname, op='approve')


class DomainTransferCancel(DomainTransferBase):
    ''' Cancel a domain transfer (to self). '''
    def __init__(self, domainname):
        super(DomainTransferCancel, self).__init__(domainname=domainname, op='cancel')


class DomainTransferState(DomainTransferBase):
    ''' Query transfer state of a domain. '''
    def __init__(self, domainname):
        super(DomainTransferState, self).__init__(domainname=domainname, op='query')


class HostCheck(Command):
    pass  # FIXME: not implemented


class HostCreate(Command):
    pass  # FIXME: not implemented


class HostDelete(Command):
    pass  # FIXME: not implemented


class HostInfo(Command):
    pass  # FIXME: not implemented


class HostUpdate(Command):
    pass  # FIXME: not implemented


def main():
    import eppsocket
    import eppxml
    xml = eppxml.wrap_socket(eppsocket.tcp_connect('testdrs.my-domain-registry.nl'))
    try:
        xml.expect(None, '/epp:epp/epp:greeting')
        xml.expect(Login(username='123456', password='aaaaaaaaaa'), XPATH_OK)
        x = xml.expect(ContactCheck(handle='DOE001234-ADMIN'), XPATH_OK)
        print(eppxml.pp(x))
        x = xml.expect(ContactInfo(handle='DOE001234-ADMIN'), XPATH_OK)
        print(eppxml.pp(x))
        # xml.expect(DomainInfo(domainname='now-power.nl'), 'abc')
        # create_cmd = DomainCreate(domainname='now-power.nl').add_nameserver('ns1.example.nl').set_registrant('DOE001234-REGIS').add_admin('DOE001234-ADMIN').add_tech('DOE001234-TECHC')
        # xml.expect(create_cmd, XPATH_OK)
        # x = xml.expect(DomainCheck(domainname='ditdomeinisvastvrij.nl'), XPATH_OK)
        # print eppxml.pp(x)
        # x = xml.expect(DomainCheck(domainname='example.nl'), XPATH_OK)
        # print eppxml.pp(x)
        # cmd = DomainUpdate(domainname='now-power.nl').add_nameserver('ns3.example.nl')
        # x = xml.expect(cmd, XPATH_OK)
        # print eppxml.pp(x)
        # x = xml.expect(DomainInfo(domainname='google.nl'), XPATH_OK)
        # x = xml.expect(DomainInfo(domainname='nu.nl'), XPATH_OK)
    except eppxml.UnexpectedData as e:
        print('== ERROR ==')
        print(e)
        print()
        print('== SENT ==')
        print(eppxml.pp(e.output))
        print('== RECEIVED ==')
        print(eppxml.pp(e.input))
    finally:
        xml.expect(Logout(), '/epp:epp/epp:response/epp:result[@code="1500"]')

    xml.close()


if __name__ == '__main__':
    main()
