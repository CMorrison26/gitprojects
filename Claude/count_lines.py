#!/usr/bin/env python3
"""
count_lines.py — recursively count non-comment, non-blank source lines.

Usage:
    python count_lines.py [options]

Options:
    --exclude DIR EXT   Skip files with extension EXT under DIR (relative to
                        the script location or absolute). Repeatable.
                        EXT may include or omit the leading dot.
    --root PATH         Root directory to scan (default: script's own directory).
    -v, --verbose       Print per-file counts.
    -h, --help          Show this help message.

Examples:
    # Skip all .xml files under output/db
    python count_lines.py --exclude output/db xml

    # Multiple exclusions
    python count_lines.py --exclude output/db xml --exclude logs csv

    # Run against a different root
    python count_lines.py --root /some/other/project --exclude vendor js
"""

import argparse
import os
import re
import sys


# ---------------------------------------------------------------------------
# Comment stripping rules
# Each entry: (style_name, set_of_extensions)
# ---------------------------------------------------------------------------

HASH_EXTS = {
    "sh", "bash", "zsh", "fish", "py", "rb", "pl", "pm", "r", "coffee",
    "yaml", "yml", "toml", "conf", "cfg", "ini", "dockerfile", "makefile",
    "mk", "cmake", "tf", "tfvars", "pp", "ex", "exs", "cr", "nim", "jl",
    "awk", "tcl", "snakefile",
}

SLASH_EXTS = {
    "js", "jsx", "ts", "tsx", "java", "c", "cpp", "cc", "cxx", "h", "hpp",
    "cs", "go", "swift", "kt", "kts", "scala", "rs", "dart", "groovy",
    "gvy", "gradle", "php", "phtml", "d", "vala", "hx", "zig", "v",
}

SQL_EXTS    = {"sql", "ddl", "dml", "psql", "mysql", "sqlite"}
CSS_EXTS    = {"css", "scss", "sass", "less"}
LUA_EXTS    = {"lua"}
VIM_EXTS    = {"vim", "vimrc"}
LISP_EXTS   = {"lisp", "clj", "cljs", "cljc", "edn", "scm", "rkt", "el", "elisp"}
HASKELL_EXTS = {"hs", "lhs", "elm", "purs"}
HTML_EXTS   = {"html", "htm", "xml", "svg", "xsl", "xslt", "jsp", "aspx",
               "cshtml", "twig", "jinja", "j2"}
BATCH_EXTS  = {"bat", "cmd"}
PS_EXTS     = {"ps1", "psm1", "psd1"}
FORTRAN_EXTS = {"f", "f90", "f95", "f03", "f08", "for"}
ASM_EXTS    = {"asm", "s"}
MATLAB_EXTS = {"m"}
ERLANG_EXTS = {"erl", "hrl"}
PROLOG_EXTS = {"pro"}
COBOL_EXTS  = {"cob", "cbl", "cobol"}

# Special basenames treated as a known extension style
BASENAME_MAP = {
    "dockerfile":       "dockerfile",
    "makefile":         "makefile",
    "rakefile":         "rb",
    "gemfile":          "rb",
    "vagrantfile":      "rb",
    "brewfile":         "rb",
    "cmakelist.txt":    "cmake",
    ".bashrc":          "sh",
    ".zshrc":           "sh",
    ".profile":         "sh",
    ".bash_profile":    "sh",
}

# Directories to always skip
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".mypy_cache", ".tox",
    "venv", ".venv", "dist", "build", ".gradle", ".idea", ".vscode",
    ".eggs", ".pytest_cache", ".ruff_cache",
}


# ---------------------------------------------------------------------------
# Stripping helpers
# ---------------------------------------------------------------------------

def _nonblank(lines):
    return sum(1 for ln in lines if ln.strip())


def strip_hash(text):
    return [ln for ln in text.splitlines() if not re.match(r'^\s*#', ln)]


def strip_slash(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    text = re.sub(r'//[^\n]*', '', text)
    return text.splitlines()


def strip_sql(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    text = re.sub(r'--[^\n]*', '', text)
    return text.splitlines()


def strip_css(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    return text.splitlines()


def strip_lua(text):
    text = re.sub(r'--\[\[.*?\]\]', '', text, flags=re.DOTALL)
    text = re.sub(r'--[^\n]*', '', text)
    return text.splitlines()


def strip_vim(text):
    return [ln for ln in text.splitlines() if not re.match(r'^\s*"', ln)]


def strip_lisp(text):
    return [ln for ln in text.splitlines() if not re.match(r'^\s*;', ln)]


def strip_haskell(text):
    text = re.sub(r'\{-.*?-\}', '', text, flags=re.DOTALL)
    text = re.sub(r'--[^\n]*', '', text)
    return text.splitlines()


def strip_html(text):
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    return text.splitlines()


def strip_batch(text):
    return [ln for ln in text.splitlines()
            if not re.match(r'^\s*(rem\b|::)', ln, re.IGNORECASE)]


def strip_powershell(text):
    text = re.sub(r'<#.*?#>', '', text, flags=re.DOTALL)
    text = re.sub(r'#[^\n]*', '', text)
    return text.splitlines()


def strip_fortran(text):
    return [ln for ln in text.splitlines()
            if not re.match(r'^\s*(!|c\s)', ln, re.IGNORECASE)]


def strip_asm(text):
    return [ln for ln in text.splitlines() if not re.match(r'^\s*[;#]', ln)]


def strip_percent(text):
    return [ln for ln in text.splitlines() if not re.match(r'^\s*%', ln)]


def strip_cobol(text):
    return [ln for ln in text.splitlines() if not re.match(r'^\s*\*', ln)]


STYLE_FUNCS = {
    "hash":       strip_hash,
    "slash":      strip_slash,
    "sql":        strip_sql,
    "css":        strip_css,
    "lua":        strip_lua,
    "vim":        strip_vim,
    "lisp":       strip_lisp,
    "haskell":    strip_haskell,
    "html":       strip_html,
    "batch":      strip_batch,
    "powershell": strip_powershell,
    "fortran":    strip_fortran,
    "asm":        strip_asm,
    "percent":    strip_percent,
    "cobol":      strip_cobol,
}


def get_style(path):
    basename = os.path.basename(path).lower()
    if basename in BASENAME_MAP:
        ext = BASENAME_MAP[basename]
    elif "." in basename:
        ext = basename.rsplit(".", 1)[-1]
    else:
        return None

    if ext in HASH_EXTS:    return "hash"
    if ext in SLASH_EXTS:   return "slash"
    if ext in SQL_EXTS:     return "sql"
    if ext in CSS_EXTS:     return "css"
    if ext in LUA_EXTS:     return "lua"
    if ext in VIM_EXTS:     return "vim"
    if ext in LISP_EXTS:    return "lisp"
    if ext in HASKELL_EXTS: return "haskell"
    if ext in HTML_EXTS:    return "html"
    if ext in BATCH_EXTS:   return "batch"
    if ext in PS_EXTS:      return "powershell"
    if ext in FORTRAN_EXTS: return "fortran"
    if ext in ASM_EXTS:     return "asm"
    if ext in MATLAB_EXTS:  return "percent"
    if ext in ERLANG_EXTS:  return "percent"
    if ext in PROLOG_EXTS:  return "percent"
    if ext in COBOL_EXTS:   return "cobol"
    return None


def count_file(path):
    style = get_style(path)
    if style is None:
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return None
    lines = STYLE_FUNCS[style](text)
    return _nonblank(lines)


# ---------------------------------------------------------------------------
# Exclusion matching
# ---------------------------------------------------------------------------

def build_exclusions(raw_pairs, root):
    """
    raw_pairs: list of (dir_path_str, ext_str) from --exclude arguments.
    Returns a list of (abs_dir, ext_without_dot) tuples.
    """
    result = []
    for dir_str, ext_str in raw_pairs:
        abs_dir = os.path.normpath(
            dir_str if os.path.isabs(dir_str) else os.path.join(root, dir_str)
        )
        ext = ext_str.lstrip(".").lower()
        result.append((abs_dir, ext))
    return result


def is_excluded(path, exclusions):
    """Return True if path matches any exclusion rule."""
    if not exclusions:
        return False
    basename = os.path.basename(path).lower()
    if "." not in basename:
        return False
    ext = basename.rsplit(".", 1)[-1]
    abs_path = os.path.abspath(path)
    for excl_dir, excl_ext in exclusions:
        if ext == excl_ext and abs_path.startswith(excl_dir + os.sep):
            return True
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Count non-comment, non-blank source lines recursively.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--exclude",
        nargs=2,
        metavar=("DIR", "EXT"),
        action="append",
        default=[],
        help="Exclude files with EXT under DIR (repeatable).",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Root directory to scan (default: script's own directory).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print per-file line counts.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(args.root) if args.root else script_dir

    if not os.path.isdir(root):
        print(f"Error: root directory not found: {root}", file=sys.stderr)
        sys.exit(1)

    exclusions = build_exclusions(args.exclude, root)

    print(f"Scanning : {root}")
    if exclusions:
        for excl_dir, excl_ext in exclusions:
            print(f"Excluding: .{excl_ext}  under  {excl_dir}")
    print("-" * 60)

    total = 0
    file_count = 0
    skipped_excluded = 0
    skipped_unknown = 0

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        # Prune hidden/generated dirs in-place so os.walk won't descend
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in SKIP_DIRS and not d.startswith(".")
        )

        for fname in sorted(filenames):
            fpath = os.path.join(dirpath, fname)

            # Skip the script itself
            if os.path.abspath(fpath) == os.path.abspath(__file__):
                continue

            if is_excluded(fpath, exclusions):
                skipped_excluded += 1
                continue

            count = count_file(fpath)
            if count is None:
                skipped_unknown += 1
                continue

            total += count
            file_count += 1
            if args.verbose:
                rel = os.path.relpath(fpath, root)
                print(f"  {count:>8,}  {rel}")

    print("-" * 60)
    print(f"Files counted    : {file_count:,}")
    print(f"Files excluded   : {skipped_excluded:,}  (matched an --exclude rule)")
    print(f"Files skipped    : {skipped_unknown:,}  (unknown/unsupported type)")
    print(f"Total lines      : {total:,}")


if __name__ == "__main__":
    main()
