earlyepp
========

Very unpolished/old Python EPP CLI client, tested against SIDN only.

This is old code, created back in 2011.


TODO
----

Packaging for BOSSO?



DNSSEC TODO
-----------

Stuff for DNSSEC::

    # info
    <extension>
      <secDNS:infData xmlns:secDNS="urn:ietf:params:xml:ns:secDNS-1.1">
        <secDNS:keyData>
          <secDNS:flags>257</secDNS:flags>
          <secDNS:protocol>3</secDNS:protocol>
          <secDNS:alg>1</secDNS:alg>
          <secDNS:pubKey>AQPJ////4Q==</secDNS:pubKey>
        </secDNS:keyData>
      </secDNS:infData>
    </extension>

    # create
    <extension>
      <secDNS:create xmlns:secDNS="urn:ietf:params:xml:ns:secDNS-1.1">
        <secDNS:keyData>
          <secDNS:flags>257</secDNS:flags>
          <secDNS:protocol>3</secDNS:protocol>
          <secDNS:alg>8</secDNS:alg>
          <secDNS:pubKey>AQPJ////4Q==</secDNS:pubKey>
        </secDNS:keyData>
      </secDNS:create>
    </extension>

    # update
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

See also:

* http://dnsviz.net/d/sidn.nl/dnssec/
* http://www.iana.org/assignments/dns-sec-alg-numbers/dns-sec-alg-numbers.xhtml
* dig -t DNSKEY|NS HOST +dnssec +multiline [@nl-server]
