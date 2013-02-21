# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Rackspace Asia
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import dns.opcode
import socket

from nova import exception
from nova.network import dyndns
from nova import test


def _fake_resolver_query(lookup):
    if lookup == 'dns.bunyip.example.com':
        return (['8.8.8.8', '4.4.4.4'], None, None)

    if lookup == '8.8.8.8':
        return (['8.8.8.8'], None, None)

    raise Exception('Unprimed query %s' % lookup)


_queries = []


def _fake_query_tcp(packet, destination):
    _queries.append((packet, destination))


class DynamicDNSTestCase(test.TestCase):
    def setUp(self):
        super(DynamicDNSTestCase, self).setUp()
        self.flags(dynamic_dns_domains='bunyip.example.com',
                   dynamic_dns_server='dns.bunyip.example.com',
                   dynamic_dns_key_name='keyname',
                   dynamic_dns_key_algorithm='hmac-sha1',
                   dynamic_dns_secret='Wr1784mFhyTP9nqXIkWpRw==')

        self.stubs.Set(dns.query, 'tcp', _fake_query_tcp)

    def test_init(self):
        d = dyndns.DynamicDNS()
        self.assertEqual(1, len(d.keyring))

    def test_init_server_is_ip(self):
        self.flags(dynamic_dns_server='8.8.8.8')
        d = dyndns.DynamicDNS()
        self.assertEqual(1, len(d.keyring))

    def test_get_domains(self):
        d = dyndns.DynamicDNS()
        self.assertEqual('bunyip.example.com', d.get_domains())

    def test_create_entry_unmanaged_domain(self):
        d = dyndns.DynamicDNS()
        self.assertRaises(exception.DomainIncorrect, d.create_entry, 'foo',
                          '192.168.1.1', 'A', 'banana.example.com')

    def test_create_entry(self):
        global _queries
        _queries = []

        d = dyndns.DynamicDNS()
        d.create_entry('foo', '192.168.1.1', 'A', 'bunyip.example.com')
        self.assertEqual(2, len(_queries))

        self.assertEqual(dns.opcode.UPDATE, _queries[0][0].opcode())
        self.assertEqual(1, len(_queries[0][0].question))
        self.assertEqual('bunyip.example.com. IN SOA',
                         _queries[0][0].question[0].to_text())
        self.assertEqual(2, len(_queries[0][0].authority))
        self.assertEqual('foo ANY A', _queries[0][0].authority[0].to_text())
        self.assertEqual('foo 300 IN A 192.168.1.1',
                         _queries[0][0].authority[1].to_text())
        self.assertEqual('dns.bunyip.example.com', _queries[0][1])

        self.assertEqual(dns.opcode.UPDATE, _queries[1][0].opcode())
        self.assertEqual(1, len(_queries[1][0].question))
        self.assertEqual('1.168.192.in-addr.arpa. IN SOA',
                         _queries[1][0].question[0].to_text())
        self.assertEqual(2, len(_queries[1][0].authority))
        self.assertEqual('1 ANY PTR', _queries[1][0].authority[0].to_text())
        self.assertEqual('1 300 IN PTR foo.bunyip.example.com.',
                         _queries[1][0].authority[1].to_text())
        self.assertEqual('dns.bunyip.example.com', _queries[1][1])

    def test_delete_entry(self):
        global _queries
        _queries = []

        def fake_get_entries_by_name(name, domain):
            return ['1.2.3.4']

        d = dyndns.DynamicDNS()
        d.get_entries_by_name = fake_get_entries_by_name

        d.delete_entry('foo', 'bunyip.example.com')
        self.assertEqual(2, len(_queries))

        self.assertEqual(dns.opcode.UPDATE, _queries[0][0].opcode())
        self.assertEqual(1, len(_queries[0][0].question))
        self.assertEqual('bunyip.example.com. IN SOA',
                         _queries[0][0].question[0].to_text())
        self.assertEqual(1, len(_queries[0][0].authority))
        self.assertEqual('foo ANY ANY', _queries[0][0].authority[0].to_text())
        self.assertEqual('dns.bunyip.example.com', _queries[0][1])

        self.assertEqual(dns.opcode.UPDATE, _queries[1][0].opcode())
        self.assertEqual(1, len(_queries[1][0].question))
        self.assertEqual('3.2.1.in-addr.arpa. IN SOA',
                         _queries[1][0].question[0].to_text())
        self.assertEqual(1, len(_queries[1][0].authority))
        self.assertEqual('4 ANY ANY', _queries[1][0].authority[0].to_text())
        self.assertEqual('dns.bunyip.example.com', _queries[1][1])

    def test_get_entries_by_address(self):
        def fake_gethostbyaddr(addr):
            return (['foo.bunyip.example.com'], None, None)
        self.stubs.Set(socket, 'gethostbyaddr', fake_gethostbyaddr)

        d = dyndns.DynamicDNS()
        self.assertEqual(['foo.bunyip.example.com'],
                         d.get_entries_by_address('8.8.8.8',
                                                  'bunyip.example.com'))

    def test_get_entries_by_name(self):
        def fake_getaddrinfo(name, port):
            return [(None, None, None, None, ('8.8.8.8', None))]
        self.stubs.Set(socket, 'getaddrinfo', fake_getaddrinfo)

        d = dyndns.DynamicDNS()
        self.assertEqual(['8.8.8.8'],
                         d.get_entries_by_name('foo', 'bunyip.example.com'))
