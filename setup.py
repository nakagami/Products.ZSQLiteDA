from setuptools import setup, find_packages
import os

version = '0.6'

setup(name='Products.SQLiteDA',
      version=version,
      description="SQLite database adapter for Zope2",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        ],
      keywords='SQLite',
      author='Hajime Nakagami',
      author_email='nakagami@gmail.com',
      url='https://github.com/nakagami/Products.SQLiteDA',
      license='ZPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['Products'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'ThreadLock',
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
