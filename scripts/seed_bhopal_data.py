import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.db.session import SessionLocal
from backend.app.db.init_db import init_db

if __name__ == "__main__":
    print("Seeding Bhopal network graph, traffic states, and demo fleet...")
    db = SessionLocal()
    try:
        init_db(db)
        print("Data seeding completed successfully!")
    finally:
        db.close()
