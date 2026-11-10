"""Operational CLI uses the same settings service. It never accepts command-line secrets."""
import argparse
import getpass
import json
import os
import sys
import warnings
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.llm.schemas import PROVIDERS, ProviderUpdate, validate_scope
from app.llm.errors import SettingsInvalid


class UnsafeTarget(Exception):
    pass


def checked_target(raw_url, *, allow_remote=False, confirmation=None):
    try:
        url = make_url(raw_url)
        local = (url.drivername, url.host, url.port, url.database, url.username) == (
            "postgresql+psycopg", "127.0.0.1", 5432, "sandcastle_dev", "sandcastle_dev")
        if not local and not (allow_remote and url.drivername == "postgresql+psycopg" and url.host
                              and confirmation == f"{url.host}:{url.port or 5432}/{url.database}"):
            raise ValueError()
        return url
    except Exception:
        raise UnsafeTarget("Refusing unverified database target. Use verified sandcastle_dev; remote writes require --allow-production-write and --confirm-database-target HOST:PORT/DATABASE.") from None


def parser():
    result = argparse.ArgumentParser(description="Configure user-scoped Sandcastle LLM credentials securely")
    identity = result.add_mutually_exclusive_group(required=True)
    identity.add_argument("--user-id", dest="user_id", help="IS OIDC sub value used by Sandcastle as user identity")
    identity.add_argument("--is-subject", dest="user_id", help="Alias for --user-id; exact IS OIDC sub, never email")
    result.add_argument("--provider", required=True, choices=PROVIDERS)
    action = result.add_mutually_exclusive_group()
    action.add_argument("--show", action="store_true", help="Read safe settings without decrypting")
    action.add_argument("--disable", action="store_true", help="Disable while preserving credentials")
    action.add_argument("--enable", action="store_true", help="Re-enable while preserving credentials")
    action.add_argument("--remove-credentials", action="store_true", help="Confirm removal interactively")
    result.add_argument("--default-model", help="Optional non-secret provider model ID")
    result.add_argument("--allow-production-write", action="store_true")
    result.add_argument("--confirm-database-target", help="Exact HOST:PORT/DATABASE for a deliberate remote target")
    return result


def configure(db, args, *, read_secret=None, read_input=None, output=print):
    """Injected I/O keeps tests noninteractive; no alternative secret-input channel."""
    read_secret = read_secret or getpass.getpass
    read_input = read_input or input
    validate_scope(args.user_id)
    from app.llm import service
    try:
        row = service.get_provider_config(db, args.user_id, args.provider)
        if args.show:
            output(json.dumps(service.provider_view(row, args.provider).model_dump()))
            return
        if args.remove_credentials:
            if read_input("Type REMOVE to delete this provider credential and disable it: ") != "REMOVE":
                output("Credential removal cancelled.")
                return
            result = service.remove_credentials(db, args.user_id, args.provider)
        else:
            values = {}
            if args.disable or args.enable:
                values["enabled"] = not args.disable
            else:
                # getpass can fall back to echoed stdin. Refuse that fallback in production CLI.
                with warnings.catch_warnings():
                    warnings.simplefilter("error", getpass.GetPassWarning)
                    secret = read_secret("API key (hidden; blank preserves existing): ")
                if secret:
                    values["credentials"] = {"api_key": secret}
                model = args.default_model
                if model is None:
                    current = (row.config.get("default_model") if row else None) or ""
                    model = read_input(f"Default model [{current or 'not set'}]: ").strip() or current
                values["config"] = {"default_model": model or None}
                values["enabled"] = read_input("Enabled [Y/n]: ").strip().lower() not in {"n", "no"}
            if args.default_model is not None:
                values["config"] = {"default_model": args.default_model}
            result = service.set_provider_config(db, args.user_id, args.provider, ProviderUpdate.model_validate(values))
        output("Provider configuration updated.")
        output(f"Enabled: {'yes' if result.enabled else 'no'}; credentials configured: {'yes' if result.has_credentials else 'no'}")
    except Exception:
        db.rollback()
        # Do not print exception strings, validation inputs, SQL parameters, or ciphertext.
        raise RuntimeError("Provider configuration failed; transaction rolled back. Check target, model, and encryption configuration.") from None


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        validate_scope(args.user_id)
        load_dotenv(Path(__file__).resolve().parents[2] / ".env")
        url = checked_target(os.getenv("DATABASE_URL"), allow_remote=args.allow_production_write,
                             confirmation=args.confirm_database_target)
        if not args.show and not sys.stdin.isatty():
            raise RuntimeError("Use an interactive terminal for provider configuration; secret input over stdin is unsupported.")
        print(f"Database: {url.database}\nHost: {url.host}:{url.port or 5432}\nScope: user\nUser: {args.user_id}\nProvider: {args.provider}")
        engine = create_engine(url, hide_parameters=True)
        try:
            with Session(engine) as db:
                actual = db.execute(text("SELECT current_database(), current_user")).one()
                if tuple(actual) != (url.database, url.username):
                    raise UnsafeTarget("Connected database identity does not match the selected target")
                configure(db, args)
        finally:
            engine.dispose()
        return 0
    except (UnsafeTarget, SettingsInvalid) as error:
        print(str(error), file=sys.stderr)
    except Exception:
        print("Provider operation failed. Verify database target, migrations, encryption key, and interactive input. No secret details are displayed.", file=sys.stderr)
    return 1
