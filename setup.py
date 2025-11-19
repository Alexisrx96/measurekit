"""setup.py - Setup script for the MeasureKit package."""

from setuptools import find_packages, setup

# Read the contents of README file
with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="measurekit",
    version="0.0.002-dev",
    author="Irvin Torres",
    author_email="irvinrx1996@hotmail.com",
    description="A Python package for handling measurement units and "
    "conversions",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/irvinrx1996/measurekit",
    packages=find_packages(exclude=["tests", "tests.*"]),
    package_data={
        "measurekit": [
            "infrastructure/config/*.conf",
            "infrastructure/config/systems/*.conf",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Physics",
    ],
    python_requires=">=3.10",
    install_requires=[
        "sympy>=1.4",
        "numpy>=2.2",
        "scipy>=1.5",
        "typing-extensions>=4.15.0",
    ],
    keywords="units, measurement, conversion, physics, engineering, science",
    project_urls={
        "Bug Reports": "https://github.com/irvinrx1996/measurekit/issues",
        "Source": "https://github.com/irvinrx1996/measurekit",
        "Documentation": "https://measurekit.readthedocs.io/",
    },
    include_package_data=True,
    tests_require=[
        "pytest>=6.0.0",
        "pytest-cov>=2.12.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.12.0",
            "black>=21.5b2",
            "isort>=5.9.1",
            "mypy>=0.812",
            "flake8>=3.9.2",
        ],
        "docs": [
            "sphinx>=4.0.2",
            "sphinx-rtd-theme>=0.5.2",
        ],
    },
)
