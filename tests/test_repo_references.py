"""Guard against README.md and docker-compose.yml naming files that do not exist.

Each check is a helper that takes the document's text (plus the repo root) and
returns a list of problems, every one naming the missing path, so the checks can
be exercised on hand-written snippets as well as on the real files.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

# Bind-mount sources that docker creates at runtime (git-ignored output dirs).
RUNTIME_MOUNT_DIRS = {"logs", "screenshots", "temp", "custom_actions"}

_TREE_ENTRY = re.compile(r"^(?P<prefix>(?:│   |    )*)(?:├── |└── )(?P<name>.+)$")
_FENCE = re.compile(r"```(?P<lang>[^\n`]*)\n(?P<body>.*?)```", re.DOTALL)


def _strip_comment(text: str) -> str:
    return re.split(r"\s#", text, maxsplit=1)[0].strip()


def _fenced_blocks(readme_text: str) -> list[tuple[str, str]]:
    return [(m["lang"].strip(), m["body"]) for m in _FENCE.finditer(readme_text)]


def readme_tree_paths(readme_text: str) -> list[str]:
    """Return repo-relative paths listed in the README's project tree."""
    for lang, body in _fenced_blocks(readme_text):
        if lang or not ("├── " in body or "└── " in body):
            continue
        paths: list[str] = []
        stack: list[str] = []
        for line in body.splitlines():
            match = _TREE_ENTRY.match(line)
            if not match:
                continue  # the root line ("browseruseagent/") or blank lines
            depth = len(match["prefix"]) // 4
            name = _strip_comment(match["name"]).rstrip("/")
            del stack[depth:]
            stack.append(name)
            paths.append("/".join(stack))
        return paths
    return []


def check_readme_tree(readme_text: str, root: Path) -> list[str]:
    paths = readme_tree_paths(readme_text)
    problems = [] if paths else ["README project tree not found"]
    problems += [
        f"README project tree lists missing path: {p}"
        for p in paths
        if not (root / p).exists()
    ]
    return problems


def readme_command_paths(readme_text: str) -> list[str]:
    """Return file/dir arguments of shell commands in README bash blocks."""
    paths: list[str] = []
    for lang, body in _fenced_blocks(readme_text):
        if lang not in {"bash", "sh", "shell"}:
            continue
        for line in body.splitlines():
            line = _strip_comment(line) if not line.lstrip().startswith("#") else ""
            if not line:
                continue
            words = shlex.split(line)
            tool, args = words[0], words[1:]
            if tool == "pip":
                paths += [
                    args[i + 1]
                    for i, a in enumerate(args[:-1])
                    if a in ("-r", "--requirement")
                ]
            elif tool == "cp" and args:
                paths.append([a for a in args if not a.startswith("-")][0])
            elif tool in {"pytest", "black", "isort"}:
                paths += [a for a in args if not a.startswith("-")]
    return paths


def check_readme_commands(readme_text: str, root: Path) -> list[str]:
    return [
        f"README command names missing path: {p}"
        for p in readme_command_paths(readme_text)
        if not (root / p).exists()
    ]


def _module_exists(module: str, root: Path) -> bool:
    module = module.split(":", 1)[0]
    if not module.startswith("app."):
        return False
    rel = Path(*module.split("."))
    return (root / rel.with_suffix(".py")).is_file() or (
        root / rel / "__init__.py"
    ).is_file()


def check_compose(compose_text: str, root: Path) -> list[str]:
    problems: list[str] = []
    services = (yaml.safe_load(compose_text) or {}).get("services") or {}
    for name, svc in services.items():
        build = svc.get("build")
        if isinstance(build, str):
            build = {"context": build}
        if isinstance(build, dict):
            context = root / build.get("context", ".")
            dockerfile = context / build.get("dockerfile", "Dockerfile")
            if not dockerfile.exists():
                problems.append(
                    f"compose service {name}: missing dockerfile {dockerfile.relative_to(root)}"
                )

        for vol in svc.get("volumes") or []:
            source = (
                vol.get("source", "") if isinstance(vol, dict) else vol.split(":", 1)[0]
            )
            if not source.startswith("./"):
                continue  # named volume or absolute path
            rel = source[2:].rstrip("/")
            if rel in RUNTIME_MOUNT_DIRS:
                continue
            if not (root / rel).exists():
                problems.append(
                    f"compose service {name}: missing bind-mount source {source}"
                )

        command = svc.get("command") or []
        words = (
            shlex.split(command)
            if isinstance(command, str)
            else [str(w) for w in command]
        )
        for i, word in enumerate(words):
            target = None
            if word in ("-A", "--app") and i + 1 < len(words):
                target = words[i + 1]
            elif word.startswith("--app="):
                target = word.split("=", 1)[1]
            if target and not _module_exists(target, root):
                problems.append(
                    f"compose service {name}: -A target {target} is not a module under app/"
                )

        depends = svc.get("depends_on") or []
        for dep in depends if isinstance(depends, list) else list(depends):
            if dep not in services:
                problems.append(
                    f"compose service {name}: depends_on names undefined service {dep}"
                )
    return problems


# --- tests on the real files -------------------------------------------------


def test_readme_tree_paths_exist():
    problems = check_readme_tree((REPO_ROOT / "README.md").read_text(), REPO_ROOT)
    assert not problems, "\n".join(problems)


def test_readme_command_paths_exist():
    problems = check_readme_commands((REPO_ROOT / "README.md").read_text(), REPO_ROOT)
    assert not problems, "\n".join(problems)


def test_compose_references_exist():
    problems = check_compose((REPO_ROOT / "docker-compose.yml").read_text(), REPO_ROOT)
    assert not problems, "\n".join(problems)


# --- the helpers really catch missing paths ----------------------------------


def test_tree_helper_rebuilds_nested_paths():
    snippet = "```\nrepo/\n├── app/\n│   └── core/\n│       └── config.py   # cfg\n└── README.md\n```\n"
    assert readme_tree_paths(snippet) == [
        "app",
        "app/core",
        "app/core/config.py",
        "README.md",
    ]


def test_helpers_report_bogus_paths():
    readme = (
        "```\nrepo/\n├── app/\n│   └── core/\n│       └── nope.py   # bogus\n└── README.md\n```\n"
        "```bash\npip install -r requirements-nope.txt\ncp nope.example .env\npytest nope_tests/\n```\n"
    )
    assert check_readme_tree(readme, REPO_ROOT) == [
        "README project tree lists missing path: app/core/nope.py"
    ]
    assert check_readme_commands(readme, REPO_ROOT) == [
        "README command names missing path: requirements-nope.txt",
        "README command names missing path: nope.example",
        "README command names missing path: nope_tests/",
    ]

    compose = """
services:
  web:
    build: {context: ., dockerfile: docker/Nope.Dockerfile}
    command: celery -A app.nope_app worker
    depends_on: [ghost]
    volumes:
      - ./logs:/app/logs
      - ./docker/nope.sql:/init.sql
"""
    assert check_compose(compose, REPO_ROOT) == [
        "compose service web: missing dockerfile docker/Nope.Dockerfile",
        "compose service web: missing bind-mount source ./docker/nope.sql",
        "compose service web: -A target app.nope_app is not a module under app/",
        "compose service web: depends_on names undefined service ghost",
    ]
