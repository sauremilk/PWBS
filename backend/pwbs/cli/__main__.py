"""Entry point for `python -m pwbs.cli` (TASK-198)."""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pwbs.cli",
        description="PWBS CLI tools",
    )
    sub = parser.add_subparsers(dest="command")

    # --- seed sub-command ---
    seed_parser = sub.add_parser("seed", help="Generate realistic demo data")
    seed_parser.add_argument(
        "--user",
        default="demo@pwbs.dev",
        help="Demo user email (default: demo@pwbs.dev)",
    )
    seed_parser.add_argument(
        "--documents",
        type=int,
        default=50,
        help="Number of documents to generate (default: 50)",
    )
    seed_parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete all demo data instead of seeding",
    )

    args = parser.parse_args()

    if args.command == "seed":
        from pwbs.cli.seed import run_seed

        run_seed(
            user_email=args.user,
            document_count=args.documents,
            clean=args.clean,
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
