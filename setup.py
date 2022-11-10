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
    name='HyperspectralPy',
    summary='A GUI-based toolbox for hyperspectral image and library viewing, detection, classification, and identificaiton analysis.',
    description='A GUI-based toolbox for hyperspectral image and library viewing, detection, classification, and identificaiton analysis.',
    long_description='# HyperspectralPy [![DOI](https://zenodo.org/badge/304360097.svg)](https://zenodo.org/badge/latestdoi/304360097) Python tools with a GUI for visualization and analysis (target detection, PCA, material identification, library management) involving multispectral and hyperspectral images.    <br/><br/>    Demo on YouTube at: https://youtube.com/playlist?list=PLzUi-TW1M9mrxAZGKlCwsFzHDv4y3030B     <br/><br/>   ![](https://github.com/wbasener/PYSPECTRA/blob/main/spectralAdv/Screenshot_PYSPECTRA.png?raw=true)',
    long_description_content_type='text/markdown',

    version=__version__,

    url='https://github.com/wbasener/HyperspectralPy',
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
            'go=HyperspectralPy.spec:menu',
        ],
    },
)