"""Interactively generate the bcrypt value used by HOMEPAGE_UPLOAD_PASS_HASH."""

from __future__ import annotations

from getpass import getpass

from passlib.context import CryptContext


def main() -> None:
    password = getpass("New upload password: ")
    confirmation = getpass("Confirm password: ")
    if not password:
        raise SystemExit("password cannot be empty")
    if password != confirmation:
        raise SystemExit("passwords do not match")
    context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    print(context.hash(password))


if __name__ == "__main__":
    main()
