# vim: set ts=8 sw=4 sts=4 et ai:
# Copyright (C) 2011, OSSO B.V., Walter Doekes
from eppcommand import *
from eppxml import pp, xpath, UnexpectedData

# Checking for used commands:
# for x in `sed -e '/^__all/,/^)/!d;/^ *'\''/!d;s/[^A-Za-z0-9 ]//g' eppcommand.py`; do grep -q $x eppsession.py || echo "$x is unused"; done
# > Hello is unused
# > ...

# BUGS/TODO:
# - Host* is not implemented (glue records?)
# - The domain and contact cache is never purged. This is good because
#   we'll have singleton objects. It is bad however because no record
#   is discarded, ever. That could cause a daemon to run out of memory.
# - Add DB for message storage, domain info caching and set_nameserver
#   and set_handles triggers for when a domain has been moved.


class EppSession(object):
    XPATH_OK = '/epp:epp/epp:response/epp:result[@code="1000"]'

    def __init__(self, eppxml_generator, username, password):
        self.cache = {
            'contacts': {},
            'domains': {},
        }
        self.eppxml = None
        self.eppxml_logged_in = False
        self.eppxml_generator = eppxml_generator
        self.username = username
        self.password = password

    def _ensure_connected(self):
        if self.eppxml is None:
            self.eppxml = self.eppxml_generator()
            self.eppxml.expect(None, '/epp:epp/epp:greeting')
            self._login()
            self.eppxml_logged_in = True

    def _ensure_disconnected(self):
        if self.eppxml is not None:
            if self.eppxml_logged_in:
                self._logout()
                self.eppxml_logged_in = False
            self.eppxml.close()
            self.eppxml = None

    def _exec(self, command, expect_response=None):
        if expect_response is None:
            expect_response = self.XPATH_OK
        self._ensure_connected()
        return self.eppxml.expect(command, expect_response)

    def _login(self):
        self.eppxml.expect(Login(username=self.username, password=self.password), self.XPATH_OK)

    def _logout(self):
        self.eppxml.expect(Logout(), '/epp:epp/epp:response/epp:result[@code="1500"]')

    def close(self):
        ''' Call close in your finally block. '''
        self._ensure_disconnected()

    ####################################################################
    # GETTING CONTACTS, DOMAINS AND MESSAGES
    ####################################################################

    def contact(self, handle):
        # NOTE: this will consume infinite memory as we never purge the cache
        if handle not in self.cache['contacts']:
            self.cache['contacts'][handle] = self.Contact(session=self, handle=handle)
        return self.cache['contacts'][handle]

    def contact_create(self, name, street, housenr, zipcode, city, countrycode, phone, fax, email, legalform=None, legalformno=None):
        ''' Create a new contact. '''
        value = self._exec(ContactCreate(
            name=name, street=street, housenr=housenr, zipcode=zipcode,
            city=city, countrycode=countrycode,
            phone=phone, fax=fax, email=email,
            legalform=legalform, legalformno=legalformno
        ))
        handle = xpath(value, '//contact:creData/contact:id')[0].text
        contact = self.contact(handle)
        contact._cache = {} # dirty cache
        return contact

    def contact_is_free(self, handle):
        ''' Check availability of contact handle. No caching is
        performed. '''
        value = self._exec(ContactCheck(handle=handle))
        info = xpath(value, '//contact:chkData/contact:cd/contact:id')[0]
        assert info.text == handle
        return info.attrib['avail'] == 'true'

    def domain(self, domainname):
        # NOTE: this will consume infinite memory as we never purge the cache
        if domainname not in self.cache['domains']:
            self.cache['domains'][domainname] = self.Domain(session=self, domainname=domainname)
        return self.cache['domains'][domainname]

    def domain_create(self, domainname, registrant=None, admin=None, tech=None, nameservers=None):
        ''' Register a new domain name. Supply iterables as parameters.
        Note that SIDN enforces 1 registrant, 1 admin, 1+ tech and 0-13
        nameservers.'''
        assert registrant is not None and admin is not None and tech is not None
        create_cmd = DomainCreate(domainname=domainname)
        for i in set(registrant):
            create_cmd.set_registrant(i)
        for i in set(admin):
            create_cmd.add_admin(i)
        for i in set(tech):
            create_cmd.add_tech(i)
        if nameservers is not None:
            for i in set(nameservers):
                create_cmd.add_nameserver(i)
        self._exec(create_cmd)
        domain = self.domain(domainname)
        domain._cache = {} # dirty cache
        return domain

    def domain_is_free(self, domainname):
        ''' Returns a boolean stating whether the domain is free. No
        caching is performed. '''
        # TODO: add so we can check multiple domains at once
        value = self._exec(DomainCheck(domainname=domainname))
        info = xpath(value, '//domain:chkData/domain:cd/domain:name')[0]
        assert info.text == domainname
        return info.attrib['avail'] == 'true'

    def messages(self, keep=False):
        ''' Poll the EPP server for new messages. '''
        max_messages = 9 # SIDN is very limited (9 or 10??)
        messages = []
        count = 0

        while max_messages > 0:
            max_messages -= 1
            readfirst_cmd = MessageQueueReadFirst()
            value = self._exec(readfirst_cmd, '/epp:epp/epp:response/epp:result[@code]')
            code = xpath(value, '/epp:epp/epp:response/epp:result')[0].attrib['code']
            if code == '1300':
                # Done
                break
            elif code == '1301':
                message_info = xpath(value, '/epp:epp/epp:response/epp:msgQ')[0]
                # FIXME: we should do better parsing here:
                # <sidn-ext-epp:command>domain:transfer-start</sidn-ext-epp:command> and others..
                # In the mean time:
                # 1013: transfer to me in progress
                # 1014: transfer from me in progress
                # 1015: transfer to me complete
                # 1016: transfer from me complete
                messages.append(xpath(value, '/epp:epp/epp:response/epp:msgQ/epp:msg')[0].text)
                count = int(message_info.attrib['count'])
                if keep:
                    break # before we start popping queued messages
                self._exec(MessageQueueRemoveFirst(msgid=message_info.attrib['id'])) # pop message
            else:
                raise UnexpectedData(readfirst_cmd, value, '/epp:epp/epp:response/epp:result[@code] code 1300 or 1301')

        # Increase the list size to the message count
        messages.extend(None for i in range(count - 1))
        return messages

    ####################################################################
    # CONTACT OBJECT BY HANDLE
    ####################################################################

    class Contact(object):
        def __init__(self, session, handle):
            self._cache = {}
            self._session = session
            self._handle = handle

        @property
        def handle(self):
            ''' Contact handle/identifier. '''
            return self._handle

        @property
        def verbose_info(self):
            ''' Verbose contact information. '''
            if 'info' not in self._cache:
                value = self._session._exec(ContactInfo(handle=self._handle))
                self._cache['info'] = value
            return pp(self._cache['info']) # FIXME: return value is not nice

        def __repr__(self):
            return "<EppSession.Contact('%s')>" % self._handle

        def change(self, name, street, housenr, zipcode, city, countrycode, phone, fax, email, legalform=None, legalformno=None):
            ''' Update contact info (everything at once). '''
            self._session._exec(ContactUpdate(handle=self._handle, name=name,
                    street=street, housenr=housenr, zipcode=zipcode, city=city, countrycode=countrycode,
                    phone=phone, fax=fax, email=email, legalform=legalform, legalformno=legalformno))
            self._cache = {}

        def delete(self):
            ''' Delete this contact. '''
            self._session._exec(ContactDelete(handle=self._handle))
            self._cache = {}

    ####################################################################
    # DOMAIN OBJECT BY DOMAINNAME
    ####################################################################

    class Domain(object):
        def __init__(self, session, domainname):
            self._cache = {}
            self._session = session
            self._domainname = domainname

        # PROPERTIES #

        @property
        def name(self):
            ''' Domain name/identifier. '''
            return self._domainname

        @property
        def token(self):
            ''' Domain token for away transfers. '''
            return xpath(self._info(), '//domain:infData/domain:authInfo/domain:pw')[0].text

        @property
        def transfer_info(self):
            ''' Verbose transfer information. '''
            value = self._session._exec(DomainTransferState(domainname=self._domainname))
            return pp(value) # FIXME: this return value is not nice

        @property
        def verbose_info(self):
            ''' Get verbose domain information. '''
            return pp(self._info()) # FIXME: return value is not nice

        # GETTERS/SETTERS #

        def get_handles(self):
            ''' Returns a dictionary with sets of handles. '''
            return {
                'registrant': set(i.text for i in xpath(self._info(), '//domain:infData/domain:registrant')),
                'admin': set(i.text for i in xpath(self._info(), '//domain:infData/domain:contact[@type="admin"]')),
                'tech': set(i.text for i in xpath(self._info(), '//domain:infData/domain:contact[@type="tech"]')),
            }

        def set_handles(self, registrant=None, admin=None, tech=None):
            ''' Supply one or more iterables of registrant, admin or tech.
            Supply None to leave it as-is, supply the empty list to clear
            the handles. Note that SIDN enforces 1 registrant, 1 admin and
            1+ techs. '''
            old = self.get_handles()
            has_edits = False
            update_cmd = DomainUpdate(domainname=self._domainname)

            if registrant is not None:
                new_registrant = set(registrant)
                if old['registrant'] != new_registrant:
                    assert len(new_registrant) == 1
                    has_edits = True
                    for i in new_registrant:
                        update_cmd.change_registrant(i)

            if admin is not None:
                new_admin = set(admin)
                if old['admin'] != new_admin:
                    has_edits = True
                    for i in new_admin.difference(old['admin']):
                        update_cmd.add_admin(i)
                    for i in old['admin'].difference(new_admin):
                        update_cmd.remove_admin(i)

            if tech is not None:
                new_tech = set(tech)
                if old['tech'] != new_tech:
                    has_edits = True
                    for i in new_tech.difference(old['tech']):
                        update_cmd.add_tech(i)
                    for i in old['tech'].difference(new_tech):
                        update_cmd.remove_tech(i)

            if has_edits:
                self._session._exec(update_cmd)
                self._cache = {}

        def get_nameservers(self):
            ''' Returns a set of nameservers. '''
            return set(i.text for i in xpath(self._info(), '//domain:infData/domain:ns')[0].iterchildren())

        def set_nameservers(self, nameservers):
            ''' Supply an iterable of nameservers. '''
            old_nameservers = self.get_nameservers()
            new_nameservers = set(nameservers)
            if not new_nameservers:
                raise AssertionError('fail')
            if old_nameservers != new_nameservers:
                update_cmd = DomainUpdate(domainname=self._domainname)
                for i in new_nameservers.difference(old_nameservers):
                    update_cmd.add_nameserver(i)
                for i in old_nameservers.difference(new_nameservers):
                    update_cmd.remove_nameserver(i)
                self._session._exec(update_cmd)
                self._cache = {}

        # HELPERS #

        def __repr__(self):
            return "<EppSession.Domain('%s')>" % self._domainname

        def _info(self):
            if 'info' not in self._cache:
                self._cache['info'] = self._session._exec(DomainInfo(domainname=self._domainname))
            return self._cache['info']

        # ACTIONS #

        def delete(self):
            ''' Delete this domain. '''
            self._session._exec(DomainDelete(domainname=self._domainname))
            self._cache = {}

        def undelete(self):
            ''' Undelete this domain. '''
            self._session._exec(DomainDeleteCancel(domainname=self._domainname))
            self._cache = {}

        def release(self):
            ''' Approve a domain transfer (away). '''
            self._session._exec(DomainTransferApprove(domainname=self._domainname))
            self._cache = {}

        def transfer(self, token):
            ''' Request a domain transfer (to self). '''
            value = self._session._exec(DomainTransfer(domainname=self._domainname, token=token))
            self._cache = {}
            # FIXME: this return value is not nice
            domainname = xpath(value, '//domain:trnData/domain:name')[0].text
            status = xpath(value, '//domain:trnData/domain:trStatus')[0].text # pending
            activation_date = xpath(value, '//domain:trnData/domain:acDate')[0].text # 2010-05-22T13:49:04.000Z
            svtrid = xpath(value, '//epp:trID/epp:svTRID')[0].text
            return domainname, status, activation_date, svtrid

        def untransfer(self):
            ''' Undo/cancel a domain transfer (to self). '''
            value = self._session._exec(DomainTransferCancel(domainname=self._domainname))

    ####################################################################
    # END OF EPPSESSION
    ####################################################################


def main():
    import eppsocket, eppxml, sys

    tracefile = None
    #tracefile = sys.stderr
    session = EppSession(lambda: eppxml.wrap_socket(eppsocket.tcp_connect('testdrs.my-domain-registry.nl', tracefile=tracefile)), '301234', 'aabbccddee')
    dsession = EppSession(lambda: eppxml.wrap_socket(eppsocket.tcp_connect('testdrs.my-domain-registry.nl', tracefile=tracefile)), '901234', 'aabbccddee')
    try:
        if not session.domain_is_free('nu.nl'):
            domain = session.domain('nu.nl')
        else:
            domain = session.domain_create('nu.nl', registrant=['DOE001234-REGIS'], tech=['DOE001234-TECHC'], admin=['DOE001234-ADMIN'])
            assert not session.domain_is_free('nu.nl')

        print 'now-power.nl token', session.domain('now-power.nl').token
        print 'message queue', session.messages(keep=False)
        assert session.domain_is_free('ditdomeinisvastvrij.nl')
        assert not session.domain_is_free('nu.nl')
        domain = session.domain('nu.nl')
        print 'nu.nl handles', domain.get_handles()
    except eppxml.UnexpectedData, e:
        print '== ERROR =='
        print e
        print
        print '== SENT =='
        print eppxml.pp(e.output)
        print '== RECEIVED =='
        print eppxml.pp(e.input)
    finally:
        session.close()
        dsession.close()


if __name__ == '__main__':
    import sys
    main()
