from setuptools import setup
import re

requirements = ["aiohttp>=3.9.5", "aiofiles>=23.2.1"]

version = ''
with open('chatango/__init__.py') as f:
    version = re.search(
        r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE).group(1)

readme = ""

with open("README.md") as f:
    readme = f.read()

setup(name="chatango-lib",
      author="neokuze",
      url="https://github.com/neokuze/chatango-lib",
      version=version,
      packages=["chatango"],
      license="GPL-3.0",
      description="A Python library for connecting to Chatango",
      long_description=readme,
      long_description_content_type="text/markdown",
      install_requires=requirements,
      python_requires=">=3.8"
      )
