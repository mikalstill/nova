# Copyright 2019 Aptira Pty Ltd
# All Rights Reserved.
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

import os
import requests
import sys
import types

from oslo_log import log as logging

import nova.conf

CONF = nova.conf.CONF

LOG = logging.getLogger(__name__)


_METRICS = None


def save(kind, name, value):
    global _METRICS
    if not _METRICS:
        _METRICS = {}
    _METRICS[name] = (kind, value)
    


def increment_counter(name):
    global _METRICS
    if not _METRICS:
        _METRICS = {}
    kind, value = _METRICS.get(name, ('counter', 0))
    _METRICS[name] = (kind, value + 1)


def publish():
    global _METRICS
    if not _METRICS:
        _METRICS = {}

    subst = {'push_gateway': CONF.metrics.push_gateway,
             'job': os.path.basename(sys.argv[0])}
    url = 'http://%(push_gateway)s/metrics/job/%(job)s/' % subst
    data = []

    for metric in _METRICS:
        kind, value = _METRICS[metric]
        if type(value) == types.DictType:
            vals = []
            for key in value:
                vals.append('%(metric)s{%(key)s} %(value)s'
                            % {'metric': metric,
                               'key': key,
                               'value': value[key]})
            value = '\n'.join(vals)
            data.append('# TYPE %(metric)s %(type)s\n%(value)s\n'
                        % {'metric': metric,
                           'type': kind,
                           'value': value})

        else:
            data.append('# TYPE %(metric)s %(type)s\n%(metric)s %(value)s\n'
                        % {'metric': metric,
                           'type': kind,
                           'value': value})

    LOG.debug('Pushing to %s data %s', url, data)

    r = requests.post(url,
                      data='\n'.join(data),
                      headers={'X-Requested-With': 'OpenStack',
                               'Content-type': 'text/xml'},
                      timeout=1)
    LOG.debug('Push result: status = %d, message = %s',
              r.status_code, r.text)
