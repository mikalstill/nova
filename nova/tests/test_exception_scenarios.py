# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Rackspace Australia
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

import inspect

from nova import exception
from nova import test
from testscenarios import load_tests_apply_scenarios as load_tests


def all_exceptions():
    found = []
    for name, obj in inspect.getmembers(exception):
        if name in ['NovaException', 'InstanceFaultRollback']:
            continue

        if not inspect.isclass(obj):
            continue

        if not issubclass(obj, exception.NovaException):
            continue

        found.append((name, {'exception_name': name,
                             'exception_object': obj}))
    return found

    
class ExceptionObjectTestCase(WithScenarios, test.NoDBTestCase):
    scenarios = all_exceptions()

    def test_message(self):
        self.assertNotEqual(self.exception_object.msg_fmt,
                            'An unknown exception occurred.',
                            ('Exception %s uses the default format string'
                             % self.exception_name))
