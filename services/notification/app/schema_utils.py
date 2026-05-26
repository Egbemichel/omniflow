import os
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def validate_schema_isolation(db_session: Session):
    """Validate that tables exist in the correct schema."""
    schema_name = os.getenv("DATABASE_SCHEMA", "notification_schema")
    service_name = "notification"

    try:
        search_path = db_session.execute(text("SHOW search_path")).scalar()
        logger.info(f"[{service_name}] Current search_path: {search_path}")
    except Exception as e:
        logger.warning(f"[{service_name}] Could not retrieve search_path: {e}")

    result = db_session.execute(
        text("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = :schema AND table_type = 'BASE TABLE'
        """),
        {"schema": schema_name},
    )
    tables = [row[0] for row in result]
    if not tables:
        logger.warning(f"[{service_name}] No tables found in schema '{schema_name}'.")
        return

    logger.info(
        f"[{service_name}] ✓ Schema '{schema_name}' contains {len(tables)} tables: {tables}"
    )
