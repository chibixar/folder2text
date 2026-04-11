#!/usr/bin/env python3
"""
folder2text - Convert a folder's contents to a single text file for AI consumption.
"""

import os
import sys
import argparse
import fnmatch
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# Extensions that are almost certainly binary/non-readable
DEFAULT_SKIP_EXTENSIONS = {
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp", ".tiff",
    # Audio/Video
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv", ".flac", ".ogg",
    # Archives
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    # Compiled / Binary
    ".exe", ".dll", ".so", ".dylib", ".bin", ".o", ".a", ".class", ".pyc",
    # Office / Documents
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # Fonts
    ".ttf", ".otf", ".woff", ".woff2",
    # Database
    ".db", ".sqlite", ".sqlite3",
    # Other binary
    ".iso", ".img", ".dmg",
}

# Directories to skip by default
DEFAULT_SKIP_DIRS = {
    ".git", ".svn", ".hg",
    "__pycache__", ".pytest_cache",
    "node_modules", ".venv", "venv", "env",
    ".idea", ".vscode",
    "dist", "build", ".next", ".nuxt",
}


def detect_clipboard_cmd() -> list[str] | None:
    """Return the clipboard copy command for the current platform, or None."""
    import platform
    system = platform.system()
    if system == "Darwin":
        return ["pbcopy"]
    if system == "Windows":
        return ["clip"]
    # Linux — try xclip, then xsel, then wl-copy (Wayland)
    for cmd, args in [
        ("xclip", ["-selection", "clipboard"]),
        ("xsel",  ["--clipboard", "--input"]),
        ("wl-copy", []),
    ]:
        if shutil.which(cmd):
            return [cmd] + args
    return None


def is_binary_file(filepath: Path, sample_size: int = 8192) -> bool:
    """Heuristically check if a file is binary."""
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(sample_size)
        # If null bytes exist, it's almost certainly binary
        if b"\x00" in chunk:
            return True
        # Try decoding as UTF-8
        chunk.decode("utf-8")
        return False
    except (UnicodeDecodeError, OSError):
        return True


def format_size(size_bytes: int) -> str:
    """Human-readable file size."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def collect_files(
    root: Path,
    skip_extensions: set[str],
    include_extensions: set[str] | None,
    skip_dirs: set[str],
    extra_skip_patterns: list[str],
    max_file_size: int,
) -> list[Path]:
    """Walk the directory and return a sorted list of files to include."""
    files = []

    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)

        # Prune skipped directories in-place so os.walk doesn't descend into them
        dirnames[:] = [
            d for d in dirnames
            if d not in skip_dirs
            and not any(fnmatch.fnmatch(d, pat) for pat in extra_skip_patterns)
        ]
        dirnames.sort()

        for filename in sorted(filenames):
            filepath = current / filename
            rel = filepath.relative_to(root)

            # Skip by glob pattern
            if any(fnmatch.fnmatch(str(rel), pat) or fnmatch.fnmatch(filename, pat)
                   for pat in extra_skip_patterns):
                continue

            ext = filepath.suffix.lower()

            # Inclusion filter takes priority if specified
            if include_extensions is not None:
                if ext not in include_extensions:
                    continue
            else:
                # Otherwise apply default skip list
                if ext in skip_extensions:
                    continue

            # Size guard
            try:
                size = filepath.stat().st_size
            except OSError:
                continue
            if size > max_file_size:
                continue

            files.append(filepath)

    return files


def build_tree(root: Path, files: list[Path]) -> str:
    """Build an ASCII directory tree of included files."""
    rel_paths = sorted(f.relative_to(root) for f in files)
    lines = [str(root.name) + "/"]
    for rel in rel_paths:
        parts = rel.parts
        indent = "    " * (len(parts) - 1)
        lines.append(f"{indent}└── {parts[-1]}")
    return "\n".join(lines)


def convert(
    folder: str,
    output: str | None,
    skip_extensions: set[str],
    include_extensions: set[str] | None,
    skip_dirs: set[str],
    extra_skip_patterns: list[str],
    max_file_size_mb: float,
    show_tree: bool,
    verbose: bool,
    separator: str,
    copy: bool = False,
) -> None:
    root = Path(folder).resolve()
    if not root.is_dir():
        print(f"Error: '{folder}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    max_bytes = int(max_file_size_mb * 1024 * 1024)

    files = collect_files(
        root,
        skip_extensions,
        include_extensions,
        skip_dirs,
        extra_skip_patterns,
        max_bytes,
    )

    if not files:
        print("No files matched the criteria. Nothing to output.", file=sys.stderr)
        sys.exit(0)

    # Determine output target
    out_file = None
    buf = []          # used when copying to clipboard

    if copy:
        # Accumulate into a list; pipe to clipboard at the end
        def emit(text: str) -> None:
            buf.append(text)
    elif output:
        out_file = open(output, "w", encoding="utf-8", errors="replace")
        def emit(text: str) -> None:
            out_file.write(text)
    else:
        def emit(text: str) -> None:
            print(text, end="")

    # Header
    header_lines = [
        f"# folder2text output",
        f"# Source   : {root}",
        f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"# Files    : {len(files)}",
    ]
    emit("\n".join(header_lines) + "\n")

    if show_tree:
        emit("\n## Directory Tree\n\n```\n")
        emit(build_tree(root, files))
        emit("\n```\n")

    skipped = 0
    included = 0

    for filepath in files:
        rel = filepath.relative_to(root)

        if is_binary_file(filepath):
            if verbose:
                print(f"  [skip binary] {rel}", file=sys.stderr)
            skipped += 1
            continue

        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            if verbose:
                print(f"  [skip error ] {rel}: {e}", file=sys.stderr)
            skipped += 1
            continue

        included += 1
        size_str = format_size(filepath.stat().st_size)

        if separator == "markdown":
            ext = filepath.suffix.lstrip(".")
            emit(f"\n\n## {rel}  ({size_str})\n\n```{ext}\n{content}\n```\n")
        elif separator == "xml":
            emit(f'\n\n<file path="{rel}" size="{size_str}">\n{content}\n</file>\n')
        else:  # plain
            divider = "=" * 72
            emit(f"\n\n{divider}\n FILE: {rel}  ({size_str})\n{divider}\n\n{content}\n")

        if verbose:
            print(f"  [ok        ] {rel}  ({size_str})", file=sys.stderr)

    # Footer
    emit(f"\n\n# End of folder2text output ({included} files included, {skipped} skipped)\n")

    if copy:
        clipboard_cmd = detect_clipboard_cmd()
        if not clipboard_cmd:
            print(
                "Error: no clipboard tool found. Install xclip, xsel, or wl-copy on Linux.",
                file=sys.stderr,
            )
            sys.exit(1)
        full_text = "".join(buf)
        char_count = len(full_text)
        try:
            proc = subprocess.run(clipboard_cmd, input=full_text.encode("utf-8"), check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error: clipboard command failed: {e}", file=sys.stderr)
            sys.exit(1)
        approx_tokens = char_count // 4
        print(
            f"Copied to clipboard! "
            f"{included} files, ~{char_count:,} chars (~{approx_tokens:,} tokens). "
            f"{skipped} skipped."
        )
    elif out_file:
        out_file.close()
        print(f"Done. {included} files written to '{output}' ({skipped} skipped).")
    else:
        print(f"\n# Stats: {included} included, {skipped} skipped.", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="folder2text",
        description="Convert a folder's text files into a single document for AI consumption.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage - print to stdout
  folder2text ./my_project

  # Save to file
  folder2text ./my_project -o output.txt

  # Only include Python and Markdown files
  folder2text ./my_project --include .py .md

  # Skip test files and __pycache__ in addition to defaults
  folder2text ./my_project --skip-patterns "test_*" "*.min.js"

  # Skip extra extensions on top of defaults
  folder2text ./my_project --skip-ext .log .csv

  # Remove .svg from the default skip list (include SVGs)
  folder2text ./my_project --allow-ext .svg

  # Use XML-style separators (good for structured AI prompts)
  folder2text ./my_project --format xml

  # Show directory tree at the top, verbose logging
  folder2text ./my_project --tree -v
""",
    )

    parser.add_argument("folder", help="Path to the folder to convert")
    parser.add_argument("-o", "--output", metavar="FILE",
                        help="Write output to FILE instead of stdout")
    parser.add_argument("--include", nargs="+", metavar="EXT",
                        help="Only include these extensions (e.g. .py .md). "
                             "Overrides the default skip list entirely.")
    parser.add_argument("--skip-ext", nargs="+", metavar="EXT",
                        help="Additional extensions to skip (e.g. .log .csv)")
    parser.add_argument("--allow-ext", nargs="+", metavar="EXT",
                        help="Remove these extensions from the default skip list "
                             "(e.g. .svg to include SVGs)")
    parser.add_argument("--skip-dirs", nargs="+", metavar="DIR",
                        help="Additional directory names to skip")
    parser.add_argument("--skip-patterns", nargs="+", metavar="PATTERN",
                        help="Glob patterns for files/dirs to skip (e.g. 'test_*' '*.min.js')")
    parser.add_argument("--max-size", type=float, default=1.0, metavar="MB",
                        help="Skip files larger than this many MB (default: 1.0)")
    parser.add_argument("--format", choices=["plain", "markdown", "xml"],
                        default="markdown",
                        help="Output format: plain, markdown (default), or xml")
    parser.add_argument("--tree", action="store_true",
                        help="Include an ASCII directory tree at the top of the output")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print per-file status to stderr")
    parser.add_argument("-c", "--copy", action="store_true",
                        help="Copy output directly to clipboard (auto-detects pbcopy/xclip/xsel/wl-copy)")
    parser.add_argument("--list-skip-defaults", action="store_true",
                        help="Print the default skip lists and exit")

    args = parser.parse_args()

    if args.list_skip_defaults:
        print("Default skipped extensions:")
        for ext in sorted(DEFAULT_SKIP_EXTENSIONS):
            print(f"  {ext}")
        print("\nDefault skipped directories:")
        for d in sorted(DEFAULT_SKIP_DIRS):
            print(f"  {d}")
        sys.exit(0)

    # Build effective skip set
    skip_ext = set(DEFAULT_SKIP_EXTENSIONS)
    if args.allow_ext:
        for e in args.allow_ext:
            skip_ext.discard(e if e.startswith(".") else f".{e}")
    if args.skip_ext:
        for e in args.skip_ext:
            skip_ext.add(e if e.startswith(".") else f".{e}")

    include_ext = None
    if args.include:
        include_ext = {e if e.startswith(".") else f".{e}" for e in args.include}

    skip_dirs = set(DEFAULT_SKIP_DIRS)
    if args.skip_dirs:
        skip_dirs.update(args.skip_dirs)

    convert(
        folder=args.folder,
        output=args.output,
        skip_extensions=skip_ext,
        include_extensions=include_ext,
        skip_dirs=skip_dirs,
        extra_skip_patterns=args.skip_patterns or [],
        max_file_size_mb=args.max_size,
        show_tree=args.tree,
        verbose=args.verbose,
        separator=args.format,
        copy=args.copy,
    )


if __name__ == "__main__":
    main()
