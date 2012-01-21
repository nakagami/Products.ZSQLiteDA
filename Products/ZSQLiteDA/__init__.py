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
__doc__='''Generic Database Adapter Package Registration

$Id: __init__.py,v 1.7 2009/08/08 07:56:34 nakagami Exp $'''
__version__='$Revision: 1.7 $'[11:-2]

import os
from App.ImageFile import ImageFile
classes=('DA.Connection',)
database_type='SQLite'

class SQLiteError(Exception):
    pass

class QueryError(SQLiteError):
    pass

misc_={'conn':
       ImageFile('Shared/DC/ZRDB/www/DBAdapterFolder_icon.gif')}

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

