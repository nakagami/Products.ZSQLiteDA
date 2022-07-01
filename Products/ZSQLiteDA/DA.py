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
from App.Dialogs import MessageDialog
import Shared.DC.ZRDB.Connection
from App.special_dtml import HTMLFile
import Acquisition
from ExtensionClass import Base
from sqlite3 import OperationalError as sqlite3_OperationalError

from .db import DB, DEFAULT_DATA_DIR, check_database, \
    create_db_file, manage_DataSources

_connections = {}
_connections_lock = allocate_lock()

data_sources = manage_DataSources

addConnectionForm = HTMLFile('dtml/connectionAdd', globals())


def extract_error(e):
    try:
        return e.args[0].replace('\n', '<br>')
    except Exception:
        return str(e).replace('\n', '<br>')


def manage_addZSQLiteConnectionForm(self, REQUEST, *args, **kw) -> HTMLFile:
    """Add a connection form"""

    return addConnectionForm(
        self, self, REQUEST,
        database_type=database_type,
        data_dir=DEFAULT_DATA_DIR,
        data_sources=data_sources(data_dir=DEFAULT_DATA_DIR))


def manage_addZSQLiteConnection(self, id: str, title: str,
                                data_dir: str,
                                connection: str = '',
                                REQUEST=None) -> 'manage_main':
    """Add a DB connection to a folder"""

    db_path = os.path.join(data_dir, connection)

    if not id:
        return MessageDialog(
            title='Edited',
            message='Please provide an id for the database adapter!',
            action='javascript:history.back()'
        )

    try:
        check_database(dbpath=db_path)
    except sqlite3_OperationalError as e:
        return MessageDialog(
            title='Edited',
            message=extract_error(e),
            action='javascript:history.back()'
        )
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

    def __init__(self, id: str, title: str,
                 connection_string: str = '', REQUEST=None) -> None:
        data_dir = REQUEST.get('data_dir', DEFAULT_DATA_DIR)
        create_db_file(data_dir=data_dir, connection_string=connection_string)
        self.data_dir = data_dir
        super().__init__(id, title, connection_string)

    def data_dir_is_default(self):  # used in the DTML forms
        return self.data_dir == DEFAULT_DATA_DIR

    manage_options = Shared.DC.ZRDB.Connection.Connection.manage_options + (
        {'label': 'Browse', 'action': 'manage_browse'},
    )

    manage_browse = HTMLFile('dtml/browse', globals())

    database_type = database_type
    id = f'{database_type}_database_connection'
    meta_type = title = f'Z {database_type} Database Connection'
    zmi_icon = 'fas fa-database'

    manage_main = HTMLFile('dtml/connectionStatus', globals())

    manage_properties = HTMLFile(
        'dtml/connectionEdit', globals(),
        data_sources=data_sources,
        DEFAULT_DATA_DIR=DEFAULT_DATA_DIR
    )

    @security.protected(change_database_connections)
    def manage_edit(self, title: str, data_dir: str, connection_string: str = '',
                    new_database: str = '', check=None, REQUEST=None) -> str:
        """Change connection
        """
        if new_database:
            if os.path.exists(os.path.join(data_dir, new_database)):
                return MessageDialog(
                    title='Edited',
                    message=(
                        f'The database file <code>{new_database}</code> already exists<br>'
                        f'in {data_dir}!'),
                    action='./manage_properties')

            connection_string = new_database

        if data_dir != self.data_dir:  # data_dir is changed
            connection_string = '' or new_database

        if not os.path.exists(data_dir):
            return MessageDialog(
                title='Edited',
                message=(
                    f'The directory <code>{data_dir}</code> does not exist.<br>'
                    'Please create it on the file system.'
                ),
                action='./manage_properties')

        self.data_dir = data_dir

        if connection_string:
            try:
                create_db_file(data_dir=data_dir, connection_string=connection_string)
            except sqlite3_OperationalError as e:
                return MessageDialog(
                    title='Edited',
                    message=extract_error(e),
                    action='./manage_properties')

            try:
                check_database(dbpath=os.path.join(data_dir, connection_string))
            except sqlite3_OperationalError as e:
                if self.connection_string == connection_string:
                    self.edit(title, '', check)
                return MessageDialog(
                    title='Edited',
                    message=extract_error(e),
                    action='./manage_properties')

        if self.connected():
            self.manage_close_connection()

        self.edit(title, connection_string, check)

        if REQUEST is not None:
            esc_id = escape(self.id)
            return MessageDialog(
                title='Edited',
                message=f'<strong>{esc_id}</strong> has been edited.',
                action='./manage_properties')

    def connected(self) -> str:
        if hasattr(self, '_v_database_connection'):
            return self._v_database_connection.opened
        print('closed')
        return ''

    def connect(self, s: str) -> 'self':
        _connections_lock.acquire()
        try:
            c = _connections
            s = os.path.join(self.data_dir, s)
            self._v_database_connection = c[s] = DB(s)
            return self
        finally:
            _connections_lock.release()

    def tpValues(self) -> list:
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

    def __getitem__(self, name: str):
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
    def __getattr__(self, name: str) -> str:
        try:
            return self._d[name]
        except KeyError:
            raise AttributeError(name)


class TableBrowser(Browser, Acquisition.Implicit):
    icon = 'what'
    Description = check = ''

    def tpValues(self) -> list:
        r = []
        tname = self.__name__
        b = SQLBrowser()
        b._parent = self
        b._d = {'SQL': self._c.sqlscript(tname)}
        r.append(b)
        return r

    def tpId(self) -> str:
        return self._d['TABLE_NAME']

    def tpURL(self) -> str:
        return "Table/%s" % self._d['TABLE_NAME']

    def Name(self) -> str:
        return self._d['TABLE_NAME']

    def Type(self) -> str:
        return self._d['TABLE_TYPE']


class SQLBrowser(Browser):
    icon = None

    def tpId(self) -> str:
        return "SQL"

    def tpURL(self) -> str:
        return "Table/%s/SQL" % self._parent._d['TABLE_NAME']

    def Name(self) -> str:
        return ''

    def Type(self) -> str:
        return ''

    def Description(self) -> str:
        return self._d['SQL']
