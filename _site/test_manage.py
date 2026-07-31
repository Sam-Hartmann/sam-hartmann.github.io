import argparse
import importlib.util
from pathlib import Path

import pytest


def _load_manage_module():
    manage_path = Path(__file__).parent / "manage.py"
    spec = importlib.util.spec_from_file_location("website_manage", manage_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def manage_module():
    return _load_manage_module()


@pytest.fixture
def isolated_site(tmp_path, monkeypatch, manage_module):
    website_dir = tmp_path / "website"
    website_dir.mkdir()

    config = website_dir / "_config.yml"
    config.write_text(
        """
sections:
  - id: parenting
    title: "Parenting Advice"
    description: "Parenting stories"
    icon: "👶"
  - id: cmpa
    title: "CMPA"
    description: "CMPA stories"
    icon: "🥛"
""".lstrip()
    )

    dev_config = website_dir / "_config_dev.yml"
    dev_config.write_text("title: DEV\n")

    posts_dir = website_dir / "_posts"
    posts_dir.mkdir()

    monkeypatch.setattr(manage_module, "WEBSITE_DIR", website_dir)
    monkeypatch.setattr(manage_module, "CONFIG_FILE", config)
    monkeypatch.setattr(manage_module, "DEV_CONFIG_FILE", dev_config)
    monkeypatch.setattr(manage_module, "POSTS_DIR", posts_dir)

    return website_dir


def test_slugify(manage_module):
    assert manage_module.slugify("  Hello, World!  ") == "hello-world"
    assert manage_module.slugify("CMPA & Parenting Tips") == "cmpa-parenting-tips"


def test_get_sections_parses_config(manage_module, isolated_site):
    sections = manage_module.get_sections()
    assert len(sections) == 2
    assert sections[0]["id"] == "parenting"
    assert sections[1]["title"] == "CMPA"


def test_add_section_to_config_appends(manage_module, isolated_site):
    manage_module.add_section_to_config("sleep", "Sleep Tips", "Sleep help", "😴")
    updated = manage_module.CONFIG_FILE.read_text()
    assert "- id: sleep" in updated
    assert 'title: "Sleep Tips"' in updated


def test_cmd_new_section_creates_files(monkeypatch, manage_module, isolated_site):
    answers = iter(["sleep-tips", "Sleep Tips", "Better bedtimes", "😴"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    manage_module.cmd_new_section(argparse.Namespace())

    section_index = isolated_site / "sleep-tips" / "index.html"
    assert section_index.exists()
    assert "layout: section" in section_index.read_text()
    assert "section_id: sleep-tips" in section_index.read_text()

    config_text = (isolated_site / "_config.yml").read_text()
    assert "- id: sleep-tips" in config_text


def test_cmd_new_post_creates_markdown(monkeypatch, manage_module, isolated_site):
    answers = iter([
        "1",                     # choose parenting
        "My First Story",        # title
        "A short excerpt",       # excerpt
        "tips, baby",            # tags
        "7",                     # read_time
        "2026-07-12",            # date
    ])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    manage_module.cmd_new_post(argparse.Namespace())

    post = isolated_site / "_posts" / "parenting" / "2026-07-12-my-first-story.md"
    assert post.exists()
    text = post.read_text()
    assert "layout: post" in text
    assert "categories: [parenting]" in text
    assert "tags: [tips, baby]" in text


def test_cmd_new_post_invalid_choice_exits(monkeypatch, manage_module, isolated_site):
    monkeypatch.setattr("builtins.input", lambda _prompt: "99")
    with pytest.raises(SystemExit) as exc:
        manage_module.cmd_new_post(argparse.Namespace())
    assert exc.value.code == 1


def test_cmd_list_posts_filters_by_section(capsys, manage_module, isolated_site):
    pdir = isolated_site / "_posts" / "cmpa"
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / "2026-07-12-cmpa-story.md").write_text("---\n---\n")

    manage_module.cmd_list_posts(argparse.Namespace(section="cmpa"))
    output = capsys.readouterr().out
    assert "cmpa" in output
    assert "Cmpa Story" in output


def test_serve_dev_runs_jekyll_with_dev_config(monkeypatch, manage_module, isolated_site):
    captured = {}

    def _fake_run(command):
        captured["command"] = command

    class _FakeTempDir:
        def __enter__(self):
            return "/tmp/hustles-test-dev"

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(manage_module, "_run_jekyll", _fake_run)
    monkeypatch.setattr(manage_module.tempfile, "TemporaryDirectory", lambda prefix: _FakeTempDir())

    manage_module.cmd_serve_dev(argparse.Namespace())

    assert captured["command"] == [
        "bundle",
        "exec",
        "jekyll",
        "serve",
        "--livereload",
        "--config",
        "_config.yml,_config_dev.yml",
        "--destination",
        "/tmp/hustles-test-dev",
    ]


def test_dev_commands_require_dev_config(monkeypatch, manage_module, isolated_site):
    (isolated_site / "_config_dev.yml").unlink()

    with pytest.raises(SystemExit) as exc_serve:
        manage_module.cmd_serve_dev(argparse.Namespace())
    assert exc_serve.value.code == 1
