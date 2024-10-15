from setuptools import setup, find_packages

from hyperspectralpy import __version__

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
    summary='A GUI-based toolbox for hyperspectral image and library viewing, detection, classification, and identificaiton analysis.',
    description='A GUI-based toolbox for hyperspectral image and library viewing, detection, classification, and identificaiton analysis.',
    long_description_content_type='text/markdown',
    long_description='[![DOI](https://zenodo.org/badge/304360097.svg)](https://zenodo.org/badge/latestdoi/304360097) Python tools with a GUI for visualization and analysis (target detection, PCA, material identification, library management) involving multispectral and hyperspectral images.  \n  -User guide at https://github.com/wbasener/hyperspectralpy/blob/main/Spectral%20Tools%20User%20Guide.pdf  \n  -To run with the GUI do "pip install hyperspectralpy" from the command line and then "import hyperspectralpy" from Python.  \n  -There is a demo on YouTube at: https://youtube.com/playlist?list=PLzUi-TW1M9mrxAZGKlCwsFzHDv4y3030B      ![](https://github.com/wbasener/hyperspectralpy/blob/main/spectralAdv/Screenshot_HySpec.png?raw=true)',
    version='1.0.2',
    url='https://github.com/wbasener/hyperspectralpy',
    author='Bill Basener',
    author_email='wb8by@virginia.edu',
    packages=['hyperspectralpy'],
    install_requires=[
        'numpy',
        'matplotlib',
        'spectral',
        'PyQt5',
        'h5py',
        'pyqtgraph',
        'scipy',
        'pygame',
        'fuzzywuzzy',
        'statsmodels',
        'Pillow',
        'pandas',
        'PyQt5_sip',
        'pyshp',
        'rasterio',
        'scikit_learn',
        'setuptools',
        'PyYAML',
        'plotly',
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

    keywords='hyperspectralpy',
    
    python_requires='>=3',

    entry_points={
        'console_scripts': [
            'go=hyperspectralpy:menu',
        ],
    },
)