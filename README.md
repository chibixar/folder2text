# folder2text

> Instantly convert any folder into a single text snapshot — ready to paste into ChatGPT, Claude, Gemini, or any AI assistant.

```bash
folder2text ./my_project -c   # done. it's in your clipboard.
```

---

## Description

`folder2text` walks your directory, skips all the junk (binaries, `node_modules`, `.git`, build artifacts), and produces a clean, well-structured document you can paste straight into any AI chat window.

**One command. Everything in context.**

---

## Install

No dependencies. Pure Python. Works on Linux, macOS, and Windows.

```bash
# Download
curl -O https://raw.githubusercontent.com/chibixar/folder2text/main/folder2text.py

# Make it a system command
chmod +x folder2text.py && sudo mv folder2text.py /usr/local/bin/folder2text
```

**Requires Python 3.10+**

---

## Usage

```bash
# Copy entire project to clipboard — paste straight into your AI chat
folder2text ./my_project -c

# Save to a file instead
folder2text ./my_project -o context.txt

# Only grab source files (skip tests, configs, everything else)
folder2text ./my_project --include .py .ts .md -c

# Add a directory tree at the top so the AI understands your structure
folder2text ./my_project --tree -c
```

---

## Features

| | |
|---|---|
| **One-command clipboard copy** | `-c` pipes straight to your clipboard — no temp files |
| **Smart binary detection** | Two-layer check: extension list + null-byte scan. Compiled files, images, archives never slip through |
| **Noise filtering** | Skips `node_modules`, `.git`, `__pycache__`, `venv`, `dist`, and more out of the box |
| **Allowlist mode** | `--include .py .md` — only grab exactly what you need |
| **Flexible exclusions** | Skip by extension, directory name, or glob pattern |
| **Directory tree** | Optional ASCII tree at the top gives the AI full structural context |
| **Three output formats** | Markdown (default), XML, or plain text |
| **Token estimate** | Prints approximate token count after copying so you know if you're near your context limit |
| **Zero dependencies** | Pure Python stdlib — nothing to `pip install` |

---

## All Options

```
folder2text <folder> [options]

Output:
  -o, --output FILE         Write to a file instead of stdout
  -c, --copy                Copy to clipboard (auto-detects pbcopy / xclip / xsel / wl-copy)
  --format {markdown,xml,plain}
                            Output format (default: markdown)
  --tree                    Prepend an ASCII directory tree

Filtering:
  --include EXT [EXT ...]   Only include these extensions — overrides all defaults
  --skip-ext EXT [EXT ...]  Skip additional extensions on top of defaults
  --allow-ext EXT [EXT ...] Re-include extensions that are skipped by default
  --skip-dirs DIR [DIR ...]  Skip additional directory names
  --skip-patterns PAT [...]  Glob patterns to skip (e.g. "test_*" "*.min.js")
  --max-size MB             Skip files larger than N MB (default: 1.0)

Info:
  -v, --verbose             Show per-file status on stderr
  --list-skip-defaults      Print built-in skip lists and exit
```

---

## Output Formats

### Markdown (default)
Best for pasting into chat UIs. Syntax-highlighted fenced blocks with file paths as headers.

~~~markdown
## src/main.py  (1.2 KB)

```python
def hello():
    print("Hello, world!")
```
~~~

### XML
Best for automated pipelines and prompt templates where the AI needs to reference files by path.

```xml
<file path="src/main.py" size="1.2 KB">
def hello():
    print("Hello, world!")
</file>
```

### Plain
No markup, maximum compatibility.

```
========================================================================
 FILE: src/main.py  (1.2 KB)
========================================================================

def hello():
    print("Hello, world!")
```

---

## Recipes

```bash
# "Explain this codebase to me"
folder2text ./my_app --include .py .md --tree -c

# "Review my backend for security issues"
folder2text ./api --include .py --skip-patterns "test_*" "migrations/*" -c

# "Why is my build broken?"
folder2text . --include .yml .toml .json --skip-dirs node_modules -c

# Save a snapshot for later / version control
folder2text ./project -o snapshots/$(date +%Y%m%d).txt

# Check how many tokens you're sending
folder2text ./project -c
# → Copied to clipboard! 38 files, ~24,600 chars (~6,150 tokens). 5 skipped.
```

---

## Clipboard Support

`-c` / `--copy` auto-detects the right tool for your system:

| Platform | Tool |
|----------|------|
| macOS | `pbcopy` (built-in) |
| Windows | `clip` (built-in) |
| Linux X11 | `xclip` or `xsel` |
| Linux Wayland | `wl-copy` |

On Linux, install one if needed:
```bash
sudo apt install xclip      # Ubuntu/Debian
sudo dnf install xclip      # Fedora
```

---

## Default Skip Lists

Run `folder2text --list-skip-defaults` to see everything. Key defaults:

**Directories:** `.git` · `node_modules` · `__pycache__` · `.venv` / `venv` / `env` · `dist` · `build` · `.next` · `.nuxt` · `.idea` · `.vscode`

**Extensions:** images · audio/video · archives · compiled binaries · Office documents · fonts · databases

Override any of these with `--allow-ext`, `--skip-ext`, or `--include`.

---

## Tips

- **Use `--include` for large projects.** It's the single best way to keep output small and focused. `--include .py` on a Django project gives you exactly the source code — no migrations, no static files, no lock files.
- **Use `--tree` when asking "how does this project work?"** The directory structure alone answers half the question.
- **Token math:** the clipboard summary prints `~N tokens`. Most models top out at 128k–200k. If you're over budget, narrow with `--include` or `--skip-patterns`.
- **Use `--format xml` for pipelines.** The `<file path="…">` tags let the model cite specific files back to you precisely.

---

## License

MIT
