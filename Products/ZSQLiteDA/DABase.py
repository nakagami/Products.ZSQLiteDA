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
from db import manage_DataSources
import Shared.DC.ZRDB.Connection, sys
from App.special_dtml import HTMLFile
from ExtensionClass import Base
import Acquisition

class Connection(Shared.DC.ZRDB.Connection.Connection):
    _isAnSQLConnection=1

    manage_options=Shared.DC.ZRDB.Connection.Connection.manage_options+(
        {'label': 'Browse', 'action':'manage_browse'},
        # {'label': 'Design', 'action':'manage_tables'},
        )

    manage_tables=HTMLFile('dtml/tables',globals())
    manage_browse=HTMLFile('dtml/browse',globals())

    info=None

    def tpValues(self):
        r=[]
        if not hasattr(self, '_v_database_connection'): 
            return r
        c=self._v_database_connection
        try:
            for d in c.tables(rdb=0):
                try:
                    name=d['TABLE_NAME']
                    b=TableBrowser()
                    b.__name__=name
                    b._d=d
                    b._c=c
                    # b._columns=c.columns(name)
                    try: b.icon=d['TABLE_TYPE']
                    except: pass
                    r.append(b)
                    # tables[name]=b
                except:
                    # print d['TABLE_NAME'], sys.exc_type, sys.exc_value
                    pass

        finally: pass #print sys.exc_type, sys.exc_value
        #self._v_tpValues=r
        return r

    def __getitem__(self, name):
        if name=='tableNamed':
            if not hasattr(self, '_v_tables'): self.tpValues()
            return self._v_tables.__of__(self)
        raise KeyError, name

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
        try: return self._d[name]
        except KeyError: raise AttributeError, name

class TableBrowser(Browser, Acquisition.Implicit):
    icon='what'
    Description=check=''

    def tpValues(self):
        r=[]
        tname=self.__name__
        b=SQLBrowser()
        b._parent = self 
        b._d = {'SQL': self._c.sqlscript(tname)}
        r.append(b)
        return r

    def tpId(self): return self._d['TABLE_NAME']
    def tpURL(self): return "Table/%s" % self._d['TABLE_NAME']
    def Name(self): return self._d['TABLE_NAME']
    def Type(self): return self._d['TABLE_TYPE']


class SQLBrowser(Browser):
    icon=None

    def tpId(self): return "SQL"
    def tpURL(self): return "Table/%s/SQL" % self._parent._d['TABLE_NAME']
    def Name(self): return ''
    def Type(self): return ''
    def Description(self): return self._d['SQL']
