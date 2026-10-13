import sys
from pathlib import Path

from radixscope.calculations import execute_request


def main() -> int:
    if len(sys.argv) != 2:
        return 2
    return execute_request(Path(sys.argv[1]))


if __name__ == "__main__":
    raise SystemExit(main())
