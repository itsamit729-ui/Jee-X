"""Import only the three sourced image questions. Safe to rerun (upserts by ref)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.database import SessionLocal
from app.importer import import_chapter_file

if __name__ == "__main__":
    path = Path(__file__).resolve().parents[2] / "generated/questions/physics/current-electricity-images.json"
    with SessionLocal() as db:
        result = import_chapter_file(db, path)
        print(result)
        if result["errors"]:
            raise SystemExit(1)
