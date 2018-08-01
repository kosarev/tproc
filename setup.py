#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name='tproc',
    version='1.0a0',
    packages=[],
    scripts=['tproc.py'],
    description='A small yet powerful text processor',
    author='Ivan Kosarev',
    author_email='ivan@kosarev.info',
    license='MIT',
    keywords='text macro processing',
    url='https://github.com/kosarev/tproc',
    entry_points={
        'console_scripts': [
            'tproc = tproc:main',
        ],
    },
    test_suite='tests',
    classifiers=[
        'Development Status :: 1 - Planning',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Documentation',
        'Topic :: Software Development',
        'Topic :: Software Development :: Localization',
        'Topic :: Software Development :: Pre-processors',
        'Topic :: Software Development :: User Interfaces',
        'Topic :: Text Editors',
        'Topic :: Text Editors :: Text Processing',
        'Topic :: Text Editors :: Word Processors',
        'Topic :: Text Processing',
        'Topic :: Text Processing :: General',
        'Topic :: Text Processing :: Markup',
        'Topic :: Utilities',
    ],
)
