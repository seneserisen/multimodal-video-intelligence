from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


def main() -> None:
    instance_path, schema_path = map(Path, sys.argv[1:3])
    instance = json.loads(instance_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(instance)
    print(f"Validated {instance_path} against {schema_path}")


if __name__ == "__main__":
    main()
