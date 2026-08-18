"""Setup script for py_maze command-line tool."""

from setuptools import setup

setup(
    name='py_maze',
    version='1.0.1',
    description='A command-line maze generator and game',
    author='Your Name',
    py_modules=['py_maze'],
    entry_points={
        'console_scripts': [
            'py_maze=py_maze:main',
        ],
    },
    python_requires='>=3.6',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Environment :: Console',
        'Topic :: Games/Entertainment :: Puzzle Games',
    ],
)
