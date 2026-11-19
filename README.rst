ZSQLiteDA
=========

The ZSQLiteDA https://github.com/nakagami/Products.ZSQLiteDA provides
support for SQLite database adapter objects in the Zope 4 and 5.

Installation
-----------------

buildout.cfg::

   eggs =
       ...
       Products.ZSQLiteDA

To add or use additional databases, simply add (or link) additional
database file to your 'var/sqlite' directory.

Database directories
--------------------

By default the adapter may only create and open SQLite databases in the
instance ``var/sqlite`` directory, keeping it confined to the instance's own
data area.

To allow other directories, point the product at a list file from
``zope.conf``::

    <product-config Products.ZSQLiteDA>
        directories-file /path/to/instance/etc/zsqliteda-directories.conf
    </product-config>

The file lists one directory per line.  Blank lines and lines starting with
``#`` are ignored.  A listed directory is *mount only* (existing databases may
be opened there) unless the line is prefixed with ``create``, which also
permits creating new databases in that directory::

    # one directory per line; prefix with "create " to allow new databases
    /srv/shared/sqlite
    create /data/app databases

The instance ``var/sqlite`` directory is always allowed (create + mount) and
never needs to be listed.

.. note::

   Without a ``directories-file`` the adapter is restricted to ``var/sqlite``.
   This is stricter than older releases, which allowed opening existing
   databases from anywhere.  Connections that point outside ``var/sqlite`` must
   have their directory added to the list file.

Transactions
------------

Each query is committed on its own. The adapter does not enlist in the Zope
transaction, so a later error in the request, or a request retry, does not
roll back SQL that has already run and does not prevent it from running
again. This is the same behaviour as previous releases.
