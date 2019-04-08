#!/usr/bin/python3

from setuptools import setup

with open('README.md', 'r') as f:
    desc = f.read()

setup(
    name        = 'miniirc_discord',
    version     = '0.5.10',
    py_modules  = ['miniirc_discord'],
    author      = 'luk3yx',
    description = 'A Discord wrapper for miniiric.',
    license     = 'MIT',

    long_description              = desc,
    long_description_content_type = 'text/markdown',
    install_requires              = ['discord.py', 'miniirc'],

    classifiers = [
        'Intended Audience :: Developers',
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries',
    ]
)
