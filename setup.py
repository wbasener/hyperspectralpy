from setuptools import setup, find_packages

from spec import __version__

setup(
    name='PYSPECTRA',
    version=__version__,

    url='https://github.com/wbasener/PYSPECTRA',
    author='Bill Basener',
    author_email='wb8by@virginia.edu',

    packages=find_packages(),

    entry_points={
        'console_scripts': [
            'go=spec.menu:MenuBar',
        ],
    },
)