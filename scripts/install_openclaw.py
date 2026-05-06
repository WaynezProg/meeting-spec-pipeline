#!/usr/bin/env python3
import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any


PLUGIN_ID = "meeting-transcribe-cloud"
SKILL_ID = "meeting-spec-pipeline"
DEFAULT_PLUGIN_CONFIG = {
    "defaultProvider": "mock",
    "providers": {
        "mock": {},
    },
}


def append_unique(values: list[Any], value: str) -> list[Any]:
    return values if value in values else [*values, value]


def read_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_config(path: Path, config: dict[str, Any], dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_suffix(path.suffix + ".meeting-spec-pipeline.bak")
        shutil.copy2(path, backup)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def install_skill(repo_root: Path, openclaw_home: Path, dry_run: bool) -> Path:
    src = repo_root / "skills" / SKILL_ID
    dst = openclaw_home / "workspace" / "skills" / SKILL_ID
    if dry_run:
        return dst
    if not src.exists():
        raise FileNotFoundError(f"Skill source not found: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return dst


def patch_plugin_config(config: dict[str, Any], plugin_path: Path) -> dict[str, Any]:
    plugins = config.setdefault("plugins", {})

    load = plugins.setdefault("load", {})
    paths = load.get("paths")
    if not isinstance(paths, list):
        paths = []
    load["paths"] = append_unique(paths, str(plugin_path))

    allow = plugins.get("allow")
    if not isinstance(allow, list):
        allow = []
    plugins["allow"] = append_unique(allow, PLUGIN_ID)

    entries = plugins.setdefault("entries", {})
    entry = entries.setdefault(PLUGIN_ID, {})
    entry["enabled"] = True
    entry.setdefault("config", DEFAULT_PLUGIN_CONFIG)
    return config


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Meeting Spec Pipeline into OpenClaw.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    openclaw_home = Path(os.environ.get("OPENCLAW_HOME", "~/.openclaw")).expanduser()
    config_path = Path(
        os.environ.get("OPENCLAW_CONFIG_FILE", openclaw_home / "openclaw.json")
    ).expanduser()
    plugin_path = (repo_root / "plugins" / PLUGIN_ID).resolve()

    if not plugin_path.exists():
        raise FileNotFoundError(f"Plugin source not found: {plugin_path}")

    skill_dst = install_skill(repo_root, openclaw_home, args.dry_run)
    config = patch_plugin_config(read_config(config_path), plugin_path)
    write_config(config_path, config, args.dry_run)

    print(json.dumps({
        "openclaw_config": str(config_path),
        "skill_path": str(skill_dst),
        "plugin_path": str(plugin_path),
        "plugin_id": PLUGIN_ID,
        "dry_run": args.dry_run,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
