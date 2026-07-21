# physure/cli.py
import argparse
import sys

from physure.scripts.generate_types import generate


def main():
    """Entry point for the Physure CLI."""
    parser = argparse.ArgumentParser(description="Physure CLI Tool")
    subparsers = parser.add_subparsers(dest="command")

    # sync-types command
    _ = subparsers.add_parser(
        "sync-types", help="Generate type hints for available units."
    )

    # repl command
    repl_parser = subparsers.add_parser(
        "repl", help="Interactive unit-aware calculator (PHS syntax)."
    )
    repl_parser.add_argument(
        "expression",
        nargs="*",
        help="Evaluate this expression or file and exit instead of starting a REPL.",
    )

    # run command
    run_parser = subparsers.add_parser(
        "run", help="Run a .phs script file or PHS expression."
    )
    run_parser.add_argument(
        "expression",
        nargs="+",
        help="Path to .phs file or expression to execute.",
    )

    args = parser.parse_args()

    if args.command in ("repl", "run"):
        from physure.repl import main as repl_main

        sys.exit(repl_main(args.expression))

    if args.command == "sync-types":
        print("Synchronizing types for Physure units...")
        try:
            generate()
            print(
                "Successfully generated _generated_types.py and registry.pyi"
            )
        except Exception as e:
            print(f"Error generating types: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            from physure.repl import main as repl_main

            sys.exit(repl_main(sys.argv[1:]))

        parser.print_help()


if __name__ == "__main__":
    main()
