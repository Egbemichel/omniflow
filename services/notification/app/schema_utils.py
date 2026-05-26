import os
from sqlalchemy import event


def _schema_name():
    # Return schema name from environment variable
    return os.getenv("DATABASE_SCHEMA")


def setup_schema_listeners(engine):
    """
    Sets up event listeners to handle schema switching.
    On SQLite, we strip the schema name since SQLite doesn't support schemas.
    On PostgreSQL, we keep it.
    """
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "before_cursor_execute", retval=True)
        def process_sql(conn, cursor, statement, parameters, context, execmany):
            # In SQLite, remove 'schema.' prefix from table names
            schema = _schema_name()
            if schema and f'"{schema}".' in statement:
                statement = statement.replace(f'"{schema}".', "")
            elif schema and f"{schema}." in statement:
                statement = statement.replace(f"{schema}.", "")
            return statement, parameters
