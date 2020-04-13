from pathlib import Path

from setuptools import setup, find_packages

THIS_DIR = Path(__file__).parent


setup(
    name="globus-transfer",
    version="0.0.1",
    author="Josh Karpel",
    author_email="josh.karpel@gmail.com",
    description="A utility for initiating Globus transfers from the command line",
    long_description=Path("README.md").read_text(),
    long_description_content_type="text/markdown",
    url="https://github.com/JoshKarpel/globus-transfer",
    py_modules=find_packages(),
    entry_points={"console_scripts": ["globus = globus.cli:cli"]},
    install_requires=Path("requirements.txt").read_text().splitlines(),
)
