import base64

from PySide6.QtCore import QSignalBlocker, QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
)

from radixscope.core.byte_inspection import parse_byte_input
from radixscope.gui.bitfields import BitfieldPanel
from radixscope.gui.widgets import Workspace


class ByteInspectorWorkspace(Workspace):
    page_bytes = 256

    def __init__(self) -> None:
        super().__init__(
            "Byte Inspector", "Select raw bytes and reinterpret their exact bit pattern"
        )
        self._buffer = b""
        self.input = QPlainTextEdit("3F 80 00 00")
        self.input.setMaximumHeight(100)
        self.input.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.input_format = QComboBox()
        self.input_format.addItems(["hex", "binary", "base64", "utf8"])
        self.byteorder = QComboBox()
        self.byteorder.addItems(["big", "little"])
        self.offset = QSpinBox()
        self.offset.setRange(0, 65535)
        self.length = QSpinBox()
        self.length.setRange(1, 65536)
        self.length.setValue(4)
        self.all_bytes = QCheckBox("Interpret from offset through the end of the buffer")
        self.all_bytes.setChecked(True)
        self.interpret_as = QComboBox()
        self.interpret_as.addItems(["unsigned integer", "signed integer", "binary16", "bfloat16",
                                    "binary32", "binary64"])
        self.convert_input_button = QPushButton("Convert buffer to selected input format")
        self.convert_input_button.setEnabled(False)
        self.convert_input_button.clicked.connect(self.convert_input)
        self.copy_bytes_button = QPushButton("Copy selected bytes")
        self.copy_bytes_button.setEnabled(False)
        self.copy_bytes_button.clicked.connect(self.copy_bytes)
        self._byte_page = QSpinBox()
        self._byte_page.setMinimum(1)
        self._byte_page.valueChanged.connect(self.display_bytes)
        self.byte_table = QTableWidget(0, 18)
        self.byte_table.setHorizontalHeaderLabels(
            ["Offset", *[f"{column:02X}" for column in range(16)], "ASCII"]
        )
        self.byte_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.byte_table.setSelectionMode(QAbstractItemView.SelectionMode.ContiguousSelection)
        self.byte_table.verticalHeader().setVisible(False)
        self.byte_table.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.byte_table.setMinimumHeight(130)
        self.byte_table.setMaximumHeight(240)
        self.byte_table.itemSelectionChanged.connect(self.select_range)
        self.form.addRow("Input", self.input)
        self.form.addRow("Input format", self.input_format)
        self.form.addRow("Format conversion", self.convert_input_button)
        self.form.addRow("Byte order", self.byteorder)
        self.form.addRow("Selection offset", self.offset)
        self.form.addRow("Selection length", self.length)
        self.form.addRow("Selection mode", self.all_bytes)
        self.form.addRow("Interpret as", self.interpret_as)
        self.form.addRow("Byte view page", self._byte_page)
        self.form.addRow("Offset · Hex · ASCII", self.byte_table)
        self.form.addRow("Selected bytes", self.copy_bytes_button)
        self.bitfields = BitfieldPanel()
        self.form.addRow("Bitfield layout", self.bitfields)
        self.bitfields.pattern_requested.connect(self.apply_pattern)
        self.result_invalidated.connect(self.bitfields.clear)
        self.run_button.setText("Inspect bytes")
        self.run_button.setEnabled(True)
        self.run_button.clicked.connect(self.start_calculation)
        self.result_ready.connect(self.show_bytes)
        self.result_invalidated.connect(lambda: self.byte_table.setEnabled(False))
        self.result_invalidated.connect(lambda: self.copy_bytes_button.setEnabled(False))
        self.all_bytes.toggled.connect(self.update_controls)
        self.interpret_as.currentIndexChanged.connect(self.update_type)
        self.update_controls()
        self.bind_inputs()
        self._refresh = QTimer(self)
        self._refresh.setSingleShot(True)
        self._refresh.setInterval(150)
        self._refresh.timeout.connect(self.start_calculation)
        self.input.textChanged.connect(self.clear_buffer)
        for spin in (self.offset, self.length):
            spin.valueChanged.connect(lambda: self._refresh.start())
        for combo in (self.byteorder, self.interpret_as):
            combo.currentIndexChanged.connect(lambda: self._refresh.start())
        self.all_bytes.toggled.connect(lambda: self._refresh.start())

    def update_controls(self) -> None:
        self.length.setEnabled(not self.all_bytes.isChecked())

    def update_type(self) -> None:
        sizes = {"binary16": 2, "bfloat16": 2, "binary32": 4, "binary64": 8}
        count = sizes.get(self.interpret_as.currentText())
        if count is not None:
            self.all_bytes.setChecked(False)
            self.length.setValue(count)

    def clear_buffer(self) -> None:
        self._buffer = b""
        self.byte_table.setRowCount(0)
        self.convert_input_button.setEnabled(False)

    def show_bytes(self, title: str, report: dict[str, object]) -> None:
        self._buffer = parse_byte_input(self.input.toPlainText(), self.input_format.currentText())
        blocker = QSignalBlocker(self._byte_page)
        self._byte_page.setMaximum((len(self._buffer) + self.page_bytes - 1) // self.page_bytes)
        self._byte_page.setValue(self.offset.value() // self.page_bytes + 1)
        del blocker
        self.convert_input_button.setEnabled(True)
        self.copy_bytes_button.setEnabled(True)
        self.byte_table.setEnabled(True)
        self.display_bytes()
        bits = report.get("bits")
        if isinstance(bits, str):
            self.bitfields.set_pattern(int(bits, 2), len(bits))

    def apply_pattern(self, pattern: int) -> None:
        if self._report is None:
            return
        offset, length = self._report["offset"], self._report["length"]
        assert isinstance(offset, int) and isinstance(length, int)
        replacement = pattern.to_bytes(
            length, "little" if self.byteorder.currentText() == "little" else "big"
        )
        data = self._buffer[:offset] + replacement + self._buffer[offset + length:]
        blocker = QSignalBlocker(self.input_format)
        self.input_format.setCurrentText("hex")
        del blocker
        self.input.setPlainText(data.hex(" ").upper())
        self.start_calculation()

    def display_bytes(self) -> None:
        blocker = QSignalBlocker(self.byte_table)
        start = (self._byte_page.value() - 1) * self.page_bytes
        data = self._buffer[start:start + self.page_bytes]
        self.byte_table.setRowCount((len(data) + 15) // 16)
        self.byte_table.clearContents()
        selected_end = len(self._buffer) if self.all_bytes.isChecked() else (
            self.offset.value() + self.length.value()
        )
        for row, position in enumerate(range(0, len(data), 16)):
            chunk = data[position:position + 16]
            self.byte_table.setItem(row, 0, QTableWidgetItem(f"{start + position:08X}"))
            for column, byte in enumerate(chunk, 1):
                item = QTableWidgetItem(f"{byte:02X}")
                self.byte_table.setItem(row, column, item)
                absolute = start + position + column - 1
                item.setToolTip(f"Offset {absolute} (0x{absolute:X})")
                item.setSelected(self.offset.value() <= absolute < selected_end)
            preview = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in chunk)
            self.byte_table.setItem(row, 17, QTableWidgetItem(preview))
        self.byte_table.resizeColumnsToContents()
        del blocker

    def select_range(self) -> None:
        if not self._buffer or not self.byte_table.isEnabled():
            return
        start = (self._byte_page.value() - 1) * self.page_bytes
        positions = sorted({start + index.row() * 16 + index.column() - 1
                            for index in self.byte_table.selectedIndexes()
                            if 1 <= index.column() <= 16})
        positions = [position for position in positions if position < len(self._buffer)]
        if not positions:
            return
        if positions[-1] - positions[0] + 1 != len(positions):
            self.status.setText("Select consecutive bytes or enter an offset and length")
            return
        blockers = [QSignalBlocker(widget) for widget in (self.offset, self.length, self.all_bytes)]
        self.offset.setValue(positions[0])
        self.length.setValue(len(positions))
        self.all_bytes.setChecked(False)
        del blockers
        self.update_controls()
        self.start_calculation()

    def copy_bytes(self) -> None:
        if self._report is not None:
            QApplication.clipboard().setText(str(self._report["bytes"]))

    def convert_input(self) -> None:
        if not self._buffer:
            return
        format_ = self.input_format.currentText()
        data = self._buffer
        if format_ == "hex":
            text = data.hex(" ").upper()
        elif format_ == "binary":
            text = " ".join(f"{byte:08b}" for byte in data)
        elif format_ == "base64":
            text = base64.b64encode(data).decode("ascii")
        else:
            try:
                text = data.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                self.set_error("Buffer is not valid UTF-8; choose a lossless byte format")
                return
        self.input.setPlainText(text)
        self.start_calculation()

    def restore_state(self, state: dict[str, object]) -> None:
        super().restore_state(state)
        if "bitfields" in state:
            self.bitfields.restore_state(state["bitfields"])
        self.update_controls()
        self._refresh.stop()

    def snapshot(self) -> dict[str, object]:
        state = super().snapshot()
        state["bitfields"] = self.bitfields.snapshot()
        return state

    def cancel_calculation(self) -> None:
        if hasattr(self, "_refresh"):
            self._refresh.stop()
        super().cancel_calculation()
