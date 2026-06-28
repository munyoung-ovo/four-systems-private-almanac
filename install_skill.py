import argparse
import os
import shutil
from pathlib import Path


SKILL_NAME = "huangdao-jiri"
EXCLUDE_DIRS = {
    ".git",
    ".codex",
    ".pytest_cache",
    "__pycache__",
    "tmp_install",
    ".skill_deps",
    ".venv",
    "venv",
    "env",
}
EXCLUDE_FILES = {
    "profiles/_active",
}
EXCLUDE_SUFFIXES = {
    ".pyc",
}
GENERATED_DIRS = {
    "outputs",
    "profiles",
    "materials",
}


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


def should_skip(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    parts = set(rel.parts)
    if parts & EXCLUDE_DIRS:
        return True
    if path.is_file() and path.suffix in EXCLUDE_SUFFIXES:
        return True
    if rel.as_posix() in EXCLUDE_FILES:
        return True
    if rel.parts and rel.parts[0] in GENERATED_DIRS:
        return path.name != ".gitkeep"
    return False


def copy_skill(root: Path, target: Path) -> None:
    root = root.resolve()
    target = target.resolve()
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    for src in root.rglob("*"):
        resolved_src = src.resolve()
        if resolved_src == target or target in resolved_src.parents:
            continue
        if should_skip(src, root):
            continue
        dst = target / src.relative_to(root)
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def install(root: Path) -> None:
    target = default_codex_home() / "skills" / SKILL_NAME
    copy_skill(root, target)
    print(f"Codex: {target}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Install this skill for Codex."
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    install(root)


if __name__ == "__main__":
    main()
