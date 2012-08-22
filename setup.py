#!/usr/bin/python -tt

from setuptools import setup

setup(
    name = 'python-ponyvirt',
    version = '1',
    author = 'The PonyCloud Team',
    description = ('high-level libvirt bindings'),
    license = 'proprietary',
    keywords = 'virtualization',
    url = 'http://github.com/ponycloud/python-ponyvirt',
    packages=['ponyvirt'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Topic :: System :: Emulators',
        'License :: Other/Proprietary License',
    ],
)


# vim:set sw=4 ts=4 et:
# -*- coding: utf-8 -*-
