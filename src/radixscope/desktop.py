import json
import os
import sys
import traceback
from pathlib import Path


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        if len(sys.argv) != 3:
            return 2
        from radixscope.calculations import execute_request

        return execute_request(Path(sys.argv[2]))
    if len(sys.argv) > 1 and sys.argv[1] == "--self-check":
        if len(sys.argv) != 3:
            return 2
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        receipt: dict[str, object]
        try:
            from radixscope.gui.verification import verify_desktop

            receipt = verify_desktop()
        except Exception:
            receipt = {"status": "error", "traceback": traceback.format_exc()}
        try:
            Path(sys.argv[2]).write_text(
                json.dumps(receipt, ensure_ascii=True, indent=2), encoding="utf-8"
            )
        except OSError:
            return 1
        return 0 if receipt["status"] == "ok" else 1
    from radixscope.gui import main as gui_main

    return gui_main()


if __name__ == "__main__":
    raise SystemExit(main())
