


"""Rich console helpers for consistent CLI styling."""
from __future__ import annotations

import textwrap
from datetime import datetime
from typing import Sequence, List

from rich import box
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme
from rich.text import Text
from rich.align import Align
from rich.style import Style

from ..models.note import Note

# --- Theme & Constants ---
BG_DARK = "grey11"
INK = "white"
SUBDUED = "grey70"
ACCENT = "cyan"
SUCCESS = "bright_green"
WARNING = "yellow"
ERROR = "red"
MARGIN_RED = "red"
PAPER_LINE = "grey50"
SPIRAL = "grey30"

_THEME = Theme({
    "success": f"bold {SUCCESS}",
    "warning": WARNING,
    "error": f"bold {ERROR}",
    "note.title": f"bold {ACCENT} italic",
    "note.meta": f"{SUBDUED} italic",
    "note.id": "magenta",
    "note.tag": "bright_green",
    "ink": INK,
    "margin": MARGIN_RED,
    "paper_line": PAPER_LINE,
    "bg_dark": BG_DARK,
})

console = Console(theme=_THEME)

# --- Helper: Reactive Width ---
def get_notebook_width() -> int:
    """Return current terminal width with safety margin."""
    return max(80, console.size.width - 4)

def _make_margin_with_content(content: Group, margin_char: str = "│", style: str = "margin") -> Table:
    """Render content with a fake left-hand margin."""
    grid = Table.grid(padding=(0, 1), expand=True)
    grid.add_column("margin", width=1, no_wrap=True)
    grid.add_column("content", ratio=1)

    # For each renderable in the Group, create a corresponding margin line
    for item in content.renderables:
        # Determine number of lines the item takes
        console = Console(record=True, width=get_notebook_width()-4)
        console.print(item)
        lines = console.export_text().splitlines()

        # For each line, add a row with margin and the line
        for line in lines:
            grid.add_row(Text(margin_char, style=style), Text(line))

    return grid
# --- Core UI Building Blocks ---

def _get_app_header_content() -> Group:
    """Returns the renderable header: spiral + centered title."""
    width = get_notebook_width()
    spiral = _spiral_header(width=width - 4, holes=12)  # leave panel padding
    title = Text.assemble(
        ("✎ ", f"{ACCENT} bold"),
        ("cli-unites", f"{ACCENT} bold italic"),
        ("  ", ""),
        ("unite your team with queryable notes", f"{SUBDUED} italic"),
    )
    centered_title = Align.center(title)
    return Group(spiral, centered_title)

def _get_note_panel_content(note: Note) -> Group:
    """Returns the renderable content for a single note panel."""
    width = get_notebook_width()
    created = _format_timestamp(note.created_at)
    tags = ", ".join(note.tags) if note.tags else "—"
    team = note.team_id or "—"
    git = f"{note.git_branch} @ {note.git_commit[:7]}" if note.git_commit and note.git_branch else "—"

    title_text = Text(f"✎ {note.title}", style=Style.parse(f"bold {ACCENT} italic"))
    meta = Text.assemble(
        Text("id ", style=Style.parse(f"{SUBDUED} italic")),
        Text(note.id[:8], style="magenta"),
        Text("  •  tags ", style=Style.parse(f"{SUBDUED} italic")),
        Text(tags, style="bright_green"),
        Text("  •  team ", style=Style.parse(f"{SUBDUED} italic")),
        Text(team, style=f"{INK} italic"),
        Text("\n"),
        Text("created ", style=Style.parse(f"{SUBDUED} italic")),
        Text(created, style=f"{INK} italic"),
        Text("  •  git ", style=Style.parse(f"{SUBDUED} italic")),
        Text(git, style=f"{INK} italic"),
    )
    body_content = note.body.strip() or "(empty)"
    body = _ruled_lines(body_content, wrap_width=width - 12)

    return Group(title_text, Text(" "), meta, Text(" "), body)

def _get_notes_table_content(
    notes: Sequence[Note],
    show_index: bool = False,
    include_team: bool = True,
    include_summary: bool = False,
) -> Table:
    """Returns a Table renderable for a list of notes with lined-paper style."""
    width = get_notebook_width()

    table = Table(
        box=box.MINIMAL,  # no vertical lines
        highlight=True,
        show_header=True,
        header_style=Style.parse(f"bold {ACCENT} italic"),
        expand=True,
        style=f"on {BG_DARK}",
        show_lines=True
    )

    # --- Columns ---
    columns: list[tuple[str, str | Style, int | None, bool, int]] = []

    if show_index:
        columns.append(("#", Style.parse(f"{SUBDUED} italic"), None, True, 0))
    columns.append(("ID", "magenta", 9, True, 0))
    columns.append(("Title", Style.parse(f"bold {ACCENT} italic"), None, False, 30))
    if include_summary:
        columns.append(("Summary", f"{INK} italic", None, False, 40))
    columns.append(("Tags", "bright_green", None, False, 20))
    if include_team:
        columns.append(("Team", f"{INK} italic", None, True, 10))
    columns.append(("Created", Style.parse(f"{SUBDUED} italic"), None, True, 0))
    columns.append(("Git", Style.parse(f"{SUBDUED} italic"), None, True, 0))

    # Add columns to table
    for col_name, col_style, col_width, no_wrap, ratio in columns:
        table.add_column(
            col_name,
            style=col_style,
            no_wrap=no_wrap,
            width=col_width,
            ratio=ratio
        )

    # --- Rows ---
    for idx, note in enumerate(notes, start=1):
        created = _format_timestamp(note.created_at)
        tags = ", ".join(note.tags) if note.tags else "—"
        team = note.team_id or "—"
        git = f"{note.git_branch} @ {note.git_commit[:7]}" if note.git_commit and note.git_branch else "—"
        summary = _summarise(note) if include_summary else None

        row: list[str | Text] = []
        if show_index:
            row.append(str(idx))
        row.extend([note.id[:8], Text(note.title, overflow="fold")])
        if include_summary and summary is not None:
            row.append(Text(summary, overflow="fold"))
        row.append(Text(tags, overflow="fold"))
        if include_team:
            row.append(team)
        row.extend([created, git])
        table.add_row(*row)

    return table

def _get_status_panel_content(status_lines: Sequence[str], context_lines: Sequence[str] | None = None) -> Group:
    """Returns the renderable content for a status panel."""
    width = get_notebook_width()
    body_lines = list(status_lines)
    if context_lines:
        body_lines.append("")
        body_lines.extend(context_lines)

    body_text = "\n".join(body_lines)

    panel = Panel(
        Text.from_markup(body_text),
        title=Text("status", style=Style.parse(f"bold {ACCENT} italic")),
        box=box.ROUNDED,
        border_style=ACCENT,
        style=f"on {BG_DARK}",
        padding=(1, 2),
    )
    return Group(Text(""), panel)
def render_notebook_page(content_items: list, page_title: str = "cli-unites") -> Panel:
    """
    Render a notebook page with:
      - continuous left-hand red margin
      - content (tables, panels, headers) intact
      - terminal-width responsive layout
    """
    page_content = Group(*content_items)

    # --- Measure content height without printing ---
    measure_console = Console(record=True, width=get_notebook_width() - 4)
    measure_console.begin_capture()          # capture output internally
    measure_console.print(page_content)
    content_height = measure_console.height
    measure_console.end_capture()            # discard captured output

    # --- Grid: left-hand margin + main content ---
    grid = Table.grid(padding=(0, 1), expand=True)
    grid.add_column("margin", width=1, no_wrap=True)
    grid.add_column("content", ratio=1)

    # --- Red vertical margin ---
    margin = Text("│\n" * content_height, style="margin")
    grid.add_row(margin, page_content)

    # --- Final notebook panel ---
    return Panel(
        grid,
        title=Text(f"✎ {page_title}", style=Style.parse(f"bold {ACCENT} italic")),
        border_style=ACCENT,
        box=box.ROUNDED,
        style=f"on {BG_DARK}",
        padding=(1, 2),
        width=get_notebook_width(),
        expand=False
    )

# --- High-Level Display Functions ---

def display_notes_list(notes: Sequence[Note], **kwargs):
    """Prints the display for a list of notes."""
    header = _get_app_header_content()
    table = _get_notes_table_content(notes, **kwargs)
    page = render_notebook_page([header, table], page_title="notes list")
    console.print(page)

def display_note_view(note: Note):
    """Prints the display for a single note."""
    header = _get_app_header_content()
    note_content = _get_note_panel_content(note)
    page = render_notebook_page([header, note_content], page_title=f"note: {note.id[:8]}")
    console.print(page)

def render_simple_panel(title: str, content: str | Group) -> Panel:
    """Renders a simple, clean panel for interactive flows."""
    return Panel(
        content,
        title=Text(f"◇ {title}", style=Style.parse(f"bold {ACCENT} italic")),
        border_style=ACCENT,
        box=box.ROUNDED,
        style=f"on {BG_DARK}",
        padding=(1, 2),
        width=get_notebook_width(),
    )

def display_note_add_success(note: Note, git_context: dict, config: dict):
    """Prints the success view after adding a note."""
    header = _get_app_header_content()
    note_content = _get_note_panel_content(note)
    
    status_lines = [f"[success]Saved note {note.id[:8]} for {note.title}[/success]"]
    context_bits = []
    if config.get("team_id"):
        context_bits.append(f"Team: [note.title]{config['team_id']}[/note.title]")
    if git_context.get("branch"):
        context_bits.append(f"Branch: {git_context['branch']}")
    if git_context.get("commit"):
        context_bits.append(f"Commit: {git_context['commit'][:7]}")
        
    status_content = _get_status_panel_content(status_lines, context_bits)
    
    page = render_notebook_page([header, note_content, status_content], page_title="note saved")
    console.print(page)

# --- Low-Level Helpers & Primitives ---

def _print_status(prefix: str, color: str, message: str):
    console.print(Text.assemble(
        Text(prefix, style=Style.parse(f"bold {color}")),
        Text(message, style="ink"),
    ))

def print_success(message: str) -> None:
    _print_status("✓ ", SUCCESS, message)

def print_warning(message: str) -> None:
    _print_status("! ", WARNING, message)

def print_error(message: str) -> None:
    _print_status("✗ ", ERROR, message)

def set_fullscreen_background():
    """Set the terminal background to dark grey for full-screen mode."""
    import sys, os
    console.clear()
    sys.stdout.write("\033[48;5;233m")
    sys.stdout.flush()
    try:
        rows, cols = os.popen('stty size', 'r').read().split()
        for _ in range(int(rows)):
            sys.stdout.write(" " * int(cols) + "\n")
    except:
        pass  # Fallback for non-tty environments
    sys.stdout.write("\033[H")
    sys.stdout.flush()

def _spiral_header(width: int = 64, holes: int = 8) -> Text:
    """Top spiral ring row: ○   ○   ○ … (faint, retro-lab aesthetic)"""
    spacing = max(2, (width // holes) - 1)
    ring = "○"
    slots = (ring + " " * spacing) * holes
    return Text(slots[:width], style=SPIRAL)

def _ruled_lines(content: str, wrap_width: int = 76) -> Group:
    """Wraps text to width and overlays faint ruled lines between paragraphs."""
    lines = []
    paragraphs = content.split("\n")
    for i, para in enumerate(paragraphs):
        if not para.strip():
            lines.append(Text(" "))
            continue
        wrapped = textwrap.wrap(para, width=wrap_width, replace_whitespace=False)
        for chunk in wrapped:
            lines.append(Text(chunk, style="ink"))
        if i < len(paragraphs) - 1 and para.strip():
            lines.append(Text("─" * min(wrap_width, 80), style="paper_line"))
    return Group(*lines)

def _format_timestamp(value: datetime) -> str:
    if not isinstance(value, datetime): return ""
    if value.tzinfo is None: return value.strftime("%Y-%m-%d %H:%M")
    return value.astimezone().strftime("%Y-%m-%d %H:%M")

def _summarise(note: Note) -> str:
    text = note.body.strip()
    if not text: return "—"
    first_line = text.splitlines()[0].strip()
    if len(first_line) <= 80: return first_line
    return f"{first_line[:77]}…"



