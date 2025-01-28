from setuptools import setup, find_packages

setup(
    name="crypto_j_trader",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "numpy",
        "pandas",
        "requests",
        "websockets",
        "coinbase-advanced-py",
        "PyJWT",
        "cryptography",
    ],
    python_requires=">=3.8",
)
