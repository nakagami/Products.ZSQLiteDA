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
import os
import json
import logging
from urllib.parse import urlencode
from AccessControl.Permissions import change_database_connections, \
    open_close_database_connection, view_management_screens
from AccessControl.SecurityInfo import ClassSecurityInfo
import Shared.DC.ZRDB.Connection
from App.special_dtml import HTMLFile
from sqlite3 import OperationalError as sqlite3_OperationalError

from . import __version__
from .db import DB, DEFAULT_DATA_DIR, check_database, \
    create_db_file, manage_DataSources, safe_db_name, format_sql, \
    configured_dirs, can_create_in, can_mount_from

logger = logging.getLogger('Products.ZSQLiteDA')

database_type = 'SQLite'

data_sources = manage_DataSources

addConnectionForm = HTMLFile('dtml/connectionAdd', globals())


def extract_error(e):
    try:
        return e.args[0]
    except Exception:
        return str(e)


def _add_form(self, REQUEST, message=''):
    """The Add form. ``message`` is a bootstrap alert above the fields."""
    data_dir = DEFAULT_DATA_DIR
    if REQUEST is not None and REQUEST.get('data_dir'):
        data_dir = REQUEST['data_dir']
    try:
        sources = data_sources(data_dir=data_dir)
    except sqlite3_OperationalError:
        data_dir = DEFAULT_DATA_DIR
        sources = data_sources(data_dir=data_dir)
    return addConnectionForm(
        self, self, REQUEST,
        database_type=database_type,
        data_dir=data_dir,
        data_sources=sources,
        manage_tabs_message=message)


def manage_addZSQLiteConnectionForm(self, REQUEST, *args, **kw) -> HTMLFile:
    """Add a connection form"""

    return _add_form(self, REQUEST)


def manage_addZSQLiteConnection(self, id: str, title: str,
                                data_dir: str,
                                connection: str = '',
                                new_database: str = '',
                                mode: str = '',
                                REQUEST=None) -> 'Connection.manage_main':
    """Add a DB connection to a folder"""

    if not id:
        if REQUEST is None:
            raise sqlite3_OperationalError(
                'Please provide an id for the database adapter!')
        return _add_form(
            self, REQUEST, 'Please provide an id for the database adapter!')

    # Existing vs. create-new is driven by the mode radio, with a fallback to
    # whichever field carries a value so a scripted or JS-less POST still does
    # the right thing. The two inputs use distinct field names ('connection'
    # and 'new_database'), so the form can never submit a duplicate that
    # ZPublisher would fold into a list.
    creating = (mode == 'new') or (not connection and bool(new_database))
    if creating:
        connection = new_database

    db_path = os.path.join(data_dir, connection)

    try:
        safe_db_name(connection)
        if creating and connection and os.path.exists(db_path):
            raise sqlite3_OperationalError(
                f'The database file “{connection}” already exists\n'
                f'in {data_dir}!')
        if connection and not creating and not os.path.exists(db_path):
            # 'use existing' must not silently fall through to creating a file
            raise sqlite3_OperationalError(
                f'The database “{connection}” does not exist in “{data_dir}”. '
                'Select an existing database or create a new one.')
        check_database(dbpath=db_path)
    except sqlite3_OperationalError as e:
        if REQUEST is None:
            raise
        # Stay on the Add form. MessageDialog is the old full-page dialog and
        # would leave the ZMI layout.
        return _add_form(self, REQUEST, extract_error(e))
    # Note - ZSQLiteDA's connect immediately check is alway false
    self._setObject(id, Connection(
        id, title, connection, REQUEST=REQUEST, data_dir=data_dir))
    if REQUEST is not None:
        return self.manage_main(self, REQUEST)


class Connection(Shared.DC.ZRDB.Connection.Connection):
    " "

    security = ClassSecurityInfo()
    _isAnSQLConnection = True
    data_dir = DEFAULT_DATA_DIR

    def __init__(self, id: str, title: str, connection_string: str = '',
                 REQUEST=None, data_dir: str = None) -> None:
        if data_dir is None:
            data_dir = (REQUEST.get('data_dir', DEFAULT_DATA_DIR)
                        if REQUEST is not None else DEFAULT_DATA_DIR)
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
    da_version = __version__
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
        """Change the connection's title, data directory and database.

        ``data_dir`` must be in the allowlist, except that a connection whose
        stored directory pre-dates the allowlist stays editable in place (e.g.
        to fix its title) without being re-opened. ``connection_string`` selects
        an existing database in that directory; ``new_database`` creates one.
        """
        def fail(message):
            # Programmatic callers (REQUEST is None) get an exception rather
            # than a management page they cannot render (connectionEdit.dtml
            # dereferences REQUEST).
            if REQUEST is None:
                raise sqlite3_OperationalError(message)
            return self._properties_message(REQUEST, message, 'danger')

        for name in (new_database, connection_string):
            try:
                safe_db_name(name)
            except sqlite3_OperationalError as e:
                return fail(extract_error(e))

        dir_changed = (data_dir != self.data_dir)

        # A connection whose stored directory is not on the allowlist (e.g. one
        # created before the allowlist existed) may still be edited in place:
        # its title can be changed, but it is not re-opened, its directory may
        # not be changed to another non-allowed one, and no database may be
        # created there. Anything that actually opens a database still goes
        # through connect() -> check_database, so this stays secure by default.
        if not can_mount_from(data_dir):
            if dir_changed or new_database:
                return fail(
                    f'This adapter may not use databases in “{data_dir}”. '
                    'Choose an allowed directory, or add this one to the file '
                    'named by “directories-file” in the '
                    '<product-config Products.ZSQLiteDA> section of zope.conf.')
            self.edit(title, self.connection_string, None)
            if REQUEST is not None:
                return self._properties_message(
                    REQUEST, f'“{self.id}” has been edited.')
            return

        if not os.path.exists(data_dir):
            return fail(
                f'The directory “{data_dir}” does not exist.\n'
                'Please create it on the file system.')

        if new_database:
            if os.path.exists(os.path.join(data_dir, new_database)):
                return fail(
                    f'The database file “{new_database}” already exists\n'
                    f'in {data_dir}!')
            try:
                create_db_file(data_dir=data_dir, connection_string=new_database)
            except sqlite3_OperationalError as e:
                return fail(extract_error(e))
            connection_string = new_database
        elif connection_string and not os.path.exists(
                os.path.join(data_dir, connection_string)):
            if dir_changed:
                # The directory was changed and the previously selected database
                # is not in the new one: adopt the directory but drop the stale
                # selection, rather than binding to an unrelated same-named file
                # or failing outright.
                connection_string = ''
            else:
                return fail(
                    f'The database “{connection_string}” does not exist in '
                    f'“{data_dir}”. Select a database that exists in that '
                    'directory.')

        if connection_string:
            try:
                check_database(dbpath=os.path.join(data_dir, connection_string))
            except sqlite3_OperationalError as e:
                if not dir_changed and self.connection_string == connection_string:
                    # the currently-bound database has become invalid: clear it
                    self.edit(title, '', check)
                return fail(extract_error(e))

        self.data_dir = data_dir

        if self.connected():
            self.manage_close_connection()

        # Re-open right away when a database is selected, so the Status and
        # Browse tabs reflect the new connection immediately. Honour an explicit
        # ``check`` from a programmatic caller; the UI form sends none, so it
        # defaults to opening whenever a database is selected. An empty
        # connection_string stays closed (connecting to '' would point at the
        # directory and fail).
        connect_now = bool(connection_string) if check is None else bool(check)
        self.edit(title, connection_string,
                  1 if (connect_now and connection_string) else None)

        if REQUEST is not None:
            return self._properties_message(
                REQUEST, f'“{self.id}” has been edited.')

    def _properties_message(self, REQUEST, message, message_type='success'):
        """Redirect to Properties so the tab matches the page.

        Rendering the template directly leaves the browser on ``manage_edit``.
        That address matches no tab, so the first tab (Status) is highlighted
        while the Properties form is still on screen.
        """
        query = urlencode({
            'manage_tabs_message': message,
            'manage_tabs_type': message_type,
        })
        return REQUEST.RESPONSE.redirect(
            f'{self.absolute_url()}/manage_properties?{query}')

    def connected(self) -> str:
        if hasattr(self, '_v_database_connection'):
            return self._v_database_connection.opened
        return ''

    def connect(self, s: str) -> 'Connection':
        # connect() is the authoritative allowlist/validation point. The Add and
        # Edit forms validate up front for early feedback, but a legacy object
        # whose stored data_dir predates the allowlist (or a crafted name) must
        # not be openable through the Status tab, an implicit __call__, or a
        # ZODB reconnect either.
        safe_db_name(s)
        dbpath = os.path.join(self.data_dir, s)
        check_database(dbpath=dbpath)
        # Opening must never *create* a database. check_database deliberately
        # accepts a not-yet-existing file in a create-allowed directory so the
        # Add/Edit "create new" paths can pre-create it via create_db_file();
        # but reaching connect() with the file missing means it was removed
        # underneath us, so surface that instead of letting sqlite3.connect()
        # silently fabricate an empty database and mask the data loss.
        if s and not os.path.exists(dbpath):
            raise sqlite3_OperationalError(
                f'The database “{s}” no longer exists in “{self.data_dir}”.')
        # close any previous connection first, otherwise the old sqlite3
        # handle leaks when reconnecting (e.g. Open clicked twice, or after edit)
        self.manage_close_connection()
        self._v_database_connection = DB(dbpath)
        # keep the base class's _v_connected marker in sync, so title_or_id()
        # / title_and_id() report "(connected)" like a stock ZRDB connection
        self._v_connected = self._v_database_connection.opened
        return self

    @security.protected(open_close_database_connection)
    def manage_open_connection(self, REQUEST=None):
        """Open the connection. A failure — e.g. a directory that is no longer
        in the allowlist, or an invalid database — is shown as a red alert
        rather than the base class's default green 'success' banner."""
        msg, msg_type = '', 'success'
        try:
            self.connect(self.connection_string)
        except Exception as exc:
            # log with traceback like the base class does, so a failed open is
            # diagnosable even when there is no REQUEST to show the alert on
            logger.error('Error opening database connection.', exc_info=True)
            msg, msg_type = str(exc), 'danger'
        if REQUEST is not None:
            return self.manage_main(self, REQUEST,
                                    manage_tabs_message=msg,
                                    manage_tabs_type=msg_type)

    @security.protected(open_close_database_connection)
    def manage_close_connection(self, REQUEST=None):
        """Close the connection and drop the stale volatile handle, so that
        __call__ reconnects on demand instead of returning a closed connection."""
        result = super().manage_close_connection(REQUEST)
        try:
            del self._v_database_connection
        except AttributeError:
            pass
        return result

    @security.protected(view_management_screens)
    def manage_browse_data(self):
        # Data for the Browse tab: one entry per table/view with its columns
        # and CREATE statement, as plain built-in types so the DTML template
        # can iterate them directly.
        if not self.connected():
            return []
        c = self._v_database_connection
        result = []
        for d in c.tables():
            name = d['TABLE_NAME']
            result.append({
                'name': name,
                'kind': d['TABLE_TYPE'],
                'columns': c.columns(name),
                'sql': format_sql(c.sqlscript(name)),
            })
        return result

    @security.protected(view_management_screens)
    def manage_listDataSources(self, data_dir=None, REQUEST=None):
        """JSON: the database files in `data_dir` plus whether the directory
        allows creating / mounting databases, used by the Properties form to
        refresh its picker when the data directory is changed."""
        if data_dir is None:
            data_dir = self.data_dir
        result = {
            'data_dir': data_dir,
            'can_create': can_create_in(data_dir),
            'can_mount': can_mount_from(data_dir),
            'databases': [],
            'error': '',
        }
        if result['can_mount']:
            try:
                result['databases'] = [name for name, _ in
                                       data_sources(data_dir=data_dir)]
            except sqlite3_OperationalError as e:
                result['error'] = extract_error(e)
        else:
            result['error'] = 'This directory is not in the allowlist.'
        if REQUEST is not None:
            REQUEST.RESPONSE.setHeader('Content-Type', 'application/json')
        return json.dumps(result)

    @security.protected(view_management_screens)
    def zsql_dir_options(self):
        # directories offered in the Properties data-directory dropdown: the
        # configured allowlist plus this connection's current directory (which
        # may pre-date the allowlist), sorted.
        return sorted(set(configured_dirs()) | {self.data_dir})

    @security.protected(view_management_screens)
    def zsql_can_create_here(self):
        # whether new databases may be created in this connection's directory
        return can_create_in(self.data_dir)

    @security.protected(view_management_screens)
    def zsql_can_mount_here(self):
        # whether this connection's directory may be used at all
        return can_mount_from(self.data_dir)

    @security.protected(view_management_screens)
    def zsql_databases(self):
        # database files for the Properties picker's initial render: empty when
        # the current directory is not allowed or cannot be read, so a legacy or
        # missing data_dir is never enumerated and never crashes the render.
        # manage_listDataSources then drives the allowlist-aware refresh.
        names = []
        if can_mount_from(self.data_dir):
            try:
                names = [name for name, _ in data_sources(data_dir=self.data_dir)]
            except sqlite3_OperationalError:
                names = []
        # Always include the currently-bound database, even if it is a dot-file
        # (hidden from the listing) or has since disappeared, so the picker
        # always has an option matching connection_string and saving the form
        # cannot silently rebind the adapter to a different file (or wipe the
        # binding when the select would otherwise be empty).
        cs = self.connection_string
        if cs and cs not in names:
            names.append(cs)
        return sorted(names)

    def manage_wizard(self, tables):
        pass

    def manage_join(self, tables, select_cols, join_cols, REQUEST=None):
        pass

    def manage_insert(self, table, cols, REQUEST=None):
        pass

    def manage_update(self, table, keys, cols, REQUEST=None):
        pass
