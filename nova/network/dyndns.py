# Copyright 2013 Rackspace Asia
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import dns.query
import dns.reversename
import dns.tsigkeyring
import dns.update
import socket

from oslo.config import cfg

from nova import exception
from nova.network import dns_driver
from nova.openstack.common import log as logging

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

dynamic_dns_opts = [
    # TODO(mikal): this really should be derived from a call to conductor to
    # find out what domains are configured in the database.
    cfg.ListOpt('dynamic_dns_domains',
               default='',
               help='A list of domains we are willing to send updates for'),
    cfg.StrOpt('dynamic_dns_server',
               default='',
               help='Server to send dynamic DNS updates to'),
    cfg.StrOpt('dynamic_dns_key_name',
               default='',
               help='The name of the DNS key to use for a TSIG update'),
    cfg.StrOpt('dynamic_dns_key_algorithm',
               default='hmac-sha1',
               help='The algorithm used to generate the DNS key'),
    cfg.StrOpt('dynamic_dns_secret',
               default='',
               help='The value of the DNS key'),
    cfg.IntOpt('dynamic_dns_ttl',
               default=300,
               help=('The TTL to use for DNS entries')),
    cfg.BoolOpt('dynamic_dns_create_reverse',
                default=True,
                help=('Create reverse DNS entries as well')),
    ]

CONF.register_opts(dynamic_dns_opts)


class DynamicDNS(dns_driver.DNSDriver):
    """Driver for dynamic DNS updates to something like bind."""

    def __init__(self):
        self.keyring = dns.tsigkeyring.from_text({
                CONF.dynamic_dns_key_name: CONF.dynamic_dns_secret
                })

    def _check_request(self, domain):
        if domain not in CONF.dynamic_dns_domains:
            raise exception.DomainIncorrect(
                domain=domain, domainlist=CONF.dynamic_dns_domains)

    def _make_update(self, domain):
        return dns.update.Update(domain,
                                 keyring=self.keyring,
                                 keyalgorithm=CONF.dynamic_dns_key_algorithm)

    def get_domains(self):
        return CONF.dynamic_dns_domains

    def create_entry(self, name, address, record_type, domain):
        LOG.audit(_('Updating the DNS entry for %(name)s in %(domain)s to '
                    '%(type)s %(address)s'),
                  {'name': name,
                   'domain': domain,
                   'type': record_type,
                   'address': address})

        self._check_request(domain)
        update = self._make_update(domain)
        update.replace(name, CONF.dynamic_dns_ttl, record_type, str(address))
        response = dns.query.tcp(update, CONF.dynamic_dns_server)

        if CONF.dynamic_dns_create_reverse:
            fqdn = '%s.%s.' % (name, domain)
            name = str(dns.reversename.from_address(str(address)))

            domain = '.'.join(name.split('.')[1:])
            name = name.split('.')[0]
            record_type = 'PTR'
            address = fqdn

            LOG.audit(_('Updating the DNS entry for %(name)s in %(domain)s to '
                        '%(type)s %(address)s'),
                      {'name': name,
                       'domain': domain,
                       'type': record_type,
                       'address': address})

            update = self._make_update(domain)
            update.replace(name, CONF.dynamic_dns_ttl, record_type,
                           str(address))
            response = dns.query.tcp(update, CONF.dynamic_dns_server)

    def delete_entry(self, name, domain):
        name = name.split('.')[0]
        LOG.audit(_('Deleting the DNS entry for %(name)s in %(domain)s'),
                  {'name': name,
                   'domain': domain})
        self._check_request(domain)

        update = self._make_update(domain)
        update.delete(name)
        response = dns.query.tcp(update, CONF.dynamic_dns_server)

        if CONF.dynamic_dns_create_reverse:
            for n in self.get_entries_by_name(name, domain):
                name = str(dns.reversename.from_address(str(n)))

                domain = '.'.join(name.split('.')[1:])
                name = name.split('.')[0]

                LOG.audit(_('Deleting the DNS entry for %(name)s in '
                            '%(domain)s'),
                          {'name': name,
                           'domain': domain})

                update = self._make_update(domain)
                update.delete(name)
                response = dns.query.tcp(update, CONF.dynamic_dns_server)

    def get_entries_by_address(self, address, domain):
        # NOTE(mikal): we make the assumption that the host resolver here
        # knows how to resolve the dynamic domain.
        (hostname, _, _) = socket.gethostbyaddr(address)
        return hostname

    def get_entries_by_name(self, name, domain):
        # NOTE(mikal): we make the assumption that the host resolver here
        # knows how to resolve the dynamic domain.
        addrs = []

        try:
            for retval in socket.getaddrinfo('%s.%s' % (name, domain), None):
                (_, _, _, _, (addr, port)) = retval
                addrs.append(addr)
        except socket.gaierror:
            # gaierror: (-5, 'No address associated with hostname')
            pass

        return addrs

    def modify_address(self, name, address, domain):
        self.create_entry(name, address, 'A', domain)

    def create_domain(self, domain):
        LOG.audit(_('We do not create domains yet. We are assuming %(domain)s '
                    'already exists.'), {'domain': domain})

    def delete_domain(self, domain):
        LOG.audit(_('We do not delete domains yet. We are assuming %(domain)s '
                    'already exists.'), {'domain': domain})

    def delete_dns_file(self):
        LOG.warn(_("This shouldn't be getting called except during testing."))
        pass
