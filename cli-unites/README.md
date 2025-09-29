# cli-unites

[![PyPI](https://img.shields.io/pypi/v/cli-unites.svg)](https://pypi.org/project/cli-unites/)
[![Changelog](https://img.shields.io/github/v/release/annavanwingerden/cli-unites?include_prereleases&label=changelog)](https://github.com/annavanwingerden/cli-unites/releases)
[![Tests](https://github.com/annavanwingerden/cli-unites/actions/workflows/test.yml/badge.svg)](https://github.com/annavanwingerden/cli-unites/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/annavanwingerden/cli-unites/blob/master/LICENSE)

unite your team with query-able project notes

## Installation

Install this tool using `pip`:
```bash
pip install cli-unites
```
## Usage

For help, run:
```bash
cli-unites --help
```
You can also use:
```bash
python -m cli_unites --help
```
## Development

To contribute to this tool, first checkout the code. Then create a new virtual environment using `uv`:
```bash
cd cli-unites
uv venv
source .venv/bin/activate
```
Now install the dependencies and test dependencies:
```bash
uv pip install -e '.[test]'
```
To run the tests:
```bash
python -m pytest
```
