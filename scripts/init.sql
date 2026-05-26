-- Creates isolated schemas for each service.
-- Runs automatically when the Postgres container starts for the first time.

CREATE SCHEMA IF NOT EXISTS auth_schema;
CREATE SCHEMA IF NOT EXISTS form_schema;
CREATE SCHEMA IF NOT EXISTS workflow_schema;
CREATE SCHEMA IF NOT EXISTS task_schema;
CREATE SCHEMA IF NOT EXISTS notification_schema;

-- Grant permissions to pk_user (who is the owner/db user)
GRANT ALL ON SCHEMA auth_schema         TO pk_user;
GRANT ALL ON SCHEMA form_schema         TO pk_user;
GRANT ALL ON SCHEMA workflow_schema     TO pk_user;
GRANT ALL ON SCHEMA task_schema         TO pk_user;
GRANT ALL ON SCHEMA notification_schema TO pk_user;
