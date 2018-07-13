import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="rwrap",
    version="0.0.1",
    author="Toby Slight",
    author_email="tobyslight@gmail.com",
    description="Rsync wrapper to backup/restore users on a host",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tslight/rwrap",
    packages=setuptools.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD 3 Clause",
        "Operating System :: OS Independent",
    ),
)
