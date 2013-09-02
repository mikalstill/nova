# Copyright 2013 Rackspace Australia
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

from sqlalchemy import Boolean, Column, Integer, MetaData, String, Table
from sqlalchemy import select
from nova.db.sqlalchemy.utils import InsertFromSelect


# NOTE(mikal): we stopped allowing users to specify an image id for config
# drive to overlay on top of when config drvie v1 was deprecated in Folsom.
# Instead, we now treat that String(255) column as a boolean. We are therefore
# less worried than usual about the downgrade being lossy in this migration
# than normal.


def convert_to_bool(migrate_engine, meta, table_name):
    table = Table(table_name, meta, autoload=True)
    new_config_drive = Column('new_config_drive', Boolean, default=False)
    new_config_drive.create(table, populate_default=False)

    table.update().\
            where(table.c.config_drive != None).\
            values(new_config_drive=True).\
            execute()

    table.c.config_drive.drop()
    table.c.new_config_drive.alter(name='config_drive')


def convert_to_string(migrate_engine, meta, table_name):
    table = Table(table_name, meta, autoload=True)
    new_config_drive = Column('new_config_drive', String(255), default='')
    new_config_drive.create(table, populate_default=False)

    table.update().\
            where(table.c.config_drive == True).\
            values(new_config_drive='yes').\
            execute()

    table.c.config_drive.drop()
    table.c.new_config_drive.alter(name='config_drive')


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    convert_to_bool(migrate_engine, meta, 'instances')
    convert_to_bool(migrate_engine, meta, 'shadow_instances')


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    convert_to_string(migrate_engine, meta, 'instances')
    convert_to_string(migrate_engine, meta, 'shadow_instances')
