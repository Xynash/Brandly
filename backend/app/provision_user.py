"""Create a password account in an existing agency."""

import argparse
from getpass import getpass
import uuid

from sqlalchemy.exc import IntegrityError

from app.core.db import SessionLocal
from app.models import Agency, User
from app.services.auth import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agency-id", type=uuid.UUID, required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", choices=("admin", "writer"), default="writer")
    args = parser.parse_args()
    email, name = args.email.strip().lower(), args.name.strip()
    if not 0 < len(email) <= 320 or not 0 < len(name) <= 200:
        parser.error("Provide an email and display name")

    password = getpass("Temporary password: ")
    if not 15 <= len(password) <= 256 or password != getpass("Confirm password: "):
        parser.error("Passwords must match and contain 15 to 256 characters")

    try:
        with SessionLocal.begin() as db:
            if db.get(Agency, args.agency_id) is None:
                parser.error("Agency does not exist")
            db.add(User(
                agency_id=args.agency_id, password_hash=hash_password(password),
                email=email, full_name=name, role=args.role,
            ))
    except IntegrityError:
        parser.error("The user ID or email already has a Brandly membership")


if __name__ == "__main__":
    main()
