import argparse
import json

from generate_requirement_spec import SPEC_SECTIONS


def validate_requirement_spec_sections(markdown: str) -> list[str]:
    missing = []
    for section in SPEC_SECTIONS:
        if f"## {section}" not in markdown:
            missing.append(section)
    return missing


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("requirement_spec_md")
    args = parser.parse_args()
    text = open(args.requirement_spec_md, encoding="utf-8").read()
    missing = validate_requirement_spec_sections(text)
    print(json.dumps({"missing_sections": missing}, ensure_ascii=False, indent=2))
    raise SystemExit(1 if missing else 0)


if __name__ == "__main__":
    main()
