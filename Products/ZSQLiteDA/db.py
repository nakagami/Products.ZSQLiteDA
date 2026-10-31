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
import sqlite3

from DateTime import DateTime
import Shared.DC.ZRDB.THUNK
import App.ApplicationManager
import App.config

instancepath = App.ApplicationManager.getConfiguration().instancehome
DEFAULT_DATA_DIR = os.path.abspath(os.path.join(instancepath, 'var', 'sqlite'))


def _product_config() -> dict:
    """The <product-config Products.ZSQLiteDA> mapping from zope.conf (or {})."""
    try:
        pc = getattr(App.config.getConfiguration(), 'product_config', None) or {}
    except Exception:
        return {}
    # ZConfig lower-cases the section name
    return pc.get('products.zsqliteda') or pc.get('Products.ZSQLiteDA') or {}


# process-wide cache of the parsed directories-file, keyed on (path, mtime) so
# it is re-read only when the file actually changes; configured_dirs() is hit
# repeatedly per request (connect -> check_database, listDataSources, every
# ZODB load via __setstate__ -> connect) and re-parsing it each time is wasteful.
_dirs_cache = None


def configured_dirs() -> dict:
    """Directories this adapter may use, as ``{absolute_dir: allow_create}``.

    Read from the file named by the ``directories-file`` key of the product
    config: one directory per line, ``#`` comments and blank lines ignored, and
    a ``create `` prefix marks a directory in which new databases may also be
    created. The instance default directory is always included (create allowed),
    so with no configuration the adapter is restricted to ``var/sqlite``.

    The parsed result is cached and only re-read when the file's mtime changes."""
    global _dirs_cache
    cfg_path = _product_config().get('directories-file')
    mtime = None
    if cfg_path and os.path.isfile(cfg_path):
        try:
            mtime = os.path.getmtime(cfg_path)
        except OSError:
            mtime = None
    cache_key = (cfg_path, mtime)
    cache = _dirs_cache
    if cache is not None and cache[0] == cache_key:
        return dict(cache[1])   # copy so callers can't mutate the cached dict
    dirs = {}
    if cfg_path and os.path.isfile(cfg_path):
        with open(cfg_path, encoding='utf-8') as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                allow_create = False
                head = line.split(None, 1)
                if head[0].lower() == 'create':
                    line = head[1].strip() if len(head) > 1 else ''
                    allow_create = True
                if line:
                    dirs[os.path.abspath(os.path.expanduser(line))] = allow_create
    dirs[DEFAULT_DATA_DIR] = True
    _dirs_cache = (cache_key, dict(dirs))
    return dirs


def can_mount_from(data_dir: str) -> bool:
    """May an existing database located in ``data_dir`` be opened? Relative
    paths are rejected outright, so a crafted relative ``data_dir`` can never be
    resolved against the process working directory and accidentally match an
    allowed entry."""
    return (os.path.isabs(data_dir)
            and os.path.abspath(data_dir) in configured_dirs())


def can_create_in(data_dir: str) -> bool:
    """May a new database be created in ``data_dir``? Relative paths are
    rejected outright (see :func:`can_mount_from`)."""
    return (os.path.isabs(data_dir)
            and configured_dirs().get(os.path.abspath(data_dir)) is True)


def _dir_list(dirs) -> str:
    return '\n'.join('“%s”' % d for d in sorted(dirs)) or '(none)'


# this is just a basic check
def check_database(dbpath: str) -> bool:
    data_dir, connection_string = os.path.split(dbpath)

    if data_dir and not os.path.isabs(data_dir):
        raise sqlite3.OperationalError(
            f'The data directory “{data_dir}” must be an absolute path.')
    data_dir = os.path.abspath(data_dir)

    error_msg = ''

    if not can_mount_from(data_dir):
        error_msg = (
            'This SQLite Database Adapter may not use databases in '
            f'“{data_dir}”.\n\n'
            'Allowed directories:\n'
            f'{_dir_list(configured_dirs())}\n\n'
            'Add a directory to the file named by “directories-file” in the '
            '<product-config Products.ZSQLiteDA> section of zope.conf to '
            'permit it.')
    elif not os.path.exists(data_dir):
        error_msg = f'The directory “{data_dir}” does not exist!'
    elif not os.path.isdir(data_dir):
        error_msg = f'“{data_dir}” is not a directory!'
    elif not os.path.exists(dbpath):
        if not can_create_in(data_dir):
            error_msg = (
                f'There is no database “{connection_string}” in '
                f'“{data_dir}”, and new databases may not be created there.'
                '\n\nNew databases can be created in:\n'
                f'{_dir_list(d for d, c in configured_dirs().items() if c)}')
    elif connection_string:
        try:
            filesize = os.stat(dbpath).st_size

            if 0 < filesize < 16:
                error_msg = (
                    f'The file “{connection_string}” in “{data_dir}” is too '
                    'small to be a valid SQLite 3 database!')
            elif filesize >= 16:
                with open(dbpath, 'rb') as db:
                    header = db.read(16)
                if header.startswith(b'SQLite format 3\x00'):
                    return True
                error_msg = (
                    f'The file “{connection_string}” in “{data_dir}” is '
                    'not a valid SQLite 3 database!')
        except OSError as exc:
            # an unreadable file/directory (permissions, NFS, …) would otherwise
            # raise a bare OSError that the callers' ``except OperationalError``
            # handlers miss, turning a friendly alert into a ZMI 500.
            error_msg = (
                f'The database “{connection_string}” in “{data_dir}” cannot '
                f'be read: {exc.strerror or exc}.')

    if error_msg:
        raise sqlite3.OperationalError(error_msg)


def manage_DataSources(data_dir: str = DEFAULT_DATA_DIR) -> map:
    if os.sep not in data_dir:
        data_dir = os.path.join(DEFAULT_DATA_DIR, data_dir)  # create a subdirectory DEFAULT_DATA_DIR

    error_msg = ''

    if os.path.exists(data_dir):
        if not os.path.isdir(data_dir):
            error_msg = (
                'The Zope SQLite Database Adapter requires the existence of '
                f'the directory “{data_dir}”. This exists, but is not a '
                'directory.')
    else:
        if data_dir != DEFAULT_DATA_DIR:
            error_msg = (
                'The Zope SQLite Database Adapter requires the existence of '
                f'the directory “{data_dir}”. Please create it on the file '
                'system.')

        elif not os.path.exists(DEFAULT_DATA_DIR):
            # it's quite safe to create the default path
            os.mkdir(DEFAULT_DATA_DIR)

    if error_msg:
        raise sqlite3.OperationalError(error_msg)

    try:
        names = os.listdir(data_dir)
    except OSError as exc:
        # e.g. the directory is on the allowlist but not readable; convert to
        # OperationalError so the picker's callers degrade gracefully instead
        # of raising a bare OSError that crashes the render.
        raise sqlite3.OperationalError(
            f'The directory “{data_dir}” cannot be read: '
            f'{exc.strerror or exc}.')

    return map(
        lambda d: (d, ''),
        sorted(
            f for f in names
            if not f.startswith('.')
            and os.path.isfile(os.path.join(data_dir, f))
        )
    )


def safe_db_name(connection_string: str) -> None:
    """Reject database names that try to escape their data directory via a
    path separator, an absolute path, or the directory aliases '.' and '..',
    or that contain control characters — a NUL byte would otherwise crash file
    creation with ``ValueError: embedded null byte`` and a newline would create
    a file with an unusable name. An empty name is allowed (it means 'no
    database selected yet')."""
    if connection_string and (
            os.path.isabs(connection_string)
            or os.path.basename(connection_string) != connection_string
            or connection_string in (os.curdir, os.pardir)
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in connection_string)):
        # deliberately do not echo the name back: it may contain the control
        # characters we are rejecting, which would then land in an HTML alert.
        raise sqlite3.OperationalError(
            'Invalid database name: it must be a plain file name without path '
            'separators or control characters.'
        )


def create_db_file(data_dir: str, connection_string: str) -> None:
    safe_db_name(connection_string)
    if not os.path.isabs(data_dir):
        raise sqlite3.OperationalError(
            f'The data directory “{data_dir}” must be an absolute path.')
    data_dir = os.path.abspath(data_dir)
    db_path = os.path.join(data_dir, connection_string)

    if os.path.exists(db_path):
        return

    if can_create_in(data_dir):
        if data_dir == DEFAULT_DATA_DIR and not os.path.exists(DEFAULT_DATA_DIR):
            os.mkdir(DEFAULT_DATA_DIR)
        if not os.path.isdir(data_dir):
            raise sqlite3.OperationalError(
                f'The directory “{data_dir}” does not exist. '
                'Please create it on the file system.')
        if connection_string:
            with open(db_path, 'w') as f:
                f.write('')
    else:
        error_msg = (
            f'New databases may not be created in “{data_dir}”.\n\n'
            'New databases can be created in:\n'
            f'{_dir_list(d for d, c in configured_dirs().items() if c)}\n\n'
            'Add the directory (with a “create” prefix) to the file named by '
            '“directories-file” in the <product-config Products.ZSQLiteDA> '
            'section of zope.conf to permit it.')
        raise sqlite3.OperationalError(error_msg)


def _ends_in_line_comment(s: str) -> bool:
    """True when the last content of ``s`` lies inside a ``--`` comment.

    A comma appended on that same line would be commented out, so a column
    separator has to move to the next line instead."""
    i, q, in_line = 0, None, False
    while i < len(s):
        ch = s[i]
        if in_line:
            if ch == '\n':
                in_line = False
            i += 1
            continue
        if q:
            if ch == q:
                if q != ']' and i + 1 < len(s) and s[i + 1] == q:
                    i += 2
                    continue
                q = None
            i += 1
            continue
        if s.startswith('--', i):
            in_line = True
            i += 2
            continue
        j = _skip_comment(s, i)
        if j != i:
            i = j
            continue
        if ch in ("'", '"', '`'):
            q = ch
        elif ch == '[':
            q = ']'
        i += 1
    return in_line


def _skip_comment(s: str, i: int) -> int:
    """If a SQL comment starts at ``s[i]``, return the index just past it,
    otherwise ``i``. Handles ``--`` line comments and ``/* */`` block comments
    so a comma or parenthesis inside a comment is not mistaken for part of the
    column definitions (SQLite keeps comments verbatim in ``sqlite_master``)."""
    if s.startswith('--', i):
        nl = s.find('\n', i)
        return len(s) if nl == -1 else nl + 1
    if s.startswith('/*', i):
        end = s.find('*/', i + 2)
        return len(s) if end == -1 else end + 2
    return i


def _open_paren(s: str) -> int:
    """Index of the first ``(`` outside quotes and comments, or -1.

    A parenthesis inside a quoted name, such as ``"t(x)"``, is not the
    start of the column list."""
    q, i = None, 0
    while i < len(s):
        ch = s[i]
        if q:
            if ch == q:
                if q != ']' and i + 1 < len(s) and s[i + 1] == q:
                    i += 2
                    continue
                q = None
            i += 1
            continue
        j = _skip_comment(s, i)
        if j != i:
            i = j
            continue
        if ch in ("'", '"', '`'):
            q = ch
        elif ch == '[':
            q = ']'
        elif ch == '(':
            return i
        i += 1
    return -1


def _split_top_level(s: str) -> list:
    """Split a string on commas that sit outside any parentheses, quotes or
    comments."""
    parts, buf, depth, q, i = [], [], 0, None, 0
    while i < len(s):
        ch = s[i]
        if q:
            buf.append(ch)
            if ch == q:
                if q != ']' and i + 1 < len(s) and s[i + 1] == q:
                    buf.append(s[i + 1]); i += 2; continue
                q = None
            i += 1; continue
        j = _skip_comment(s, i)
        if j != i:
            buf.append(s[i:j]); i = j; continue
        if ch in ("'", '"', '`'):
            q = ch; buf.append(ch)
        elif ch == '[':
            q = ']'; buf.append(ch)
        elif ch == '(':
            depth += 1; buf.append(ch)
        elif ch == ')':
            depth -= 1; buf.append(ch)
        elif ch == ',' and depth == 0:
            parts.append(''.join(buf)); buf = []
        else:
            buf.append(ch)
        i += 1
    if buf:
        parts.append(''.join(buf))
    return parts


def format_sql(sql: str) -> str:
    """Pretty-print a CREATE TABLE statement (one column per line, indented).
    SQLite stores the original text, so a column added via ALTER TABLE ends up
    appended on a single long line; this reflows it. Other statements (views
    etc.) are returned unchanged."""
    if not sql:
        return sql
    s = sql.strip()
    if not s.upper().startswith('CREATE TABLE'):
        return s
    open_idx = _open_paren(s)
    if open_idx == -1:
        return s
    header = s[:open_idx].rstrip()
    if ' AS ' in (' ' + header.upper() + ' '):   # CREATE TABLE ... AS SELECT
        return s
    # find the matching close paren for the column-defs block (quote/paren/
    # comment aware)
    depth, q, close_idx, i = 0, None, -1, open_idx
    while i < len(s):
        ch = s[i]
        if q:
            if ch == q:
                if q != ']' and i + 1 < len(s) and s[i + 1] == q:
                    i += 2; continue
                q = None
            i += 1; continue
        j = _skip_comment(s, i)
        if j != i:
            i = j; continue
        if ch in ("'", '"', '`'):
            q = ch
        elif ch == '[':
            q = ']'
        elif ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                close_idx = i; break
        i += 1
    if close_idx == -1:
        return s
    cols = [c.strip() for c in _split_top_level(s[open_idx + 1:close_idx]) if c.strip()]
    if not cols:
        return s
    trailer = s[close_idx + 1:].strip()
    # A trailing ``--`` comment swallows the rest of its line, so the separating
    # comma has to go on the next line or it (and the following column) vanish.
    rendered = []
    for i, col in enumerate(cols):
        if i < len(cols) - 1 and _ends_in_line_comment(col):
            rendered.append(f'    {col}\n    ,')
        elif i < len(cols) - 1:
            rendered.append(f'    {col},')
        else:
            rendered.append(f'    {col}')
    body = '\n'.join(rendered)
    result = f'{header} (\n{body}\n)'
    if trailer:
        result += ' ' + trailer
    return result


class DB(Shared.DC.ZRDB.THUNK.THUNKED_TM):

    opened = ''

    def open(self):
        connection = self.connection
        self.db = sqlite3.connect(connection, check_same_thread=False)
        self.opened = DateTime()

    def close(self):
        self.db.close()
        self.opened = None

    def __init__(self, connection):
        self.connection = connection
        self.open()

    def query(self, query_string, max_rows=None):
        queries = [q.strip() for q in query_string.split('\0') if q.strip()]
        if not queries:
            raise sqlite3.OperationalError('empty query')

        self._begin()
        c = self.db.cursor()
        desc = None
        result = []
        try:
            for qs in queries:
                c.execute(qs)
                d = c.description
                if d is None:
                    continue
                if desc is None:
                    desc = d
                elif d != desc:
                    raise sqlite3.OperationalError(
                        'Multiple incompatible selects in '
                        'multiple sql-statement query'
                    )

                if max_rows:
                    if not result:
                        result = c.fetchmany(max_rows)
                    elif len(result) < max_rows:
                        result = result + c.fetchmany(max_rows - len(result))
                else:
                    result.extend(c.fetchall())
            # commit inside the protected block, so a failing commit also rolls
            # back instead of leaving the transaction open for a later query
            self._finish()
        except Exception:
            # roll back partial work (including a failed commit) so a later
            # query can't commit it
            self._abort()
            raise
        finally:
            try:
                c.close()
            except Exception:
                pass

        if desc is None:
            return (), ()

        items = []
        for name, type, width, ds, p, scale, null_ok in desc:
            if type == 'NUMBER':
                if scale == 0:
                    type = 'i'
                else:
                    type = 'n'
            elif type == 'DATE':
                type = 'd'
            else:
                type = 's'
            items.append({
                'name': name,
                'type': type,
                'width': width,
                'null': null_ok,
            })

        return items, result

    def _begin(self) -> None:
        # sqlite3 opens an implicit transaction only for INSERT, UPDATE,
        # DELETE and REPLACE. A CREATE before that is committed on its own,
        # so the rollback in query() would leave the new table behind.
        # An explicit transaction puts the whole batch, including DDL, in
        # one unit. Skip when a transaction is already open.
        if not self.db.in_transaction:
            self.db.execute('BEGIN')

    def _finish(self) -> None:
        self.db.commit()

    def _abort(self) -> None:
        self.db.rollback()

    def tables(self, *args, **kw) -> list:
        self._begin()
        c = self.db.cursor()
        c.execute("SELECT name, type FROM sqlite_master WHERE type='table' or type='view'")

        result = []
        rs = c.fetchall()
        for r in rs:
            result.append({
                'TABLE_NAME': r[0],
                'TABLE_TYPE': r[1]
            })
        self._finish()
        return result

    def columns(self, table_name: str) -> list:
        self._begin()
        c = self.db.cursor()
        # PRAGMA does not accept a bound parameter for the table name, so the
        # identifier is quoted with any embedded double quotes doubled.
        ident = '"' + table_name.replace('"', '""') + '"'
        c.execute('PRAGMA table_info(%s)' % ident)
        result = []
        for cid, name, ctype, notnull, dflt, pk in c.fetchall():
            result.append({
                'name': name,
                'type': ctype,
                'notnull': notnull,
                'default': dflt,
                'pk': pk,
            })
        self._finish()
        return result

    def sqlscript(self, table_name: str) -> str:
        self._begin()
        c = self.db.cursor()
        c.execute("SELECT sql FROM sqlite_master WHERE name=?", (table_name,))
        row = c.fetchone()
        self._finish()
        return row[0] if row and row[0] else ''
