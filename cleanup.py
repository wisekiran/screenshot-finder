import argparse

from storage import expire_web_uploads, initialize_database


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean up web screenshots indexed over 24 hours ago."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Delete expired images and records; otherwise only count them.",
    )
    args = parser.parse_args()

    initialize_database()

    count = expire_web_uploads(dry_run=not args.apply)

    if args.apply:
        print(f"Deleted {count} expired screenshot(s).")
    else:
        print(f"Found {count} expired screenshot(s). No files deleted.")


if __name__ == "__main__":
    main()