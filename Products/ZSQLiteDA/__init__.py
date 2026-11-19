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
# Single source of truth for the package version: setup.py parses this
# line, DA.py imports it for the ZMI display. Must stay above the DA
# import -- DA.py does ``from . import __version__`` while this module
# is still initialising.
__version__ = '0.9.0'

from . import DA
from App.ImageFile import ImageFile

misc_ = {
    'conn': ImageFile('images/DBAdapterFolder_icon.gif', globals()),
    'table': ImageFile('images/table.gif', globals()),
}


def initialize(context):

    context.registerClass(
        DA.Connection,
        permission='Add Z SQLite Database Connections',
        constructors=(DA.manage_addZSQLiteConnectionForm,
                      DA.manage_addZSQLiteConnection)
        )
