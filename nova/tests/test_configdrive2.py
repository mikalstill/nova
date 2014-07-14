# Copyright 2012 Michael Still and Canonical Inc
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
import tempfile

import mox
from oslo.config import cfg

from nova.compute import api as compute_api
from nova import context
from nova import db
from nova.openstack.common import fileutils
from nova import test
import nova.tests.image.fake as fake_image
from nova import utils
from nova.virt import configdrive

CONF = cfg.CONF


class FakeInstanceMD(object):
    def metadata_for_config_drive(self):
        yield ('this/is/a/path/hello', 'This is some content')


class ConfigDriveTestCase(test.NoDBTestCase):

    def test_create_configdrive_iso(self):
        CONF.set_override('config_drive_format', 'iso9660')
        imagefile = None

        try:
            self.mox.StubOutWithMock(utils, 'execute')

            utils.execute('genisoimage', '-o', mox.IgnoreArg(), '-ldots',
                          '-allow-lowercase', '-allow-multidot', '-l',
                          '-publisher', mox.IgnoreArg(), '-quiet', '-J', '-r',
                          '-V', 'config-2', mox.IgnoreArg(), attempts=1,
                          run_as_root=False).AndReturn(None)

            self.mox.ReplayAll()

            with configdrive.ConfigDriveBuilder(FakeInstanceMD()) as c:
                (fd, imagefile) = tempfile.mkstemp(prefix='cd_iso_')
                os.close(fd)
                c.make_drive(imagefile)

        finally:
            if imagefile:
                fileutils.delete_if_exists(imagefile)

    def test_create_configdrive_vfat(self):
        CONF.set_override('config_drive_format', 'vfat')
        imagefile = None
        try:
            self.mox.StubOutWithMock(utils, 'mkfs')
            self.mox.StubOutWithMock(utils, 'execute')
            self.mox.StubOutWithMock(utils, 'trycmd')

            utils.mkfs('vfat', mox.IgnoreArg(),
                       label='config-2').AndReturn(None)
            utils.trycmd('mount', '-o', mox.IgnoreArg(), mox.IgnoreArg(),
                         mox.IgnoreArg(),
                         run_as_root=True).AndReturn((None, None))
            utils.execute('umount', mox.IgnoreArg(),
                          run_as_root=True).AndReturn(None)

            self.mox.ReplayAll()

            with configdrive.ConfigDriveBuilder(FakeInstanceMD()) as c:
                (fd, imagefile) = tempfile.mkstemp(prefix='cd_vfat_')
                os.close(fd)
                c.make_drive(imagefile)

            # NOTE(mikal): we can't check for a VFAT output here because the
            # filesystem creation stuff has been mocked out because it
            # requires root permissions

        finally:
            if imagefile:
                fileutils.delete_if_exists(imagefile)


class ConfigDriveDbTestCase(test.TestCase):
    IMAGE_FIXTURES = {
        'image_no_config_drive_property': {
            'image_meta': {'name': 'fakemachine', 'size': 0,
                           'disk_format': 'ami', 'status': 'active',
                           'container_format': 'ami'},
        },
        'image_config_drive_optional': {
            'image_meta': {'name': 'fakemachine', 'size': 0,
                           'disk_format': 'ami', 'status': 'active',
                           'container_format': 'ami',
                           'img_config_drive': 'optional'},
        },
        'image_config_drive_mandatory': {
            'image_meta': {'name': 'fakemachine', 'size': 0,
                           'disk_format': 'ami', 'status': 'active',
                           'container_format': 'ami',
                           'img_config_drive': 'mandatory'},
        },
        'image_config_drive_malformed': {
            'image_meta': {'name': 'fakemachine', 'size': 0,
                           'disk_format': 'ami', 'status': 'active',
                           'container_format': 'ami',
                           'img_config_drive': 'pickles_are_yukky'},
        },
    }

    def test_config_drive_required_by_image_property(self):
        # NOTE(mikal): we need a real instance object here because we need to
        # run through _populate_instance_for_create in the compute API for this
        # code to work

        try:
            # Stub out the image service
            fake_image.stub_out_image_service(self.stubs)
            image_service = fake_image.FakeImageService()
            image_service.images.clear()
            for image_id, image_meta in self.IMAGE_FIXTURES.items():
                image_meta = image_meta['image_meta']
                image_meta['id'] = image_id
                image_service.create(None, image_meta)

            # Create a security group
            admin_ctxt = context.get_admin_context()
            db.security_group_create(admin_ctxt,
                                     {'user_id': 'fake',
                                      'project_id': 'fake',
                                      'name': 'testgroup',
                                      'description': 'test group'})

            ca = compute_api.API()
            instance_type = {'id': 1,
                            'flavorid': 1,
                            'name': 'm1.tiny',
                            'memory_mb': 512,
                            'vcpus': 1,
                            'vcpu_weight': None,
                            'root_gb': 1,
                            'ephemeral_gb': 0,
                            'rxtx_factor': 1,
                            'swap': 0,
                            'deleted': 0,
                            'disabled': False,
                            'is_public': True,
                            }

            user_ctxt = context.RequestContext('fake', 'fake')
            (instances, _) = ca.create(user_ctxt,
                                       instance_type,
                                       'image_no_config_drive_property',
                                       min_count=1, max_count=1)
            self.assertFalse(configdrive.required_by(instances[0]))

            (instances, _) = ca.create(user_ctxt,
                                       instance_type,
                                       'image_config_drive_optional',
                                       min_count=1, max_count=1)
            self.assertFalse(configdrive.required_by(instances[0]))

            (instances, _) = ca.create(user_ctxt,
                                       instance_type,
                                       'image_config_drive_mandatory',
                                       min_count=1, max_count=1)
            self.assertTrue(configdrive.required_by(instances[0]))

            (instances, _) = ca.create(user_ctxt,
                                       instance_type,
                                       'image_config_drive_malformed',
                                       min_count=1, max_count=1)
            self.assertFalse(configdrive.required_by(instances[0]))

        finally:
            fake_image.FakeImageService_reset()
