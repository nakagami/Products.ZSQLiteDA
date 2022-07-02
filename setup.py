from setuptools import setup, find_packages


version = '0.7.4'

setup(name='Products.ZSQLiteDA',
      version=version,
      description="SQLite database adapter for Zope4",
      long_description=open("README.rst").read(),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Zope :: 4",
        "Framework :: Zope :: 5",
        "License :: OSI Approved :: Zope Public License",
        ],
      keywords='SQLite',
      author='Hajime Nakagami',
      author_email='nakagami@gmail.com',
      url='https://github.com/nakagami/Products.ZSQLiteDA',
      license='ZPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['Products'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
        'Products.ZSQLMethods',
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
