from setuptools import setup, find_packages

setup(
    name="crypto_j_trader",
    version="0.1.0",
    packages=find_packages(include=['crypto_j_trader', 'crypto_j_trader.*']),
    python_requires=">=3.8",
    install_requires=[
        'pytest>=7.0.0',
        'pytest-asyncio>=0.25.0',
        'pytest-cov>=3.0.0',
    ],
)