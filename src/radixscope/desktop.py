import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        if len(sys.argv) != 3:
            return 2
        from radixscope.calculations import execute_request

        return execute_request(Path(sys.argv[2]))
    from radixscope.gui import main as gui_main

    return gui_main()


if __name__ == "__main__":
    raise SystemExit(main())
