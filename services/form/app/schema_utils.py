from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def validate_schema_isolation(db_session: Session, schema_name: str = "form_schema"):
    """Verify all tables exist in the target schema, not public."""
    # First, log current search path and default schema
    try:
        search_path = db_session.execute(text("SHOW search_path")).scalar()
        logger.info(f"Current search_path: {search_path}")
    except Exception as e:  # pragma: no cover
        logger.warning(f"Could not retrieve search_path: {e}")

    result = db_session.execute(
        text("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = :schema AND table_type = 'BASE TABLE'
        """),
        {"schema": schema_name},
    )
    tables = [row[0] for row in result]
    logger.info(f"Tables found in schema '{schema_name}': {tables}")

    if not tables:
        # Check if they exist in public instead
        public_result = db_session.execute(
            text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            AND table_name IN ('forms', 'form_fields')
            """)
        )
        public_tables = [row[0] for row in public_result]
        if public_tables:  # pragma: no cover
            raise RuntimeError(
                f"Tables {public_tables} found in 'public' schema instead of '{schema_name}'. "
                "Alembic migration failed to isolate the schema."
            )
        else:  # pragma: no cover
            raise RuntimeError(
                f"No tables found in schema '{schema_name}'. "
                "Alembic migration may not have run or created tables in the wrong place."
            )
