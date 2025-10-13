"""Rich console helpers for consistent CLI styling."""
from __future__ import annotations

import textwrap
from datetime import datetime
from typing import Sequence

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme
from rich.markup import escape
from rich.text import Text
from rich.align import Align
from rich.padding import Padding
from rich.style import Style
from rich.layout import Layout
from rich.live import Live
from rich.screen import Screen

from ..models.note import Note

# --- Minimalist terminal-notebook theme: sleek & focused ---
BG_DARK = "grey11"       # dark background for panels
INK = "white"            # primary text - crisp white
SUBDUED = "grey70"       # metadata - lighter for contrast
ACCENT = "cyan"          # headings - bright cyan
SUCCESS = "bright_green"
WARNING = "yellow"
ERROR = "red"
MARGIN_RED = "red"       # notebook left margin - bright red
PAPER_LINE = "grey50"    # ruled lines - white/grey
SPIRAL = "grey30"        # faint spiral header

_THEME = Theme(
    {
        "success": f"bold {SUCCESS}",
        "warning": WARNING,
        "error": f"bold {ERROR}",
        "note.title": f"bold {ACCENT} italic",  # italic for retro feel
        "note.meta": f"{SUBDUED} italic",       # subtle italic
        "note.id": "magenta",
        "note.tag": "bright_green",
        "ink": INK,
        "margin": MARGIN_RED,
        "paper_line": PAPER_LINE,
        "bg_dark": BG_DARK,
    }
)

console = Console(theme=_THEME)


def set_fullscreen_background():
    """Set the terminal background to dark grey for full-screen mode."""
    import sys
    import os
    import time
    
    # Clear screen first
    sys.stdout.write("\033[2J\033[H")  # Clear screen and move to home
    sys.stdout.flush()
    
    # Set background color to dark grey
    # ESC[48;5;Nm sets background to 256-color palette color N
    # Color 233-235 are dark greys in the 256-color palette
    sys.stdout.write("\033[48;5;233m")
    sys.stdout.flush()
    
    # Fill the entire screen with the background color
    # Get terminal size
    try:
        rows, cols = os.popen('stty size', 'r').read().split()
        rows, cols = int(rows), int(cols)
    except:
        rows, cols = 24, 80  # Fallback
    
    # Print empty lines to fill screen with background
    for _ in range(rows):
        sys.stdout.write(" " * cols + "\n")
    sys.stdout.flush()
    
    # Move cursor back to top
    sys.stdout.write("\033[H")
    sys.stdout.flush()
    
    # Small delay to let terminal render
    time.sleep(0.1)


def print_app_header():
    """Print the app header with spiral for full-screen mode."""
    import sys
    
    width = console.width
    spiral = spiral_header(width=width - 4, holes=12)
    
    title = Text.assemble(
        ("✎ ", f"{ACCENT} bold"),
        ("cli-unites", f"{ACCENT} bold italic"),
        ("  ", ""),
        ("unite your team with queryable notes", f"{SUBDUED} italic"),
    )
    
    header_panel = Panel(
        Group(spiral, Text(""), Align.center(title)),
        border_style=ACCENT,
        style=f"on {BG_DARK}",
        box=box.ROUNDED,
        padding=(0, 2),
    )
    
    console.print(header_panel)
    console.print()  # Add spacing
    sys.stdout.flush()  # Force flush output


def spiral_header(width: int = 64, holes: int = 8) -> Text:
    """Top spiral ring row: ○   ○   ○ … (faint, retro-lab aesthetic)"""
    spacing = max(2, (width // holes) - 1)
    ring = "○"
    slots = (ring + " " * spacing) * holes
    return Text(slots[:width], style=SPIRAL)


def ruled_lines(content: str, wrap_width: int = 76) -> Group:
    """
    Wraps text to width and overlays faint ruled lines between paragraphs.
    Simulates notebook paper ruling.
    """
    lines = []
    paragraphs = content.split("\n")
    
    for i, para in enumerate(paragraphs):
        if not para.strip():
            lines.append(Text(" "))
            continue
        
        wrapped = textwrap.wrap(para, width=wrap_width, replace_whitespace=False)
        for chunk in wrapped:
            lines.append(Text(chunk, style=INK))
        
        # Add faint ruled line between paragraphs (but not after the last one)
        if i < len(paragraphs) - 1 and para.strip():
            lines.append(Text("─" * min(wrap_width, 80), style=PAPER_LINE))
    
    return Group(*lines)


def notebook_frame(inner_renderable, title: str = "note", width: int = 84) -> Panel:
    """
    A panel with spiral top and red margin, like a notebook page.
    """
    # Create grid with margin and content
    grid = Table.grid(padding=(0, 1))
    grid.expand = True
    grid.add_column("margin", width=1, ratio=0, no_wrap=True)
    grid.add_column("content", ratio=1)
    
    # Red margin rule (notebook margin)
    margin_col = Text("│", style=MARGIN_RED)
    grid.add_row(margin_col, inner_renderable)
    
    # Spiral header at top
    header = spiral_header(width=width - 2)
    
    group = Group(
        Align.left(header),
        grid
    )
    
    return Panel(
        group,
        title=Text(f"✎ {title}", style=f"{ACCENT} italic bold"),
        border_style=ACCENT,
        box=box.ROUNDED,
        style=f"on {BG_DARK}",  # dark background
        padding=(1, 2),
        expand=False
    )


def print_success(message: str) -> None:
    console.print(Text.assemble(("✓ ", f"bold {SUCCESS}"), (message, INK)))


def print_warning(message: str) -> None:
    console.print(Text.assemble(("! ", f"bold {WARNING}"), (message, INK)))


def print_error(message: str) -> None:
    console.print(Text.assemble(("✗ ", f"bold {ERROR}"), (message, INK)))


def render_note_panel(note: Note) -> Panel:
    """
    Detailed note view with notebook styling: spiral, margin, ruled lines.
    """
    created = _format_timestamp(note.created_at)
    tags = ", ".join(note.tags) if note.tags else "—"
    team = note.team_id or "—"
    git = f"{note.git_branch} @ {note.git_commit[:7]}" if note.git_commit and note.git_branch else "—"
    
    # Title with handwritten feel - cyan italic
    title_text = Text(f"✎ {note.title}", style=f"{ACCENT} italic bold")
    
    # Metadata line with subtle symbols - italicized
    meta = Text.assemble(
        ("id ", f"{SUBDUED} italic"), (note.id[:8], "magenta"),
        ("  •  tags ", f"{SUBDUED} italic"), (tags, "bright_green"),
        ("  •  team ", f"{SUBDUED} italic"), (team, f"{INK} italic"),
        ("\n", ""),
        ("created ", f"{SUBDUED} italic"), (created, f"{INK} italic"),
        ("  •  git ", f"{SUBDUED} italic"), (git, f"{INK} italic"),
    )
    
    # Body with ruled lines
    body_content = note.body.strip() or "(empty)"
    body = ruled_lines(body_content, wrap_width=76)
    
    # Combine everything
    inner = Group(
        title_text,
        Text(" "),
        meta,
        Text(" "),
        body
    )
    
    return notebook_frame(inner_renderable=inner, title="note", width=84)


def render_notes_table(
    notes: Sequence[Note],
    show_index: bool = False,
    include_team: bool = True,
    include_summary: bool = False,
) -> Table:
    """
    List view with notebook margin and ruled lines between rows.
    """
    # Outer grid with red margin
    outer = Table.grid(expand=True)
    outer.add_column("margin", width=1, ratio=0)
    outer.add_column("content", ratio=1)
    
    # Add spiral header
    header = spiral_header(width=80, holes=10)
    spiral_row = Table.grid(expand=True)
    spiral_row.add_column("margin", width=1)
    spiral_row.add_column("header", ratio=1)
    spiral_row.add_row(Text(" ", style=MARGIN_RED), header)
    
    # Inner table with actual content - dark background
    table = Table(box=None, highlight=True, show_header=True, 
                  header_style=f"{ACCENT} bold italic", expand=True,
                  style=f"on {BG_DARK}")
    
    if show_index:
        table.add_column("#", style=f"{SUBDUED} italic", no_wrap=True, justify="right")
    table.add_column("ID", style="magenta", no_wrap=True)
    table.add_column("Title", style=f"{ACCENT} bold italic", overflow="fold", min_width=15)
    if include_summary:
        table.add_column("Summary", style=f"{INK} italic", overflow="fold")
    table.add_column("Tags", style="bright_green", overflow="fold")
    if include_team:
        table.add_column("Team", style=f"{INK} italic", no_wrap=True)
    table.add_column("Created", style=f"{SUBDUED} italic", no_wrap=True)
    table.add_column("Git", style=f"{SUBDUED} italic", no_wrap=True)

    for idx, note in enumerate(notes, start=1):
        created = _format_timestamp(note.created_at)
        tags = ", ".join(note.tags) if note.tags else "—"
        team = note.team_id or "—"
        git = f"{note.git_branch} @ {note.git_commit[:7]}" if note.git_commit and note.git_branch else "—"
        summary = _summarise(note) if include_summary else None

        row: list[str] = []
        if show_index:
            row.append(str(idx))
        row.extend([note.id[:8], note.title])
        if include_summary and summary is not None:
            row.append(summary)
        row.append(tags)
        if include_team:
            row.append(team)
        row.extend([created, git])
        table.add_row(*row)
        
        # Add faint ruled line between rows (except last)
        if idx < len(notes):
            separator = [""] * (len(row))
            separator[1] = Text("─" * 40, style=PAPER_LINE)
            table.add_row(*separator)
    
    # Combine margin with table
    content_group = Group(spiral_row, table)
    
    # Create final layout with red margin
    final = Table.grid(expand=True)
    final.add_column("margin", width=1, ratio=0)
    final.add_column("content", ratio=1)
    final.add_row(Text("│", style=MARGIN_RED), content_group)
    
    return final


def _format_timestamp(value: datetime) -> str:
    if not isinstance(value, datetime):
        return ""
    if value.tzinfo is None:
        return value.strftime("%Y-%m-%d %H:%M")
    return value.astimezone().strftime("%Y-%m-%d %H:%M")


def _summarise(note: Note) -> str:
    text = note.body.strip()
    if not text:
        return "—"
    first_line = text.splitlines()[0].strip()
    if len(first_line) <= 80:
        return first_line
    return f"{first_line[:77]}…"


def render_status_panel(status_lines: Sequence[str], context_lines: Sequence[str] | None = None) -> Panel:
    """
    Status panel - minimalist dark theme.
    """
    body_lines = list(status_lines)
    if context_lines:
        body_lines.append("")
        body_lines.extend(context_lines)
    
    # Create text with proper styling
    content_parts = []
    for line in body_lines:
        content_parts.append(line)
    
    body_text = "\n".join(content_parts)
    
    # Minimalist dark panel
    return Panel(
        Text.from_markup(body_text),
        title=Text("status", style=f"{ACCENT} italic bold"),
        box=box.ROUNDED,
        border_style=ACCENT,
        style=f"on {BG_DARK}",
        padding=(1, 2),
    )


def fullscreen_display(renderable, title: str = "cli-unites"):
    """
    Display content in full-screen mode with dark background.
    Press Ctrl+C to exit.
    """
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )
    
    # Header with title
    header_text = Text(f"✎ {title}", style=f"{ACCENT} bold italic", justify="center")
    layout["header"].update(Panel(header_text, border_style=ACCENT, style=f"on {BG_DARK}"))
    
    # Main content
    layout["body"].update(renderable)
    
    # Footer with instructions
    footer_text = Text("Press Ctrl+C to exit", style=SUBDUED, justify="center")
    layout["footer"].update(Panel(footer_text, border_style=SUBDUED, style=f"on {BG_DARK}"))
    
    with Screen(style=f"on {BG_DARK}") as screen:
        console.print(layout, height=screen.height)
        try:
            import time
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
