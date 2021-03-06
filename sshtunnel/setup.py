from setuptools import setup, find_packages
import sys, os

version = '0.0'

setup(name='sshtunnel-monitor',
      version=version,
      description="A simple ssh tunnel monitoring server",
      long_description="",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords=['ssh tunnel', 'sock proxy', 'monitor'],
      author='Senbin Yu',
      author_email='justdoit920823@gmail.com',
      url='https://github.com/justdoit0823/sshtunneld.git',
      license='GPL',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      scripts=[],
      data_files=[('/etc', ['etc/sshtunneld.conf']),
                  ('/etc/init.d', ['scripts/sshtunnel.sh'])],
      entry_points={
          'console_scripts': [
              "sshtunnel=sshtunnel:main"
          ]
      },
)
