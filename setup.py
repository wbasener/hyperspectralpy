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
    name='hyperspectralpy',
    description='A GUI-based toolbox for hyperspectral image and library viewing, detection, classification, and identificaiton analysis.',
    version=__version__,

    url='https://github.com/wbasener/hyperspectralpy',
    author='Bill Basener',
    author_email='wb8by@virginia.edu',

    packages=find_packages(),
    
    extras_require={
        'math': extra_math,

        'bin': extra_bin,

        'dev': extra_dev,
    },

    classifiers = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],

    keywords='hyperspectral',
    
    python_requires='>=3',

    entry_points={
        'console_scripts': [
            'go=hyperspectralpy.spec:menu',
        ],
    },
)