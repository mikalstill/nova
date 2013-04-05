# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Why do we need this? If you have dnspython in your environment, eventlet
# monkeypatches getaddrinfo() with a greendns call which isn't ipv6 aware.
# You can turn off the monkey patch, but it involves setting an environment
# variable before eventlet is loaded. Hence a loader.

import os
import sys

# NOTE(mikal): All of this is because if dnspython is present in your
# environment then eventlet monkeypatches socket.getaddrinfo() with an
# implementation which doesn't work for IPv6. What we're checking here is
# that the magic environment variable was set when the import happened.
if 'eventlet' in sys.modules and not os.environ.get('EVENTLET_NO_GREENDNS'):
    raise ImportError('eventlet imported before nova.wrapeventlet '
                      '(env var set to %s)'
                      % os.environ.get('EVENTLET_NO_GREENDNS'))

os.environ['EVENTLET_NO_GREENDNS'] = 'yes'

import eventlet

eventlet.monkey_patch(os=False)
