#!/usr/bin/env python3
"""
manage.py - CLI for managing website sections and posts.

Usage:
    python manage.py new-section
    python manage.py new-post
    python manage.py new-post --section SECTION --title TITLE --subtitle SUBTITLE --content CONTENT --image IMAGE --tags TAGS --date YYYY-MM-DD
    python manage.py list-sections
    python manage.py list-posts [--section SECTION]
    python manage.py serve-dev
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

WEBSITE_DIR = Path(__file__).parent
CONFIG_FILE = WEBSITE_DIR / "_config.yml"
DEV_CONFIG_FILE = WEBSITE_DIR / "_config_dev.yml"
POSTS_DIR = WEBSITE_DIR / "_posts"

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
image: {image}
excerpt: >
  {excerpt}
read_time: {read_time}
# medium_url: https://medium.com/@your-handle/your-post
---

{content}
"""


def slugify(text: str) -> str:
    """Convert a string to a URL/filename-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text


def yaml_escape(value: str) -> str:
    """Escape text so it can be safely placed inside YAML quotes."""
    return value.replace('"', '\\"').strip()


def get_sections() -> list[dict]:
    """Parse section IDs and titles from _config.yml."""
    if not CONFIG_FILE.exists():
        return []

    content = CONFIG_FILE.read_text()
    sections: list[dict] = []
    in_sections = False
    current: dict = {}

    for line in content.splitlines():
        if re.match(r"^sections:", line):
            in_sections = True
            continue

        if not in_sections:
            continue

        if re.match(r"^\S", line) and not line.startswith(" ") and not line.startswith("-"):
            break

        id_match = re.match(r"\s+id:\s+(.+)", line)
        title_match = re.match(r"\s+title:\s+\"?(.+?)\"?\s*$", line)
        icon_match = re.match(r"\s+icon:\s+\"?(.+?)\"?\s*$", line)
        dash_match = re.match(r"\s+-\s+id:", line)

        if dash_match:
            if current:
                sections.append(current)
            current = {}
            id_match = re.match(r"\s+-\s+id:\s+(.+)", line)
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

    if "sections:" in content:
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


def find_section_id(section_input: str, sections: list[dict]) -> str:
    """Resolve a section from id or title-like input."""
    section_input = section_input.strip()
    if not section_input:
        return ""

    for section in sections:
        sid = section.get("id", "")
        title = section.get("title", "")
        if section_input == sid:
            return sid
        if slugify(section_input) == slugify(title):
            return sid

    return ""


def cmd_list_sections(_args) -> None:
    sections = get_sections()
    if not sections:
        print("No sections found in _config.yml.")
        return

    print("Sections:")
    for section in sections:
        print(f"  {section.get('icon', '')}  {section.get('id')}  -  {section.get('title', '')}")


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
    for post_file in posts:
        fname = post_file.stem
        parts = fname.split("-", 3)
        post_date = "-".join(parts[:3]) if len(parts) >= 3 else "?"
        section = post_file.parent.name
        title = parts[3].replace("-", " ").title() if len(parts) == 4 else fname
        print(f"{post_date:<12} {section:<16} {title}")


def cmd_new_section(_args) -> None:
    print("-- Create a new section --")
    section_id = slugify(input("Section ID (url-safe slug, e.g. sleep-tips): ").strip())
    title = input("Title (e.g. Sleep Tips): ").strip()
    description = input("Short description: ").strip()
    icon = input("Emoji icon (e.g. 😴): ").strip() or "📖"

    if not section_id:
        print("Error: section ID cannot be empty.")
        sys.exit(1)

    section_dir = WEBSITE_DIR / section_id
    index_file = section_dir / "index.html"

    if index_file.exists():
        print(f"Warning: {index_file} already exists - skipping file creation.")
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

    existing_ids = [s["id"] for s in get_sections()]
    if section_id in existing_ids:
        print(f"Warning: '{section_id}' already in _config.yml - skipping config update.")
    else:
        add_section_to_config(section_id, title, description, icon)
        print(f"Added '{section_id}' to _config.yml")

    print(f"\nSection '{title}' ready at /{section_id}/")
    print("   Add posts with: python manage.py new-post")


def cmd_new_post(args) -> None:
    sections = get_sections()
    if not sections:
        print("No sections found. Create a section first: python manage.py new-section")
        sys.exit(1)

    print("-- Create a new post --")

    section_arg = getattr(args, "section", "") or ""
    section_id = find_section_id(section_arg, sections)
    if not section_id:
        print("Available sections:")
        for i, section in enumerate(sections):
            print(f"  {i + 1}. {section.get('icon', '')} {section.get('id')} - {section.get('title', '')}")

        if section_arg:
            print(f"Invalid section '{section_arg}'.")
            sys.exit(1)

        choice = input(f"Section [1-{len(sections)}]: ").strip()
        try:
            selected = sections[int(choice) - 1]
        except (ValueError, IndexError):
            print("Invalid choice.")
            sys.exit(1)
        section_id = selected["id"]

    title = (getattr(args, "title", "") or input("Post title: ").strip()).strip()
    subtitle = (getattr(args, "subtitle", "") or input("Short subtitle/excerpt (shown on cards): ").strip()).strip()

    if not title:
        print("Error: title cannot be empty.")
        sys.exit(1)

    content_arg = getattr(args, "content", None)
    content_file_arg = getattr(args, "content_file", None)
    if content_arg and content_file_arg:
        print("Use either --content or --content-file, not both.")
        sys.exit(1)

    content = (content_arg or "").strip()
    if content_file_arg:
        content_path = Path(content_file_arg)
        if not content_path.exists():
            print(f"Content file not found: {content_path}")
            sys.exit(1)
        content = content_path.read_text().strip()

    if not content:
        content = "Write your story here using Markdown."

    csv_tags = [t.strip() for t in (getattr(args, "tags", "") or "").split(",") if t.strip()]
    repeated_tags = [t.strip() for t in (getattr(args, "tag", []) or []) if t.strip()]
    merged_tags = csv_tags + repeated_tags

    if not merged_tags:
        interactive_tags = input("Tags (comma-separated, e.g. tips, baby): ").strip()
        merged_tags = [t.strip() for t in interactive_tags.split(",") if t.strip()]

    tags = ", ".join(dict.fromkeys(merged_tags))

    read_time_arg = getattr(args, "read_time", None)
    if read_time_arg:
        read_time = str(read_time_arg).strip() or "5"
    else:
        read_time = input("Estimated read time in minutes [5]: ").strip() or "5"

    date_arg = getattr(args, "date", None)
    if date_arg:
        post_date = str(date_arg).strip()
    else:
        post_date = input(f"Date (YYYY-MM-DD) [{date.today()}]: ").strip() or str(date.today())
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", post_date):
        print("Date must be in YYYY-MM-DD format.")
        sys.exit(1)

    images = [img.strip() for img in (getattr(args, "image", []) or []) if img.strip()]
    hero_image = images[0] if images else ""
    extra_images = images[1:]

    if extra_images:
        image_blocks = [f"![Image {i + 1}]({img})" for i, img in enumerate(extra_images)]
        content = f"{content}\n\n" + "\n\n".join(image_blocks)

    slug = slugify(title)
    filename = f"{post_date}-{slug}.md"

    post_dir = POSTS_DIR / section_id
    post_dir.mkdir(parents=True, exist_ok=True)
    post_file = post_dir / filename

    if post_file.exists() and not bool(getattr(args, "overwrite", False)):
        overwrite = input(f"{post_file} already exists. Overwrite? [y/N]: ").strip().lower()
        if overwrite != "y":
            print("Aborted.")
            sys.exit(0)

    post_file.write_text(
        POST_TEMPLATE.format(
            title=yaml_escape(title),
            date=post_date,
            section_id=section_id,
            tags=tags,
            image=hero_image,
            excerpt=yaml_escape(subtitle or title),
            read_time=read_time,
            content=content,
        )
    )

    print(f"\nPost created: {post_file.relative_to(WEBSITE_DIR)}")
    print("   Edit it, then commit and push to publish.")


def cmd_serve_dev(_args) -> None:
    """Serve the website using development config overrides in a temp output dir."""
    if not DEV_CONFIG_FILE.exists():
        print("Missing _config_dev.yml. Create it first.")
        sys.exit(1)
    with tempfile.TemporaryDirectory(prefix="hustles-jekyll-dev-") as temp_dir:
        print(f"Starting Jekyll in DEV mode (temporary destination: {temp_dir})...")
        _run_jekyll([
            "bundle",
            "exec",
            "jekyll",
            "serve",
            "--livereload",
            "--config",
            "_config.yml,_config_dev.yml",
            "--destination",
            temp_dir,
        ])


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

    np = sub.add_parser("new-post", help="Create a new post (from args or interactively)")
    np.add_argument("--section", help="Section ID (or section title)")
    np.add_argument("--title", help="Post title")
    np.add_argument("--subtitle", help="Subtitle/teaser (stored as excerpt)")
    np.add_argument("--content", help="Markdown content body")
    np.add_argument("--content-file", help="Path to a markdown/text file for post content")
    np.add_argument("--image", action="append", default=[], help="Hero/image path or URL (repeat for multiple images)")
    np.add_argument("--tags", help="Comma-separated tags")
    np.add_argument("--tag", action="append", default=[], help="Single tag (repeatable)")
    np.add_argument("--date", default=str(date.today()), help="Post date in YYYY-MM-DD (default: today)")
    np.add_argument("--read-time", default="5", help="Estimated read time in minutes (default: 5)")
    np.add_argument("--overwrite", action="store_true", help="Overwrite existing post file without prompting")

    sub.add_parser("serve-dev", help="Run local dev server with _config_dev.yml in a temporary output folder")

    args = parser.parse_args()

    commands = {
        "list-sections": cmd_list_sections,
        "list-posts": cmd_list_posts,
        "new-section": cmd_new_section,
        "new-post": cmd_new_post,
        "serve-dev": cmd_serve_dev,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
