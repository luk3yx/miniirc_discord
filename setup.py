#!/usr/bin/python3

from setuptools import setup

with open('README.md', 'r') as f:
    desc = f.read()

setup(
    name        = 'miniirc_discord',
    version     = '0.5.12',
    py_modules  = ['miniirc_discord'],
    author      = 'luk3yx',
    description = 'A Discord wrapper for miniirc.',
    license     = 'MIT',

    long_description              = desc,
    long_description_content_type = 'text/markdown',
    install_requires              = ['discord.py>=1.0.0,<2', 'miniirc'],
    python_requires               = '>=3.5',

    classifiers = [
        'Intended Audience :: Developers',
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries',
    ]
)
