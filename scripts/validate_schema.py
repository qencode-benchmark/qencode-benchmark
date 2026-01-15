import json
from pathlib import Path
from jsonschema import Draft202012Validator

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-dir", default=None, help="DB directory (default: <repo>/db)")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    schema_path = root / "schema_v1.json"
    db_dir = Path(args.db_dir).resolve() if args.db_dir else (root / "db")


    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    files = sorted([p for p in db_dir.glob("*.json") if p.name != "index.json"])
    ok = 0
    bad = 0

    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        if errors:
            bad += 1
            print(f"❌ {f.name}")
            for e in errors[:5]:
                print("   -", e.message)
        else:
            ok += 1
            print(f"✅ {f.name}")

    print(f"\nDone. OK={ok}, BAD={bad}, Total={ok+bad}")

if __name__ == "__main__":
    main()

