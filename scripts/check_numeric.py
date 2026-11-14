"""Dependency-free numeric regression checks; optional Qt and packaged Windows checks."""

import argparse
import ctypes
import json
import math
import os
import random
import struct
import subprocess
import sys
import tempfile
import time
from fractions import Fraction
from pathlib import Path

from radixscope.cli import build_parser, run_command
from radixscope.core import (
    ExactValue,
    FixedWidthInteger,
    FloatClass,
    FloatOperation,
    IEEEFormat,
    analyze_integer_width,
    compare_numeric_inputs,
    decode_ieee754,
    encode_ieee754,
    evaluate_expression,
    experiment_float_arithmetic,
    format_exact,
    parse_float_operand,
    parse_number,
    trace_value,
)
from radixscope.core.float_arithmetic import _round_finite
from radixscope.core.precision import power_of_two


def check_core(exhaustive: bool) -> None:
    rng = random.Random(754)
    for base in range(2, 37):
        for _ in range(40):
            value = ExactValue(rng.randrange(-10000, 10000), rng.randrange(1, 18))
            assert parse_number(format_exact(value, base), base) == value
    assert evaluate_expression("0xFF + 1/3 + 0.(6)") == ExactValue(256)
    assert evaluate_expression("(-5//2) + (13%5) + ((0xF&3)<<2)") == ExactValue(12)
    assert parse_number("1.25e-3", 10) == ExactValue(1, 800)
    assert trace_value(ExactValue(1, 7), 10, max_steps=2).complete is False
    assert trace_value(ExactValue(1, 7), 10, max_steps=6).recurring_start == 0
    for width in (1, 8, 16, 32, 64, 257):
        for signed in (False, True):
            lo = -(1 << (width - 1)) if signed else 0
            hi = (1 << (width - int(signed))) - 1
            for value in (lo - 1, lo, hi, hi + 1):
                analysis = analyze_integer_width(value, width, signed)
                assert analysis.fits_selected == (lo <= value <= hi)
            for value in (lo, hi):
                integer = FixedWidthInteger(value, width, signed)
                assert FixedWidthInteger.from_bits(integer.bits, signed=signed) == integer
                assert integer.extract_bits(0, width, signed) == integer
    for fmt in (IEEEFormat.BINARY16, IEEEFormat.BFLOAT16):
        patterns = range(65536) if exhaustive else [0, 1, 0x8000, 0xFFFF, *range(0, 65536, 61)]
        for pattern in patterns:
            value = decode_ieee754(pattern, fmt)
            host = (
                struct.unpack(">e", pattern.to_bytes(2, "big"))[0]
                if fmt == 16
                else (struct.unpack(">f", (pattern << 16).to_bytes(4, "big"))[0])
            )
            if math.isfinite(host):
                assert value.exact is not None and value.exact.fraction == Fraction(host)
                assert (
                    encode_ieee754(
                        value.exact, fmt, negative_zero=host == 0 and bool(pattern & 0x8000)
                    ).pattern
                    == pattern
                )
            else:
                assert value.classification == (
                    FloatClass.NAN if math.isnan(host) else FloatClass.INFINITY
                )
    for fmt in IEEEFormat:
        tiny = power_of_two(1 - fmt.bias - fmt.fraction_width)
        experiment = experiment_float_arithmetic(tiny, ExactValue(1, 2), "multiply", fmt)
        assert experiment.rounded_operands.flags.underflow
        assert not experiment_float_arithmetic(
            tiny, ExactValue(1), "multiply", fmt
        ).rounded_operands.flags.underflow
        assert experiment_float_arithmetic(
            ExactValue(1), ExactValue(0), "divide", fmt
        ).rounded_operands.flags.divide_by_zero
        assert experiment_float_arithmetic(
            ExactValue(0), ExactValue(0), "divide", fmt
        ).rounded_operands.flags.invalid
        for operation in FloatOperation:
            a, b = parse_float_operand("0.1", fmt), parse_float_operand("0.2", fmt)
            assert (
                experiment_float_arithmetic(a, b, operation, fmt).rounded_operands.value.format
                == fmt
            )
        assert (
            experiment_float_arithmetic(
                parse_float_operand("-0", fmt), parse_float_operand("-0", fmt), "add", fmt
            ).rounded_operands.value.sign_bit
            == 1
        )
    source = decode_ieee754(0x380FFFFFE1000000, 64).exact
    assert source is not None
    boundary = _round_finite(source, IEEEFormat.BINARY32)
    assert boundary.value.pattern == 0x00800000 and boundary.flags.underflow
    comparison = compare_numeric_inputs("255", "127", width=8)
    assert comparison.changed_positions == (7,) and comparison.difference == ExactValue(128)
    fractional = compare_numeric_inputs("1/3", "2/3")
    assert fractional.xor is None and fractional.difference == ExactValue(-1, 3)
    parser = build_parser()
    for command in [
        ["convert", "FF", "--from", "16", "--to", "10"],
        ["expression", "0xFF + 1"],
        ["integer", "127", "--width", "8", "--signed", "--op", "add", "--operand", "1"],
        ["ieee", "compare", "0.1"],
        ["inspect", "1", "--type", "bfloat16"],
        ["compare-numbers", "1/3", "2/3"],
        ["float-op", "add", "0.1", "0.2", "--format", "binary16"],
        ["batch", "1\nbad\n3", "--exact"],
    ]:
        assert isinstance(run_command(parser.parse_args(command)), dict)
    print(
        "Core numeric, IEEE, arithmetic flags and CLI checks passed"
    )


def check_desktop() -> list[tuple[str, dict[str, object]]]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from radixscope.calculations import calculate
    from radixscope.gui.app import MainWindow, create_application
    from radixscope.gui.icon import ICON_SIZES, icon_image
    from radixscope.settings import SettingsStore

    app = create_application()
    states: list[tuple[str, dict[str, object]]] = []
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "state.json"
        window = MainWindow(SettingsStore(path))
        window.show()
        for language in ("en", "ko"):
            for theme in ("Light", "Dark"):
                window.store.preferences.update(language=language, theme=theme)
                window.apply_language()
                window.apply_theme()
                for index, workspace in enumerate(window.workspaces):
                    window.tabs.setCurrentIndex(index)
                    workspace.set_result(calculate(workspace.title, workspace.snapshot()))
                    for width, height in ((640, 480), (1000, 720)):
                        window.resize(width, height)
                        app.processEvents()
                        assert window.width() == width and workspace.run_button.isVisible()
        for workspace in window.workspaces:
            states.append((workspace.title, workspace.snapshot()))
        inspector = window.workspaces[2]
        for analysis in ("Format comparison", "Numeric comparison", "Floating-point arithmetic"):
            state = dict(
                inspector.snapshot(),
                analysis=analysis,
                input="0.1",
                other_input="0.2",
                data_type="binary16",
                input_mode="Expression",
            )
            inspector.restore_state(state)
            inspector.set_result(calculate(inspector.title, inspector.snapshot()))
            assert inspector.current_report() is not None
            states.append((inspector.title, inspector.snapshot()))
        for size in ICON_SIZES:
            image = icon_image(size)
            assert image.size().width() == size and image.pixelColor(0, 0).alpha() == 0
        window.save_preferences()
        window.close()
        restored = MainWindow(SettingsStore(path))
        assert restored.workspaces[2].snapshot()["analysis"] == "Floating-point arithmetic"
        assert restored.workspaces[2].current_report() is None
        restored.close()
        QApplication.processEvents()
    print(
        "Qt workspaces, modes, sizes, themes, languages, icons and restoration passed"
    )
    return states


def check_executable(executable: Path, states: list[tuple[str, dict[str, object]]]) -> None:
    if sys.platform != "win32":
        raise RuntimeError("EXE verification requires Windows")
    import pefile
    from PySide6.QtGui import QImage

    from radixscope.calculations import calculate
    from radixscope.gui.icon import ICON_SIZES

    pe = pefile.PE(str(executable))
    assert pe.FILE_HEADER.Machine == 0x8664
    icons: dict[int, bytes] = {}
    groups: list[bytes] = []
    for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if entry.id in (3, 14):
            for resource in entry.directory.entries:
                data = resource.directory.entries[0].data.struct
                payload = pe.get_data(data.OffsetToData, data.Size)
                if entry.id == 3:
                    icons[resource.id] = payload
                else:
                    groups.append(payload)
    assert len(groups) == 1
    group = groups[0]
    assert struct.unpack_from("<HHH", group) == (0, 1, 7)
    for index, size in enumerate(ICON_SIZES):
        width, height, _, _, _, bits, length, identifier = struct.unpack_from(
            "<BBBBHHIH", group, 6 + index * 14
        )
        payload = icons[identifier]
        assert (width or 256) == size and (height or 256) == size and bits == 32
        assert len(payload) == length
        expected = executable.parents[2] / "build" / "windows" / f"radixscope-{size}.png"
        assert payload == expected.read_bytes()
        image = QImage.fromData(payload)
        assert not image.isNull() and image.pixelColor(0, 0).alpha() == 0
    versions = [item for group_ in pe.FileInfo for item in group_ if item.Key == b"StringFileInfo"]
    assert versions[0].StringTable[0].entries[b"ProductVersion"] == b"1.0.0"
    env = dict(os.environ)
    env.pop("QT_QPA_PLATFORM", None)
    env.pop("PYTHONPATH", None)
    for title, state in states:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "request.json").write_text(
                json.dumps({"workspace": title, "state": state}), encoding="utf-8"
            )
            subprocess.run(
                [str(executable), "--worker", directory], env=env, check=True, timeout=45
            )
            result = json.loads((path / "result.json").read_text(encoding="utf-8"))
            assert "report" in result, result
            assert result["report"] == calculate(title, state)
    user32 = ctypes.windll.user32
    user32.SendMessageW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_size_t,
        ctypes.c_ssize_t,
    ]
    user32.SendMessageW.restype = ctypes.c_ssize_t
    user32.IsWindowVisible.argtypes = [ctypes.c_void_p]
    user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    user32.EnumWindows.argtypes = [callback_type, ctypes.c_void_p]
    process = subprocess.Popen([str(executable)], env=env)
    window_handles: list[int] = []

    @callback_type
    def collect(handle: int, unused: int) -> bool:
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        if pid.value == process.pid and user32.IsWindowVisible(handle):
            window_handles.append(handle)
        return True

    try:
        deadline = time.monotonic() + 45
        while not window_handles and time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"GUI exited before its window appeared: {process.returncode}")
            user32.EnumWindows(collect, None)
            time.sleep(0.1)
        assert window_handles, "packaged GUI did not show a native window"
        handle = window_handles[0]
        assert user32.SendMessageW(handle, 0x007F, 1, 0), "missing large window icon"
        assert user32.SendMessageW(handle, 0x007F, 0, 0) or user32.SendMessageW(
            handle, 0x007F, 2, 0
        ), "missing small window icon"
        user32.SendMessageW(handle, 0x0010, 0, 0)
        process.wait(timeout=15)
        assert process.returncode == 0
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    print(
        "Windows x64 EXE: resources, version, frozen workers, GUI icons and clean exit passed"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exhaustive", action="store_true")
    parser.add_argument("--desktop", action="store_true")
    parser.add_argument("--exe", type=Path)
    args = parser.parse_args()
    check_core(args.exhaustive)
    states = check_desktop() if args.desktop or args.exe else []
    if args.exe:
        check_executable(args.exe.resolve(), states)


if __name__ == "__main__":
    main()
