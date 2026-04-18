from setuptools import setup, find_packages

from shipping_integration import __version__

setup(
    name="shipping_integration",
    version=__version__,
    description="eShipper rate calculation for IPCONNEX",
    author="IPCONNEX",
    author_email="dev@ipconnex.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=[],
)
