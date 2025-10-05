# cli-unites

[![PyPI](https://img.shields.io/pypi/v/cli-unites.svg)](https://pypi.org/project/cli-unites/)
[![Changelog](https://img.shields.io/github/v/release/fac-31/Pro0929-CLI-Unites?include_prereleases&label=changelog)](https://github.com/fac-31/Pro0929-CLI-Unites/releases)
[![Tests](https://github.com/fac-31/Pro0929-CLI-Unites/actions/workflows/test.yml/badge.svg)](https://github.com/fac-31/Pro0929-CLI-Unites/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/fac-31/Pro0929-CLI-Unites/blob/master/LICENSE)

**Unite your team with query-able project notes**

A command-line tool for capturing, organizing, and searching project knowledge across your team. Built with SQLite for offline-first operation and automatic git context capture.

## Features

- 📝 **Add Notes**: Capture project learnings with automatic git context
- 🔍 **Search**: Find notes by keyword across title, body, and tags
- 📋 **List & Filter**: View notes with tag filtering and team isolation
- 👥 **Team Management**: Organize notes by team with configurable defaults
- 🔐 **Authentication**: Optional Supabase integration for team sync
- 📊 **Activity Feed**: See recent notes and team activity
- 🎨 **Rich UI**: Beautiful terminal output with Rich formatting

## Installation

### From PyPI (when published)
```bash
pip install cli-unites
```

### From Source
```bash
git clone https://github.com/fac-31/Pro0929-CLI-Unites.git
cd Pro0929-CLI-Unites
uv venv
source .venv/bin/activate
uv pip install -e '.[test]'
```

## Quick Start

1. **Add your first note**:
   ```bash
   notes add "Project Setup" --body "How to set up the development environment"
   ```

2. **Set your team**:
   ```bash
   notes team --set "my-team"
   ```

3. **Search for notes**:
   ```bash
   notes search "setup"
   ```

4. **List recent activity**:
   ```bash
   notes activity
   ```

## Commands

### `notes add <title>`
Add a new note to your knowledge base.

**Options:**
- `--body TEXT`: Note content (or read from stdin)
- `--allow-empty`: Allow saving empty notes
- `-t, --tag TEXT`: Add tags (can be used multiple times)

**Examples:**
```bash
# Add with body
notes add "Bug Fix" --body "Fixed the authentication issue" --tag bug --tag urgent

# Add from stdin
echo "Important meeting notes" | notes add "Team Meeting"

# Interactive editor
notes add "Design Decision"  # Opens your default editor
```

### `notes search <query>`
Search notes by keyword across title, body, and tags.

**Options:**
- `--all-teams`: Search across all teams (not just current team)

**Examples:**
```bash
notes search "authentication"
notes search "bug" --all-teams
```

### `notes list`
List stored notes with optional filtering.

**Options:**
- `-t, --tag TEXT`: Filter by tag
- `-n, --limit INT`: Limit number of results
- `--team TEXT`: Show notes for specific team

**Examples:**
```bash
notes list --tag important
notes list --limit 10
notes list --team "frontend-team"
```

### `notes activity`
Show recent notes for quick overview.

**Options:**
- `--team TEXT`: Show activity for specific team
- `-n, --limit INT`: Number of notes to show (default: 5)

### `notes team`
Manage team configuration.

**Options:**
- `--set TEXT`: Set default team ID
- `--recent`: Show recently used team IDs

**Examples:**
```bash
notes team --set "my-team"
notes team --recent
notes team  # Show current team
```

### `notes auth`
Configure authentication and sync settings.

**Options:**
- `--token TEXT`: CLI auth token
- `--team-id TEXT`: Default team identifier
- `--supabase-url TEXT`: Supabase project URL
- `--supabase-key TEXT`: Supabase service role key
- `--show`: Show current auth configuration

## Data Storage

- **Local Database**: SQLite database stored in `~/.cli-unites/notes.db`
- **Git Integration**: Automatically captures commit hash, branch, and project path
- **Team Isolation**: Notes can be organized by team with configurable defaults
- **Offline First**: Works completely offline; sync is optional

## Configuration

Configuration is stored in `~/.cli-unites/config.json`. Key settings:

- `team_id`: Default team for new notes
- `supabase_url` & `supabase_key`: Optional sync configuration
- `first_run_completed`: Onboarding completion flag

## Environment Variables

- `CLI_UNITES_DB_PATH`: Override database location
- `CLI_UNITES_DISABLE_GIT`: Set to "1" to disable git context capture
- `CLI_UNITES_SKIP_ONBOARDING`: Set to "1" to skip first-run setup

## Development

### Setup
```bash
# Clone and setup
git clone https://github.com/fac-31/Pro0929-CLI-Unites.git
cd Pro0929-CLI-Unites

# Create virtual environment with uv
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -e '.[test]'
```

### Running Tests
```bash
python -m pytest
```

### Sync Dependencies
```bash
uv sync
```

### Project Structure
```
cli_unites/
├── commands/          # CLI command implementations
├── core/             # Core functionality (db, config, git, etc.)
├── models/           # Data models
└── cli.py           # Main CLI entry point
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## License

Apache 2.0 - see [LICENSE](LICENSE) for details.

## Authors

- Anna van Wingerden
- Jaz Maslen  
- Rich Couzens



nb.

to see onboarding run this in your terminal to set onboarding flag to false: 

source .venv/bin/activate
python - <<'PY'
from cli_unites.core.config import ConfigManager
manager = ConfigManager()
current = manager.get("first_run_completed")
manager.set("first_run_completed", not current)
print(f"first_run_completed toggled to {not current}")
PY
