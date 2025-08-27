# create_schema.py
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
from .models import Base
# Use your DB URL; per your setup:

def init_db(DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/postgres"):
    engine = create_engine(DATABASE_URL, future=True)

    with engine.connect() as conn:
        # Enable required extensions (must be superuser or have privileges)
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb;"))
        except ProgrammingError as e:
            # Don’t continue if extensions can’t be created
            raise RuntimeError(
                "Failed to create required extensions (postgis/timescaledb). "
                "Ensure you’re connected as a superuser and that TimescaleDB "
                "is installed & shared_preload_libraries includes 'timescaledb'."
            ) from e

        # Ensure schema exists
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS public;"))
        conn.commit()

    # Create all tables first
    Base.metadata.create_all(engine)

    # Now convert the table to a hypertable
    # - schema-qualified table name
    # - ::regclass avoids string-to-name issues
    # - if_not_exists => TRUE makes it idempotent
    # - migrate_data => TRUE allows conversion if rows already exist
    with engine.connect() as conn:
        conn.execute(text("""
            SELECT create_hypertable(
                'public.detections_gis'::regclass,
                'timestamp',
                if_not_exists => TRUE,
                migrate_data  => TRUE
            );
        """))
        conn.commit()

    print("✅ Schema created successfully.")


