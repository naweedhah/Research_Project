-- Least-privilege roles for the Child Nutrition Intelligence Platform.
-- Passwords are development defaults; override in production.

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'cnip_app') THEN
    CREATE ROLE cnip_app LOGIN PASSWORD 'cnip_app_dev_password';
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'cnip_readonly') THEN
    CREATE ROLE cnip_readonly LOGIN PASSWORD 'cnip_readonly_dev_password';
  END IF;
END
$$;

GRANT CONNECT ON DATABASE cnip TO cnip_app, cnip_readonly;
