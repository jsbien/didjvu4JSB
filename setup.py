#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
from pathlib import Path


ROOT_DIRECTORY = Path(__file__).parent.resolve()


def get_version():
    changelog = ROOT_DIRECTORY / 'doc' / 'changelog'
    with open(changelog, mode='r') as fd:
        line = fd.readline()
    return line.split()[1].strip('()')


setup(
    name='didjvu',
    description='DjVu encoder with foreground/background separation (Python 3 fork) ',
    version=get_version(),
    license='GNU GPL 2',
    long_description=(ROOT_DIRECTORY / 'README.rst').read_text(encoding='utf-8'),
    long_description_content_type='text/x-rst',
    author='Jakub Wilk, FriedrichFröbel (Python 3)',
    url='https://github.com/FriedrichFroebel/didjvu/',
    packages=find_packages(
        where='.',
        exclude=['tests', 'tests.*', 'private', 'private.*']
    ),
    include_package_data=True,
    python_requires=">=3.6, <4",
    install_requires=[
        'gamera>=4.0.0',
        'Pillow',
    ],
    extras_require={
        'dev': [
            'coverage',
            'flake8',
            'pep8-naming',
        ],
        'docs': [
            'docutils',
            'pygments',
        ]
    },
    entry_points={
        'console_scripts': [
            'didjvu=didjvu.__main__:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Text Processing',
        'Topic :: Multimedia :: Graphics',
    ]
)
