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

instancepath = App.ApplicationManager.getConfiguration().instancehome
data_dir = os.path.abspath(os.path.join(instancepath, 'var', 'sqlite'))

def manage_DataSources():

    if not os.path.exists(data_dir):
        try:
            os.mkdir(data_dir)
        except:
            raise sqlite3.OperationalError(
                """
                The Zope SQLite Database Adapter requires the
                existence of the directory, <code>%s</code>.  An error
                occurred  while trying to create this directory.
                """ % data_dir)
    if not os.path.isdir(data_dir):
        raise sqlite3.OperationalError(
            """
            The Zope SQLite Database Adapter requires the
            existence of the directory, <code>%s</code>.  This
            exists, but is not a directory.
            """ % data_dir)

    return map(
        lambda d: (d,''),
        filter(lambda f, i=os.path.isfile, d=data_dir, j=os.path.join:
               i(j(d,f)),
               os.listdir(data_dir))
        )

class DB(Shared.DC.ZRDB.THUNK.THUNKED_TM):

    opened=''

    def open(self):
        connection = self.connection
        if connection != ':memory:':
            connection = os.path.join(data_dir, connection)
        self.db = sqlite3.connect(connection, check_same_thread = False)
        self.opened=DateTime()

    def close(self):
        self.db.close()
        self.opened = None

    def __init__(self,connection):
        self.connection=connection
        self.open()

    def query(self, query_string, max_rows=None):
        self._begin()
        c = self.db.cursor()

        queries=filter(None, [q.strip() for q in query_string.split('\0')])
        if not queries:
            raise sqlite3.OperationalError('empty query')
        desc=None
        result=[]
        for qs in queries:
            c.execute(qs)
            d=c.description
            if d is None: continue
            if desc is None: desc=d
            elif d != desc:
                raise sqlite3.OperationalError(
                    'Multiple incompatible selects in '
                    'multiple sql-statement query'
                    )

            if max_rows:
                if not result: result=c.fetchmany(max_rows)
                elif len(result) < max_rows:
                    result=result+c.fetchmany(max_rows-len(result))
            else:
                result = c.fetchall()

        self._finish()
        if desc is None: return (),()

        items=[]
        for name, type, width, ds, p, scale, null_ok in desc:
            if type=='NUMBER':
                if scale==0: type='i'
                else: type='n'
            elif type=='DATE':
                type='d'
            else: type='s'
            items.append({
                'name': name,
                'type': type,
                'width': width,
                'null': null_ok,
                })

        return items, result

    def _begin(self):
        #sqlite3.connection don't have begein() method.
        pass

    def _finish(self):
        self.db.commit()

    def _abort(self):
        conn.db.rollback()

    def tables(self,*args,**kw):
        self._begin()
        c = self.db.cursor()
        c.execute("SELECT name, type FROM sqlite_master WHERE type='table' or type='view'")

        result = []
        rs = c.fetchall()
        for r in rs:
            result.append({'TABLE_NAME':r[0], 'TABLE_TYPE':r[1]})
        self._finish()
        return result

    def sqlscript(self, table_name):
        self._begin()
        c = self.db.cursor()
        c.execute("SELECT sql FROM sqlite_master WHERE name='%s'" % table_name)
        sql = c.fetchone()[0]
        self._finish()
        return sql
