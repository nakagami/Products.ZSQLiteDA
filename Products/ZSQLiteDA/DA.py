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
database_type = 'SQLite'

import os
from _thread import allocate_lock
from html import escape
from AccessControl.Permissions import change_database_connections
from AccessControl.SecurityInfo import ClassSecurityInfo
# from OFS.PropertyManager import PropertyManager
from App.Dialogs import MessageDialog
from .db import DB, manage_DataSources, init_new_db, DEFAULT_DATA_DIR
import Shared.DC.ZRDB.Connection
from App.special_dtml import HTMLFile
import Acquisition
from ExtensionClass import Base

_connections = {}
_connections_lock = allocate_lock()

data_sources = manage_DataSources

addConnectionForm = HTMLFile('dtml/connectionAdd', globals())


def manage_addZSQLiteConnectionForm(self, REQUEST, *args, **kw):
    """Add a connection form"""

    return addConnectionForm(
        self, self, REQUEST,
        database_type=database_type,
        data_dir=DEFAULT_DATA_DIR,
        data_sources=data_sources(data_dir=DEFAULT_DATA_DIR))


def manage_addZSQLiteConnection(self, id, title, connection, REQUEST=None):
    """Add a DB connection to a folder"""

    # Note - ZSQLiteDA's connect immediately check is alway false
    self._setObject(id, Connection(
        id, title, connection, REQUEST))
    if REQUEST is not None:
        return self.manage_main(self, REQUEST)


class Connection(Shared.DC.ZRDB.Connection.Connection):
    " "

    security = ClassSecurityInfo()
    _isAnSQLConnection = True
    data_dir = DEFAULT_DATA_DIR

    def __init__(self, id, title, connection_string, REQUEST=None):
        data_dir = REQUEST.get('data_dir', DEFAULT_DATA_DIR)

        init_new_db(data_dir=data_dir, connection_string=connection_string)

        self.data_dir = data_dir

        super().__init__(id, title, connection_string)

    def data_dir_is_default(self):
        return self.data_dir == DEFAULT_DATA_DIR

    manage_options = Shared.DC.ZRDB.Connection.Connection.manage_options + (
        {'label': 'Browse', 'action': 'manage_browse'},
        # {'label': 'Design', 'action':'manage_tables'},
    )

    manage_browse = HTMLFile('dtml/browse', globals())

    database_type = database_type
    id = f'{database_type}_database_connection'
    meta_type = title = f'Z {database_type} Database Connection'
    zmi_icon = 'fas fa-database'

    manage_main = HTMLFile(
        'dtml/connectionStatus', globals()
    )

    manage_properties = HTMLFile(
        'dtml/connectionEdit', globals(),
        data_sources=data_sources,
        DEFAULT_DATA_DIR=DEFAULT_DATA_DIR
    )

    @security.protected(change_database_connections)
    def manage_edit(self, title, data_dir, connection_string='',
                    new_database='', check=None, REQUEST=None):
        """Change connection
        """
        if new_database:
            connection_string = new_database

        if data_dir != self.data_dir:  # data_dir is changed
            connection_string = '' or new_database

        if data_dir == DEFAULT_DATA_DIR:
            init_new_db(data_dir=data_dir, connection_string=connection_string)
        elif not os.path.exists(data_dir):
            return MessageDialog(
                title='Edited',
                message=f'The directory <code>{self.data_dir}</code> does not exist. Please create it on the file system.',
                action='./manage_properties')

        if not os.path.exists(os.path.join(data_dir, connection_string)):
            return MessageDialog(
                title='Edited',
                message=f'The database file <strong>{connection_string}</strong> does not exist in {data_dir}. Please create it on the file system.',
                action='./manage_properties')

        self.data_dir = data_dir

        if self.connected():
            self.manage_close_connection()

        self.edit(title, connection_string, check)

        if REQUEST is not None:
            esc_id = escape(self.id)
            return MessageDialog(
                title='Edited',
                message=f'<strong>{esc_id}</strong> has been edited.',
                action='./manage_properties')

    def connected(self):
        if hasattr(self, '_v_database_connection'):
            return self._v_database_connection.opened
        return ''

    def connect(self, s):
        _connections_lock.acquire()
        try:
            c = _connections
            self._v_database_connection = c[s] = DB(s)
            return self
        finally:
            _connections_lock.release()

    def tpValues(self):
        r = []
        if not hasattr(self, '_v_database_connection'):
            return r
        c = self._v_database_connection
        try:
            for d in c.tables(rdb=0):
                try:
                    name = d['TABLE_NAME']
                    b = TableBrowser()
                    b.__name__ = name
                    b._d = d
                    b._c = c
                    # b._columns=c.columns(name)
                    try:
                        b.icon = d['TABLE_TYPE']
                    except Exception:
                        pass
                    r.append(b)
                    # tables[name]=b
                except Exception:
                    # print d['TABLE_NAME'], sys.exc_type, sys.exc_value
                    pass

        finally:
            pass  # print sys.exc_type, sys.exc_value
        # self._v_tpValues=r
        return r

    def __getitem__(self, name):
        if name == 'tableNamed':
            if not hasattr(self, '_v_tables'):
                self.tpValues()
            return self._v_tables.__of__(self)
        raise KeyError(name)

    def manage_wizard(self, tables):
        " "

    def manage_join(self, tables, select_cols, join_cols, REQUEST=None):
        """Create an SQL join"""

    def manage_insert(self, table, cols, REQUEST=None):
        """Create an SQL insert"""

    def manage_update(self, table, keys, cols, REQUEST=None):
        """Create an SQL update"""


class TableBrowserCollection(Acquisition.Implicit):
    "Helper class for accessing tables via URLs"


class Browser(Base):
    def __getattr__(self, name):
        try:
            return self._d[name]
        except KeyError:
            raise AttributeError(name)


class TableBrowser(Browser, Acquisition.Implicit):
    icon = 'what'
    Description = check = ''

    def tpValues(self):
        r = []
        tname = self.__name__
        b = SQLBrowser()
        b._parent = self
        b._d = {'SQL': self._c.sqlscript(tname)}
        r.append(b)
        return r

    def tpId(self):
        return self._d['TABLE_NAME']

    def tpURL(self):
        return "Table/%s" % self._d['TABLE_NAME']

    def Name(self):
        return self._d['TABLE_NAME']

    def Type(self):
        return self._d['TABLE_TYPE']


class SQLBrowser(Browser):
    icon = None

    def tpId(self):
        return "SQL"

    def tpURL(self):
        return "Table/%s/SQL" % self._parent._d['TABLE_NAME']

    def Name(self):
        return ''

    def Type(self):
        return ''

    def Description(self):
        return self._d['SQL']
