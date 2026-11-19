Changelog
=========

0.9.0 (unreleased)
------------------

Security
~~~~~~~~

- Database directories are restricted to an allowlist. Without a
  ``directories-file`` in the ``Products.ZSQLiteDA`` product config, only
  the instance ``var/sqlite`` directory can be used. Older releases could
  open an existing database from any absolute path. A listed directory is
  mount-only unless its line is prefixed with ``create``.
- A database file name must be a plain file name. Paths, ``.`` and ``..``,
  and control characters are rejected.
- A non-empty file is opened only when it starts with a SQLite header.
  Empty files are still accepted, so a new database can be created.

Queries
~~~~~~~

- A Z SQL Method can run several statements in one call by putting
  ``<dtml-var sql_delimiter>`` between them. Zope renders that variable
  as a null byte, and the adapter runs the pieces as one batch. Rows
  from every ``SELECT`` come back together, also when the batch contains
  ``INSERT``, ``UPDATE`` or ``DELETE``, as long as the columns match.
  If one statement fails, the whole batch is rolled back.
- Each query still commits on its own and does not join the Zope
  transaction. A later error or a request retry neither rolls the SQL
  back nor skips it.

ZMI
~~~

- The Add, Properties, Status and Browse tabs follow the Zope 4 ZMI
  layout.
- The Add and Properties forms use the existing database or create a new
  one. Properties can switch the allowlisted directory and refresh the
  database list for that directory.
- The Browse tab lists tables and views in an accordion and shows a
  formatted ``CREATE`` statement that can be copied. A ``--`` comment no
  longer swallows the comma before the next column.
- The Properties tab shows the package version.

Packaging
~~~~~~~~~

- Declare ``Zope >= 4`` and require Python 3.7 or newer.
- Drop ``Products.ZSQLiteDA-configure.zcml``. It included a package that
  does not exist.
- Ship this changelog in the sdist.
