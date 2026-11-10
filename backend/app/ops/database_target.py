"""Read only exported DATABASE_URL; print safe identity fields, never URL/query/secrets.

This helper does not connect, load dotenv, infer production, or execute migrations.
"""
import argparse
import json
import os
import sys
from sqlalchemy.engine import make_url


def safe_target(raw):
    try:
        url = make_url(raw)
        fields = {"driver": url.drivername, "hostname": url.host, "database": url.database, "user": url.username}
        if url.drivername != "postgresql+psycopg" or any(not isinstance(value, str) or not value or any(ord(c) < 32 or ord(c) == 127 for c in value) for value in fields.values()):
            raise ValueError()
        return fields
    except Exception:
        raise ValueError("DATABASE_URL is missing or invalid; target cannot be verified.") from None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspect exported database identity without printing credentials or connecting")
    parser.add_argument("--expect-host", required=True, help="Exact production Neon hostname from independently trusted inventory")
    parser.add_argument("--expect-database", required=True, help="Exact intended production database name")
    parser.add_argument("--expect-user", help="Optional expected database login")
    args = parser.parse_args(argv)
    try:
        target = safe_target(os.environ.get("DATABASE_URL"))
    except ValueError:
        print("STOP: exported DATABASE_URL is missing or invalid. No target verified.", file=sys.stderr)
        return 1
    print(json.dumps(target, ensure_ascii=True))
    if target["hostname"] != args.expect_host or target["database"] != args.expect_database or (args.expect_user is not None and target["user"] != args.expect_user):
        print("STOP: database target does not match the expected identity. Do not migrate.", file=sys.stderr)
        return 1
    print("Target matches the supplied identity. A human must still confirm this is the intended production Neon target before migration.")
    return 0
