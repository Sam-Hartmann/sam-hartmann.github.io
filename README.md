# Website

Static site built with [Jekyll](https://jekyllrb.com) and hosted via GitHub Pages.

## Quick start (local preview)

```bash
cd website
bundle install
bundle exec jekyll serve --livereload
# open http://localhost:4000
```

## Dev/Staging mode (safe pre-production)

Use the development override config so analytics/comments stay off while you iterate:

```bash
cd website
python manage.py serve-dev
```

Build a separate dev output folder:

```bash
cd website
python manage.py build-dev
# output: _site_dev/
```

`_config_dev.yml` overrides production settings from `_config.yml`.

## Website automation CLI

```bash
cd website

# create a section (updates _config.yml + creates <section>/index.html)
python manage.py new-section

# create a post markdown file interactively
python manage.py new-post

# list current sections and posts
python manage.py list-sections
python manage.py list-posts
python manage.py list-posts --section parenting
```

## Adding a new story

Create a file in `_posts/<section>/YYYY-MM-DD-title.md`:

```yaml
---
layout: post
title: "Your Story Title"
date: 2026-07-12
categories: [parenting]   # or [cmpa]
tags: [tag1, tag2]
image: /assets/images/your-image.jpg
excerpt: "Short summary shown on cards."
read_time: 5
medium_url: https://medium.com/@your-handle/your-post   # optional
---

Your Markdown content here...
```

## Adding a new section

1. Add an entry to `_config.yml` under `sections:`
2. Create a folder `<section-id>/index.html` using the `section` layout
3. Use `categories: [<section-id>]` in post front matter

## Configuration

Edit `_config.yml` to set:
- `google_analytics` — your GA4 measurement ID
- `giscus` fields — from [giscus.app](https://giscus.app) (enable GitHub Discussions first)
- `links.etsy`, `links.gumroad`, `links.medium` — your shop/profile URLs

## Deployment

Push to `main` — GitHub Actions builds and deploys automatically.
Set GitHub Pages source to **GitHub Actions** in repo Settings → Pages.
