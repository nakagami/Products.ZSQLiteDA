##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################
database_type='SQLite'
__doc__='''%s Database Connection

$Id: DA.py,v 1.10 2009/08/08 08:18:24 nakagami Exp $''' % database_type
__version__='$Revision: 1.10 $'[11:-2]

import sys
from _thread import allocate_lock

from .db import DB, manage_DataSources, data_dir
import Shared.DC.ZRDB.Connection
from App.special_dtml import HTMLFile
import Shared.DC.ZRDB.Connection

_connections={}
_connections_lock=allocate_lock()

data_sources=manage_DataSources

manage_addZSQLiteConnectionForm=HTMLFile('dtml/connectionAdd',globals())

def manage_addZSQLiteConnection(
    self, id, title, connection, REQUEST=None):
    """Add a DB connection to a folder"""

    # Note - ZSQLiteDA's connect immediately check is alway false
    self._setObject(id, Connection(
        id, title, connection, None))
    if REQUEST is not None: return self.manage_main(self,REQUEST)

class Connection(Shared.DC.ZRDB.Connection.Connection):
    " "
    database_type=database_type
    id='%s_database_connection' % database_type
    meta_type=title='Z %s Database Connection' % database_type
    icon='misc_/Z%sDA/conn' % database_type
    data_dir=data_dir

    manage_properties=HTMLFile('dtml/connectionEdit', globals(),
                                       data_sources=data_sources)

    def connected(self):
        if hasattr(self, '_v_database_connection'):
            return self._v_database_connection.opened
        return ''

    def connect(self,s):
        _connections_lock.acquire()
        try:
            c=_connections
            self._v_database_connection=c[s]=DB(s)
            return self
        finally:
            _connections_lock.release()
