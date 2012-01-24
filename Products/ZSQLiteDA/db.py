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
try:
    import sqlite3
except:
    from pysqlite2 import dbapi2 as sqlite3

from string import strip, split
from DateTime import DateTime
import Shared.DC.ZRDB.THUNK

from Products.ZSQLiteDA import SQLiteError, QueryError, data_dir

def manage_DataSources():

    if not os.path.exists(data_dir):
        try:
            os.mkdir(data_dir)
        except:
            raise SQLiteError, (
                """
                The Zope SQLite Database Adapter requires the
                existence of the directory, <code>%s</code>.  An error
                occurred  while trying to create this directory.
                """ % data_dir)
    if not os.path.isdir(data_dir):
        raise SQLiteError, (
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

    def open(self):
        self.db = sqlite3.connect(os.path.join(data_dir, self.connection),
                                    check_same_thread = False)
        self.opened=DateTime()

    def close(self):
        self.db.close()
        self.opened = None

    def __init__(self,connection, page_charset):
        self.connection=connection
        self.page_charset = page_charset
        self.open()

    def query(self,query_string, max_rows=None):
        self._begin()
        c = self.db.cursor()
        queries=filter(None, map(strip,split(query_string, '\0')))
        if not queries: raise 'Query Error', 'empty query'
        desc=None
        result=[]
        for qs in queries:
            if self.page_charset:
                qs = unicode(qs, self.page_charset)
            c.execute(qs)
            d=c.description
            if d is None: continue
            if desc is None: desc=d
            elif d != desc:
                raise QueryError, (
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

        if self.page_charset:
            conv_result=[]
            for r in result:
                rs = []        
                for item in r:
                    try:
                        rs.append(item.encode(self.page_charset, 'ignore'))
                    except:
                        rs.append(item)
                conv_result.append(rs)
            result = conv_result
                    
        return items, result

    def _begin(self):
        #sqlite3.connection don't have begein() method.
        pass

    def _finish(self):
        self.db.commit()

    def _abort(self):
        conn.db.rollback()
