from setuptools import setup, find_packages

from HySpec import __version__

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
    name='HySpec',
    summary='A GUI-based toolbox for hyperspectral image and library viewing, detection, classification, and identificaiton analysis.',
    description='A GUI-based toolbox for hyperspectral image and library viewing, detection, classification, and identificaiton analysis.',
    long_description_content_type='text/markdown',
    long_description='[![DOI](https://zenodo.org/badge/304360097.svg)](https://zenodo.org/badge/latestdoi/304360097) Python tools with a GUI for visualization and analysis (target detection, PCA, material identification, library management) involving multispectral and hyperspectral images.  \n  -User guide at https://github.com/wbasener/HySpec/blob/main/Spectral%20Tools%20User%20Guide.pdf  \n  -To run with the GUI do "pip install HySpec" from the command line and then "import HySpec" from Python.  \n  -There is a demo on YouTube at: https://youtube.com/playlist?list=PLzUi-TW1M9mrxAZGKlCwsFzHDv4y3030B      ![](https://github.com/wbasener/HySpec/blob/main/spectralAdv/Screenshot_HySpec.png?raw=true)  \n  NOTE: Dependency checking still in progress.',


    version=__version__,

    url='https://github.com/wbasener/HySpec',
    author='Bill Basener',
    author_email='wb8by@virginia.edu',

    packages=find_packages(),
    
    install_requires=[
        'sys',
        'os',
        'numpy',
        'matplotlib',
        'spectral',
        'PyQt5',
        'h5py',
        'math',
        'pyqtgraph',
        'pickle',
        'csv',
        'sys',
        'sklearn',
        'scipy',
        'pygame',
        'functools',
        'time',
        'functools',
        'copy',
        'fuzzywuzzy',
        'operator',
        'statsmodels',
        'distutils',
        'timeit',
        'PIL',
    ],

    #extras_require={
    #    'math': extra_math,
    #    'bin': extra_bin,
    #    'dev': extra_dev,
    #},

    classifiers = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],

    keywords='hyperspectral',
    
    python_requires='>=3',

    entry_points={
        'console_scripts': [
            'go=HySpec:menu',
        ],
    },
)