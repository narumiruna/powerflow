"""PowerFlow CLI entry point - launches TUI by default."""

import sys

from .tui.app import run_app


def main() -> None:
    """Main entry point for PowerFlow CLI.

    Directly launches the Textual TUI (no subcommands needed).
    """
    # Check platform
    if sys.platform != "darwin":
        print("Error: PowerFlow only supports macOS", file=sys.stderr)
        sys.exit(1)

    # Launch TUI
    try:
        run_app()
    except KeyboardInterrupt:
        print("\nExiting PowerFlow...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
