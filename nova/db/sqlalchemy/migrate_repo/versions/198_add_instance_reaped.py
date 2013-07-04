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

from sqlalchemy import Column, Index, Integer, MetaData, Table


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    instances = Table('instances', meta, autoload=True)
    shadow_instances = Table('shadow_instances', meta, autoload=True)

    reaped_column = Column('reaped', Integer)
    instances.create_column(reaped_column)
    shadow_instances.create_column(reaped_column.copy())

    reap_attempts_column = Column('reap_attempts', Integer, nullable=False,
                                  default=0, server_default='0')
    instances.create_column(reap_attempts_column)
    shadow_instances.create_column(reap_attempts_column.copy())

    reaped_index = Index('instances_reaped_idx', instances.c.reaped)
    reaped_index.create(migrate_engine)

    reap_attempts_index = Index('instances_reap_attempts_idx',
                                instances.c.reap_attempts)
    reap_attempts_index.create(migrate_engine)


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    instances = Table('instances', meta, autoload=True)
    instances.columns.reaped.drop()
    instances.columns.reap_attempts.drop()

    shadow_instances = Table('shadow_instances', meta, autoload=True)
    shadow_instances.columns.reaped.drop()
    shadow_instances.columns.reap_attempts.drop()
