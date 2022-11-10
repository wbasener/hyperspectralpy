from setuptools import setup, find_packages

from spec import __version__

extra_math = [
    'returns-decorator',
]

extra_bin = [
    *extra_math,
]

extra_dev = [
    *extra_math,
]

setup(
    name='PYSPECTRA',
    description='A graphical user interface - base software for hyperspectral image analysis.',
    version=__version__,

    url='https://github.com/wbasener/PYSPECTRA',
    author='Bill Basener',
    author_email='wb8by@virginia.edu',

    packages=find_packages(),
    
    extras_require={
        'math': extra_math,

        'bin': extra_bin,

        'dev': extra_dev,
    },

    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'Natural Language :: English'

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],

    keywords='hyperspectral',
    
    python_requires='>=3',

    entry_points={
        'console_scripts': [
            'go=sPYSPECTRA.spec:menu',
        ],
    },
)