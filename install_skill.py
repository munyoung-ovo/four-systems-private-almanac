import argparse
import os
import shutil
from pathlib import Path


SKILL_NAME = "huangdao-jiri"
EXCLUDE_DIRS = {
    ".git",
    ".claude",
    ".codex",
    ".pytest_cache",
    "__pycache__",
    "tmp_install",
    "tmp_install_zip_test",
    "test_copy_smoke",
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


def default_claude_home() -> Path:
    return Path(os.environ.get("CLAUDE_HOME", Path.home() / ".claude"))


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

    for current, dirs, files in os.walk(root):
        current_path = Path(current).resolve()
        if current_path == target or target in current_path.parents:
            dirs[:] = []
            continue

        dirs[:] = [
            d for d in dirs
            if d not in EXCLUDE_DIRS
            and not should_skip(Path(current) / d, root)
            and (Path(current) / d).resolve() != target
            and target not in (Path(current) / d).resolve().parents
        ]

        for filename in files:
            src = Path(current) / filename
            if should_skip(src, root):
                continue
            dst = target / src.relative_to(root)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def install(root: Path, include_codex: bool, include_claude: bool) -> None:
    targets = []
    if include_codex:
        targets.append(("Codex", default_codex_home() / "skills" / SKILL_NAME))
    if include_claude:
        targets.append(("Claude Code", default_claude_home() / "skills" / SKILL_NAME))

    for label, target in targets:
        copy_skill(root, target)
        print(f"{label}: {target}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Install this skill for Codex and Claude Code."
    )
    parser.add_argument("--codex-only", action="store_true")
    parser.add_argument("--claude-only", action="store_true")
    args = parser.parse_args()

    if args.codex_only and args.claude_only:
        parser.error("choose at most one of --codex-only or --claude-only")

    root = Path(__file__).resolve().parent
    install(
        root,
        include_codex=not args.claude_only,
        include_claude=not args.codex_only,
    )


if __name__ == "__main__":
    main()
