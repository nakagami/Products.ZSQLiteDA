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
from . import DA
from App.ImageFile import ImageFile

misc_={'conn': ImageFile('images/DBAdapterFolder_icon.gif', globals()),
        'table': ImageFile('images/table.gif', globals()),
}

def initialize(context):

    context.registerClass(
        DA.Connection,
        permission='Add Z SQLite Database Connections',
        constructors=(DA.manage_addZSQLiteConnectionForm,
                      DA.manage_addZSQLiteConnection)
        )
