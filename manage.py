#!/usr/bin/env python3
"""
manage.py — CLI for managing website sections and posts.

Usage:
    python manage.py new-section
    python manage.py new-post
    python manage.py list-sections
    python manage.py list-posts [--section SECTION]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────

WEBSITE_DIR  = Path(__file__).parent
CONFIG_FILE  = WEBSITE_DIR / "_config.yml"
DEV_CONFIG_FILE = WEBSITE_DIR / "_config_dev.yml"
POSTS_DIR    = WEBSITE_DIR / "_posts"
LAYOUTS_DIR  = WEBSITE_DIR / "_layouts"

SECTION_LAYOUT_TEMPLATE = """\
---
layout: section
title: "{title}"
description: "{description}"
icon: "{icon}"
section_id: {section_id}
permalink: /{section_id}/
---
"""

POST_TEMPLATE = """\
---
layout: post
title: "{title}"
date: {date}
categories: [{section_id}]
tags: [{tags}]
image: /assets/images/{slug}.jpg   # optional — replace with your image path
excerpt: >
  {excerpt}
read_time: {read_time}
# medium_url: https://medium.com/@your-handle/your-post
---

{title}

Write your story here using Markdown.
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    """Convert a string to a URL/filename-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text


def get_sections() -> list[dict]:
    """Parse section IDs and titles from _config.yml."""
    if not CONFIG_FILE.exists():
        return []
    content = CONFIG_FILE.read_text()
    # Simple YAML parsing — look for the sections block
    sections = []
    in_sections = False
    current: dict = {}
    for line in content.splitlines():
        if re.match(r"^sections:", line):
            in_sections = True
            continue
        if in_sections:
            if re.match(r"^\S", line) and not line.startswith(" ") and not line.startswith("-"):
                # Left-indent means we've left the sections block
                break
            id_match    = re.match(r"\s+id:\s+(.+)", line)
            title_match = re.match(r"\s+title:\s+\"?(.+?)\"?\s*$", line)
            icon_match  = re.match(r"\s+icon:\s+\"?(.+?)\"?\s*$", line)
            dash_match  = re.match(r"\s+-\s+id:", line)

            if dash_match:
                if current:
                    sections.append(current)
                current = {}
                id_match = re.match(r'\s+-\s+id:\s+(.+)', line)
                if id_match:
                    current["id"] = id_match.group(1).strip()
            elif id_match:
                current["id"] = id_match.group(1).strip()
            elif title_match:
                current["title"] = title_match.group(1).strip()
            elif icon_match:
                current["icon"] = icon_match.group(1).strip()

    if current:
        sections.append(current)
    return sections


def add_section_to_config(section_id: str, title: str, description: str, icon: str) -> None:
    """Append a new section entry to the sections list in _config.yml."""
    content = CONFIG_FILE.read_text()
    new_entry = (
        f"  - id: {section_id}\n"
        f"    title: \"{title}\"\n"
        f"    description: \"{description}\"\n"
        f"    icon: \"{icon}\"\n"
    )
    # Insert after the last existing section entry
    if "sections:" in content:
        # Find the end of the sections block
        lines = content.splitlines(keepends=True)
        insert_at = None
        in_sections = False
        for i, line in enumerate(lines):
            if re.match(r"^sections:", line):
                in_sections = True
            elif in_sections and re.match(r"^\S", line) and not line.startswith(" ") and not line.startswith("-"):
                insert_at = i
                break
        if insert_at is not None:
            lines.insert(insert_at, new_entry)
        else:
            lines.append(new_entry)
        CONFIG_FILE.write_text("".join(lines))
    else:
        CONFIG_FILE.write_text(content + f"\nsections:\n{new_entry}")


def _run_jekyll(command: list[str]) -> None:
    """Run a Jekyll command from the website directory."""
    subprocess.run(command, cwd=WEBSITE_DIR, check=True)


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_list_sections(_args) -> None:
    sections = get_sections()
    if not sections:
        print("No sections found in _config.yml.")
        return
    print("Sections:")
    for s in sections:
        print(f"  {s.get('icon', '')}  {s.get('id')}  —  {s.get('title', '')}")


def cmd_list_posts(args) -> None:
    if not POSTS_DIR.exists():
        print("No _posts directory found.")
        return
    pattern = f"{args.section}/**/*.md" if args.section else "**/*.md"
    posts = sorted(POSTS_DIR.glob(pattern))
    if not posts:
        print("No posts found.")
        return
    print(f"{'Date':<12} {'Section':<16} Title")
    print("-" * 60)
    for p in posts:
        # date is first 10 chars of filename
        fname   = p.stem
        parts   = fname.split("-", 3)
        pdate   = "-".join(parts[:3]) if len(parts) >= 3 else "?"
        section = p.parent.name
        title   = parts[3].replace("-", " ").title() if len(parts) == 4 else fname
        print(f"{pdate:<12} {section:<16} {title}")


def cmd_new_section(_args) -> None:
    print("── Create a new section ──")
    section_id  = slugify(input("Section ID (url-safe slug, e.g. sleep-tips): ").strip())
    title       = input("Title (e.g. Sleep Tips): ").strip()
    description = input("Short description: ").strip()
    icon        = input("Emoji icon (e.g. 😴): ").strip() or "📖"

    if not section_id:
        print("Error: section ID cannot be empty.")
        sys.exit(1)

    # 1. Create section folder + index.html
    section_dir = WEBSITE_DIR / section_id
    index_file  = section_dir / "index.html"

    if index_file.exists():
        print(f"Warning: {index_file} already exists — skipping file creation.")
    else:
        section_dir.mkdir(parents=True, exist_ok=True)
        index_file.write_text(
            SECTION_LAYOUT_TEMPLATE.format(
                title=title,
                description=description,
                icon=icon,
                section_id=section_id,
            )
        )
        print(f"Created {index_file}")

    # 2. Add to _config.yml
    existing_ids = [s["id"] for s in get_sections()]
    if section_id in existing_ids:
        print(f"Warning: '{section_id}' already in _config.yml — skipping config update.")
    else:
        add_section_to_config(section_id, title, description, icon)
        print(f"Added '{section_id}' to _config.yml")

    print(f"\n✅ Section '{title}' ready at /{section_id}/")
    print("   Add posts with:  python manage.py new-post")


def cmd_new_post(_args) -> None:
    sections = get_sections()
    if not sections:
        print("No sections found. Create a section first: python manage.py new-section")
        sys.exit(1)

    print("── Create a new post ──")

    # Pick section
    print("Available sections:")
    for i, s in enumerate(sections):
        print(f"  {i + 1}. {s.get('icon', '')} {s.get('id')} — {s.get('title', '')}")
    choice = input(f"Section [1-{len(sections)}]: ").strip()
    try:
        section = sections[int(choice) - 1]
    except (ValueError, IndexError):
        print("Invalid choice.")
        sys.exit(1)
    section_id = section["id"]

    title     = input("Post title: ").strip()
    excerpt   = input("Short excerpt (shown on cards): ").strip()
    tags      = input("Tags (comma-separated, e.g. tips, baby): ").strip()
    read_time = input("Estimated read time in minutes [5]: ").strip() or "5"
    post_date = input(f"Date (YYYY-MM-DD) [{date.today()}]: ").strip() or str(date.today())

    if not title:
        print("Error: title cannot be empty.")
        sys.exit(1)

    slug      = slugify(title)
    filename  = f"{post_date}-{slug}.md"
    tags_str  = ", ".join(t.strip() for t in tags.split(",")) if tags else ""

    post_dir  = POSTS_DIR / section_id
    post_dir.mkdir(parents=True, exist_ok=True)
    post_file = post_dir / filename

    if post_file.exists():
        overwrite = input(f"{post_file} already exists. Overwrite? [y/N]: ").strip().lower()
        if overwrite != "y":
            print("Aborted.")
            sys.exit(0)

    post_file.write_text(
        POST_TEMPLATE.format(
            title=title,
            date=post_date,
            section_id=section_id,
            tags=tags_str,
            slug=slug,
            excerpt=excerpt or title,
            read_time=read_time,
        )
    )

    print(f"\n✅ Post created: {post_file.relative_to(WEBSITE_DIR)}")
    print("   Edit it, then commit and push to publish.")


def cmd_serve_dev(_args) -> None:
    """Serve the website using development config overrides."""
    if not DEV_CONFIG_FILE.exists():
        print("Missing _config_dev.yml. Create it first.")
        sys.exit(1)
    print("Starting Jekyll in DEV mode...")
    _run_jekyll([
        "bundle",
        "exec",
        "jekyll",
        "serve",
        "--livereload",
        "--config",
        "_config.yml,_config_dev.yml",
    ])


def cmd_build_dev(_args) -> None:
    """Build a dev version of the site to _site_dev."""
    if not DEV_CONFIG_FILE.exists():
        print("Missing _config_dev.yml. Create it first.")
        sys.exit(1)
    print("Building Jekyll DEV output...")
    _run_jekyll([
        "bundle",
        "exec",
        "jekyll",
        "build",
        "--config",
        "_config.yml,_config_dev.yml",
        "--destination",
        "_site_dev",
    ])


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="manage.py",
        description="Manage website sections and posts.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-sections", help="List all configured sections")

    lp = sub.add_parser("list-posts", help="List all posts")
    lp.add_argument("--section", metavar="SECTION_ID", help="Filter by section")

    sub.add_parser("new-section", help="Interactively create a new section")
    sub.add_parser("new-post",    help="Interactively create a new post")
    sub.add_parser("serve-dev",   help="Run local dev server with _config_dev.yml")
    sub.add_parser("build-dev",   help="Build a dev version to _site_dev")

    args = parser.parse_args()

    commands = {
        "list-sections": cmd_list_sections,
        "list-posts":    cmd_list_posts,
        "new-section":   cmd_new_section,
        "new-post":      cmd_new_post,
        "serve-dev":     cmd_serve_dev,
        "build-dev":     cmd_build_dev,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
