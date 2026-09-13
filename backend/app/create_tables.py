"""Dev convenience: create all tables directly from the SQLAlchemy models (no migration)."""
from app.core.db import Base, engine
from app import models  # noqa: F401 ensures all model modules are imported/registered


def main():
    Base.metadata.create_all(bind=engine)
    print("Tables created.")


if __name__ == "__main__":
    main()
