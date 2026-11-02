"""Guard against README.md and docker-compose.yml naming files that do not exist.

Each check is a helper that takes the document's text plus an ``exists``
predicate over repo-relative paths, and returns a list of problems, every one
naming the missing path, so the checks can be exercised on hand-written
snippets as well as on the real files.

"Exists" means tracked by git (``git ls-files``, which includes staged files),
not merely present on disk: an untracked alembic/ dir or LICENSE on one
developer's machine must not hide a reference that a clean checkout would
break. Outside a git checkout (e.g. an unpacked source archive) the check
falls back to the working tree.
"""

from __future__ import annotations

import subprocess
import re
import shlex
from pathlib import Path, PurePosixPath
from typing import Callable

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

Exists = Callable[[str], bool]


def _normalize(rel: str) -> str:
    return str(PurePosixPath(rel.strip().rstrip("/") or "."))


def tracked_exists(root: Path) -> Exists:
    """Return a predicate: is this repo-relative path a git-tracked file or dir?"""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=True,
            capture_output=True,
        ).stdout.decode()
    except (OSError, subprocess.CalledProcessError):
        return lambda rel: (root / rel).exists()
    tracked: set[str] = {"."}
    for name in filter(None, out.split("\0")):
        path = PurePosixPath(name)
        tracked.add(str(path))
        tracked.update(str(parent) for parent in path.parents)
    return lambda rel: _normalize(rel) in tracked

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


def check_readme_tree(readme_text: str, exists: Exists) -> list[str]:
    paths = readme_tree_paths(readme_text)
    problems = [] if paths else ["README project tree not found"]
    problems += [
        f"README project tree lists missing path: {p}"
        for p in paths
        if not exists(p)
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


def check_readme_commands(readme_text: str, exists: Exists) -> list[str]:
    return [
        f"README command names missing path: {p}"
        for p in readme_command_paths(readme_text)
        if not exists(p)
    ]


def _module_exists(module: str, exists: Exists) -> bool:
    module = module.split(":", 1)[0]
    if not module.startswith("app."):
        return False
    rel = PurePosixPath(*module.split("."))
    return exists(str(rel.with_suffix(".py"))) or exists(str(rel / "__init__.py"))


def check_compose(compose_text: str, exists: Exists) -> list[str]:
    problems: list[str] = []
    services = (yaml.safe_load(compose_text) or {}).get("services") or {}
    for name, svc in services.items():
        build = svc.get("build")
        if isinstance(build, str):
            build = {"context": build}
        if isinstance(build, dict):
            dockerfile = _normalize(
                str(
                    PurePosixPath(build.get("context", "."))
                    / build.get("dockerfile", "Dockerfile")
                )
            )
            if not exists(dockerfile):
                problems.append(
                    f"compose service {name}: missing dockerfile {dockerfile}"
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
            if not exists(rel):
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
            if target and not _module_exists(target, exists):
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

EXISTS = tracked_exists(REPO_ROOT)


def test_readme_tree_paths_exist():
    problems = check_readme_tree((REPO_ROOT / "README.md").read_text(), EXISTS)
    assert not problems, "\n".join(problems)


def test_readme_command_paths_exist():
    problems = check_readme_commands((REPO_ROOT / "README.md").read_text(), EXISTS)
    assert not problems, "\n".join(problems)


def test_compose_references_exist():
    problems = check_compose((REPO_ROOT / "docker-compose.yml").read_text(), EXISTS)
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
    assert check_readme_tree(readme, EXISTS) == [
        "README project tree lists missing path: app/core/nope.py"
    ]
    assert check_readme_commands(readme, EXISTS) == [
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
    assert check_compose(compose, EXISTS) == [
        "compose service web: missing dockerfile docker/Nope.Dockerfile",
        "compose service web: missing bind-mount source ./docker/nope.sql",
        "compose service web: -A target app.nope_app is not a module under app/",
        "compose service web: depends_on names undefined service ghost",
    ]


def test_untracked_file_on_disk_does_not_count(tmp_path):
    """A file present on disk but never committed must still be reported."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "README.md").write_text("tracked")
    subprocess.run(["git", "-C", str(tmp_path), "add", "README.md"], check=True)
    (tmp_path / "LICENSE").write_text("untracked")
    (tmp_path / "alembic").mkdir()
    (tmp_path / "alembic" / "env.py").write_text("untracked")

    exists = tracked_exists(tmp_path)
    readme = "```\nrepo/\n├── alembic/\n├── LICENSE\n└── README.md\n```\n"
    assert check_readme_tree(readme, exists) == [
        "README project tree lists missing path: alembic",
        "README project tree lists missing path: LICENSE",
    ]
