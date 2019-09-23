from setuptools import setup

requirements = []

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

readme = ""

with open("README.md") as f:
    readme = f.read()

setup(name="chatango.py",
    author="Yado",
    url="https://github.com/neokuze/chatango-lib",
    packages=["chatango"],
    license="MIT",
    description="A Python library for connecting to Chatango",
    long_description=readme,
    long_description_content_type="text/markdown",
    install_requires=requirements,
    python_requires=">=3.6"
)
