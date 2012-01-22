##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################
import os
import Globals
from App.ImageFile import ImageFile
classes=('DA.Connection',)
database_type='SQLite'
data_dir=os.path.abspath(os.path.join(Globals.data_dir, 'sqlite'))

class SQLiteError(Exception):
    pass

class QueryError(SQLiteError):
    pass

misc_={'conn': ImageFile('images/DBAdapterFolder_icon.gif', globals()),
        'table': ImageFile('images/table.gif', globals()),
}

DA=None
def getDA():
    global DA
    if DA is None:
        import DA
    return DA

getDA()

__module_aliases__=(
    ('Products.AqueductSQLite.DA', DA),
    )

def manage_addZSQLiteConnectionForm(self, REQUEST, *args, **kw):
    " "
    DA=getDA()
    return DA.addConnectionForm(
        self, self, REQUEST,
        database_type=database_type,
        data_dir=data_dir,
        data_sources=DA.data_sources)

def manage_addZSQLiteConnection(
    self, id, title, connection, REQUEST=None):
    " "
    return getDA().manage_addZSQLiteConnection(
        self, id, title, connection, REQUEST)

def initialize(context):

    context.registerClass(
        DA.Connection,
        permission='Add Z SQLite Database Connections',
        constructors=(manage_addZSQLiteConnectionForm,
                      manage_addZSQLiteConnection),
        legacy=(manage_addZSQLiteConnectionForm,
                manage_addZSQLiteConnection),
    )

