# Copyright 2015 Rackspace Australia
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

"""Provide monitoring counters."""

import time


counters = {}
help_strings = {}


def declare(counter_type, stable_name, help_string, initial_value=0):
    global counters
    counters[stable_name] = counter_type(stable_name, help_string,
                                         initial_value)


class Value(object):
    def __init__(self, name, help_string, initial_value):
        global help_strings
        self.name = name
        self.value = initial_value
        help_strings[name] = help_string

    def set(self, value):
        self.value = value

    def get(self):
        return self.value


class AccumulatingCounter(Value):
    def accumulate(self, additional):
        self.set(self.get() + additional)


class AccumulatingTimer(AccumulatingCounter):
    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exctype, excval, exctb):
        if exctype is not None:
            # NOTE(mikal): this means we're being cleaned up because an
            # exception was thrown. All bets are off now, and we should not
            # swallow the exception
            return False

        self.accumulate(time.time() - self.start_time)


class IncrementingCounter(AccumulatingCounter):
    def increment(self):
        self.accumulate(1)
