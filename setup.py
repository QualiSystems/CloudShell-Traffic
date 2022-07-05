"""
Package CloudShell-Traffic for distribution.
"""
from setuptools import find_packages, setup


def main() -> None:
    """Package business logic."""
    with open("requirements.txt") as requirements:
        install_requires = requirements.read().splitlines()
    with open("README.md") as readme:
        long_description = readme.read()

    setup(
        name="cloudshell-traffic",
        url="https://github.com/QualiSystems/cloudshell-traffic",
        use_scm_version={"root": ".", "relative_to": __file__, "local_scheme": "node-and-timestamp"},
        license="Apache Software License",
        author="QualiSystems",
        author_email="info@qualisystems.com",
        long_description=long_description,
        platforms="any",
        install_requires=install_requires,
        packages=find_packages(include=["cloudshell.traffic*"]),
        include_package_data=True,
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Natural Language :: English",
            "Topic :: Software Development :: Testing :: Traffic Generation",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: Apache Software License",
            "Operating System :: OS Independent",
            "Programming Language :: Python :: 3.9",
        ],
    )


if __name__ == "__main__":
    main()
