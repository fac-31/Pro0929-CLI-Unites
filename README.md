# cli-unites
unite your team with query-able project notes

## Development

To contribute to this tool, first checkout the code. Then create a new virtual environment using `uv`:
```bash
uv venv
source .venv/bin/activate
```
Now install the dependencies and test dependencies:
```bashn
uv pip install -e '.[test]'
```
To run the tests:
```bash
'python -m pytest'
```

If you're working and need to re-sync dependencies etc - type 'uv sync'

To see  options, run notes --help

