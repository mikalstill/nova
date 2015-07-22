# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
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

"""Starter script for Nova Compute."""

import sys
import threading
import time
import traceback

from flask import Flask
from flask import Response
from oslo_config import cfg
from oslo_log import log as logging

from nova.conductor import rpcapi as conductor_rpcapi
from nova import config
from nova import counters
import nova.db.api
from nova import exception
from nova.i18n import _LE
from nova import objects
from nova.objects import base as objects_base
from nova.openstack.common.report import guru_meditation_report as gmr
from nova import service
from nova import utils
from nova import version

CONF = cfg.CONF
CONF.import_opt('compute_topic', 'nova.compute.rpcapi')
CONF.import_opt('use_local', 'nova.conductor.api', group='conductor')


counters.declare(counters.Value, 'compute.started',
                 'Time the process started', time.time())
counters.declare(counters.Value, 'compute.current_time',
                 'The current time', time.time())


def block_db_access():
    class NoDB(object):
        def __getattr__(self, attr):
            return self

        def __call__(self, *args, **kwargs):
            stacktrace = "".join(traceback.format_stack())
            LOG = logging.getLogger('nova.compute')
            LOG.error(_LE('No db access allowed in nova-compute: %s'),
                      stacktrace)
            raise exception.DBNotAllowed('nova-compute')

    nova.db.api.IMPL = NoDB()


counter_server = Flask(__name__)


@counter_server.route('/')
def counter_root():
    return ""


@counter_server.route('/varz')
def counter_varz():
    counters.counters['compute.current_time'].set(time.time())

    out = []
    for counter in counters.counters:
        out.append('# %s' % counters.help_strings[counter])
        out.append('%s = %s' % (counter, counters.counters[counter].get()))
    out.append('# EOF\n')
    return Response(mimetype='text/plain', response='\n'.join(out))


def counter_runner():
    counter_server.run(port=8080)


def main():
    config.parse_args(sys.argv)
    logging.setup(CONF, 'nova')
    utils.monkey_patch()
    objects.register_all()

    gmr.TextGuruMeditation.setup_autorun(version)
    threading.Thread(target=counter_runner).start()

    if not CONF.conductor.use_local:
        block_db_access()
        objects_base.NovaObject.indirection_api = \
            conductor_rpcapi.ConductorAPI()

    server = service.Service.create(binary='nova-compute',
                                    topic=CONF.compute_topic,
                                    db_allowed=CONF.conductor.use_local)
    service.serve(server)
    service.wait()
