#!/usr/bin/env python3
"""jig: Format lore.kernel mbox emails for replies."""

import argparse
import email
import os
import subprocess
import sys
from email import policy
from email.utils import format_datetime, parsedate_to_datetime


def download_mail(url: str) -> str:
    """Download mail content using b4 tool."""
    try:
        result = subprocess.run(
            ["b4", "mbox", "--single-message", "-o", "-", url],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except FileNotFoundError as e:
        raise RuntimeError("b4 not found. Ensure b4 is installed") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"b4 download failed:\n{e.stderr}") from e


def format_mail(mbox_content: str) -> str:
    """Format mbox content into a reply-ready plain text."""
    msg = email.message_from_string(mbox_content, policy=policy.default)

    subject = msg.get("Subject", "No Subject").strip()

    raw_date = msg.get("Date", "")
    try:
        dt = parsedate_to_datetime(raw_date)
        date_str = format_datetime(dt)
    except (ValueError, TypeError):
        date_str = raw_date.strip().replace("\n", " ") or "Unknown Date"

    from_str = msg.get("From", "Unknown Sender").strip().replace("\n", " ")

    body_part = msg.get_body(preferencelist=("plain",))
    if body_part:
        body = body_part.get_content()
    else:
        body = "[Warning: Plain text message not found]"

    lines = body.splitlines()
    quoted_lines = [f"> {line}" for line in lines]
    quoted_body = "\n".join(quoted_lines)

    return f"Subject: {subject}\n\nOn {date_str} {from_str} wrote:\n\n{quoted_body}\n"


def option_format(args: argparse.Namespace) -> None:
    """Handle the format command."""
    try:
        print(f"[*] Downloading mail from {args.url}")
        mbox_content = download_mail(args.url)

        print("[*] Formatting mail")
        formatted_text = format_mail(mbox_content)

        output_path = args.output or "formatted_reply.txt"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(formatted_text)

        print(f"\nFormatted! Saved at {os.path.abspath(output_path)}")

        if args.edit:
            editor = os.environ.get("EDITOR", "vim")
            print(f"[*] Executing editor: {editor}")
            subprocess.run([editor, output_path], check=True)
            print("[*] Edited!")

    except Exception as e:
        print(f"\n[!] Error: {e}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")

    subparsers = parser.add_subparsers(dest="command")

    format_parser = subparsers.add_parser(
        "format", help="Format the mbox file to a reply-ready plain text file."
    )
    format_parser.add_argument(
        "url",
        type=str,
        help="URL of the lore.kernel email.",
    )
    format_parser.add_argument(
        "--edit",
        action="store_true",
        help="Open the text file with $EDITOR after formatting.",
    )
    format_parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output path for the plain text file (not a directory).",
    )
    format_parser.set_defaults(func=option_format)

    args = parser.parse_args()

    # Show help if no command is provided
    if args.command is None:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
