#!/usr/bin/env python3
"""
Setup script for crypto_j_trader package.
"""

from setuptools import setup, find_packages

setup(
    name="crypto_j_trader",
    version="1.0.0",
    description="Cryptocurrency trading bot with dynamic portfolio management",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "numpy>=1.21.0",
        "pandas>=1.3.0",
        "websockets>=10.0",
        "coinbase-advanced-py>=1.0.0",
        "ratelimit>=2.2.1",
        "backoff>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "mypy>=0.900",
            "pylint>=2.12.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "crypto-trader=crypto_j_trader.src.trading.trading_core:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
)