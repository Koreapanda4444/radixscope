from pathlib import Path

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
)

from radixscope.core import ExactValue
from radixscope.core.bitfields import BitfieldLayout
from radixscope.gui.bits import BitEditor
from radixscope.gui.i18n import UI_TEXT_ROLE, LocalizedComboBox, tr
from radixscope.gui.widgets import Workspace, control_row


class ComparisonWorkspace(Workspace):
    def __init__(self) -> None:
        super().__init__(
            "Binary Comparison", "Compare raw patterns, changed bits, bytes and fields"
        )
        self._layout = ""
        self._data: tuple[bytes, bytes] = (b"", b"")
        self.input = QPlainTextEdit("FF 00")
        self.other_input = QPlainTextEdit("FE 80")
        for editor in (self.input, self.other_input):
            editor.setMaximumHeight(80)
        self.input_format = LocalizedComboBox()
        self.input_format.addItems(["hex", "binary", "base64", "utf8"])
        self.byteorder = LocalizedComboBox()
        self.byteorder.addItems(["big", "little"])
        self.length_policy = LocalizedComboBox()
        self.length_policy.addItems(["equal", "zero-extend"])
        self._layout_label = QLabel("No bitfield layout")
        load = QPushButton("Load bitfield layout")
        clear = QPushButton("Clear bitfield layout")
        load.clicked.connect(self.load_layout)
        clear.clicked.connect(self.clear_layout)
        self.left_bits = BitEditor()
        self.right_bits = BitEditor()
        self.left_bits.read_only = self.right_bits.read_only = True
        self._summary = QLabel()
        self._summary.setWordWrap(True)
        self._page = QSpinBox()
        self._page.setMinimum(1)
        self._page.valueChanged.connect(self.show_byte_page)
        self.byte_table = QTableWidget(0, 4)
        self.byte_table.setHorizontalHeaderLabels(["Offset", "Left", "Right", "XOR"])
        self.byte_table.setMaximumHeight(180)
        self.byte_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.field_table = QTableWidget(0, 5)
        self.field_table.setHorizontalHeaderLabels(
            ["Field", "Left", "Right", "XOR bits", "Changed"]
        )
        self.field_table.setMaximumHeight(140)
        self.field_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.form.addRow("Left input", self.input)
        self.form.addRow("Right input", self.other_input)
        self.form.addRow("Format / order", control_row(self.input_format, self.byteorder))
        self.form.addRow("Length policy", self.length_policy)
        self.form.addRow("Bitfield layout", self._layout_label)
        self.form.addRow(load, clear)
        self.form.addRow("Difference", self._summary)
        self._show_bits = QCheckBox("Show bit differences")
        self.form.addRow(self._show_bits)
        self.form.addRow("Left bits", self.left_bits)
        self.form.addRow("Right bits", self.right_bits)
        for bit_view in (self.left_bits, self.right_bits):
            self.form.setRowVisible(bit_view, False)
        self._show_bits.toggled.connect(self.show_bits)
        self.form.addRow("Byte comparison page", self._page)
        self.form.addRow("Byte differences", self.byte_table)
        self.form.addRow("Field differences", self.field_table)
        self._source_side = LocalizedComboBox()
        self._source_side.addItems(["Left", "Right", "XOR"])
        self.form.addRow("Send comparison side", self._source_side)
        self.run_button.setText("Compare patterns")
        self.run_button.setEnabled(True)
        self.run_button.clicked.connect(self.start_calculation)
        self.result_ready.connect(self.show_difference)
        self.result_invalidated.connect(self.clear_difference)
        self.bind_inputs()

    def clear_difference(self) -> None:
        self.left_bits.clear()
        self.right_bits.clear()
        self._data = (b"", b"")
        self.byte_table.setRowCount(0)
        self.field_table.setRowCount(0)
        self._summary.clear()

    def show_bits(self, shown: bool) -> None:
        for editor in (self.left_bits, self.right_bits):
            self.form.setRowVisible(editor, shown)

    def show_difference(self, title: str, report: dict[str, object]) -> None:
        left, right = str(report["left_bits"]), str(report["right_bits"])
        positions = report["changed_bit_positions"]
        assert isinstance(positions, list)
        changed = set(positions)
        self._summary.setText(
            f"{report['changed_bits']} changed bits · {report['changed_bytes']} changed bytes"
        )
        if len(left) <= 4096:
            self.left_bits.set_pattern(int(left, 2), len(left), changed=changed)
            self.right_bits.set_pattern(int(right, 2), len(right), changed=changed)
        else:
            self._summary.setText(self._summary.text() + " · Large patterns: use byte/text views")
        self._data = (
            bytes.fromhex(str(report["left_bytes"])),
            bytes.fromhex(str(report["right_bytes"])),
        )
        self._page.setMaximum((len(self._data[0]) + 127) // 128)
        self.show_byte_page()
        fields = report["fields"]
        assert isinstance(fields, list)
        self.field_table.setRowCount(len(fields))
        for row, field in enumerate(fields):
            for column, key in enumerate(("name", "left", "right", "xor_bits", "changed")):
                item = QTableWidgetItem(str(field[key]))
                if key == "changed":
                    item.setData(UI_TEXT_ROLE, str(field[key]))
                self.field_table.setItem(row, column, item)
        self.field_table.resizeColumnsToContents()

    def show_byte_page(self) -> None:
        left, right = self._data
        start = (self._page.value() - 1) * 128
        self.byte_table.setRowCount(min(128, max(0, len(left) - start)))
        for row, index in enumerate(range(start, min(len(left), start + 128))):
            for column, text in enumerate(
                (
                    f"{index:08X}",
                    f"{left[index]:02X}",
                    f"{right[index]:02X}",
                    f"{left[index] ^ right[index]:02X}",
                )
            ):
                item = QTableWidgetItem(text)
                if left[index] != right[index] and column > 0:
                    item.setBackground(QColor("#a34e2a"))
                    item.setForeground(QColor("#ffffff"))
                self.byte_table.setItem(row, column, item)
        self.byte_table.resizeColumnsToContents()

    def load_layout(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("Load bitfield layout"), "", "JSON (*.json)")
        if not path:
            return
        try:
            if Path(path).stat().st_size > 1024 * 1024:
                raise ValueError("layout exceeds 1 MiB")
            text = Path(path).read_text(encoding="utf-8")
            layout = BitfieldLayout.from_json(text)
        except (ValueError, OSError) as error:
            self.set_error(str(error))
            return
        self.invalidate_result()
        self._layout = text
        self._layout_label.setText(f"{len(layout.fields)} fields · {layout.width} bits")
        self.translate_ui()

    def clear_layout(self) -> None:
        self.invalidate_result()
        self._layout = ""
        self._layout_label.setText("No bitfield layout")
        self.translate_ui()

    def snapshot(self) -> dict[str, object]:
        state = super().snapshot()
        state["layout"] = self._layout
        return state

    def request_transfer(self) -> None:
        if self._report is None:
            return
        side = self._source_side.currentText().lower()
        data = bytes.fromhex(str(self._report[f"{side}_bytes"]))
        order = "little" if self._report["byteorder"] == "little" else "big"
        pattern = int.from_bytes(data, "little" if order == "little" else "big")
        self.transfer_requested.emit(
            self._destination.currentText(), self._transfer_mode.currentIndex() == 1,
            {"bits": format(pattern, f"0{len(data) * 8}b"), "bytes": data.hex(" "),
             "width": len(data) * 8, "byteorder": order, "exact": str(ExactValue(pattern)),
             "signed": False, "data_type": "integer"},
        )

    def restore_state(self, state: dict[str, object]) -> None:
        super().restore_state(state)
        self._layout = ""
        self._layout_label.setText("No bitfield layout")
        self.translate_ui()
        text = state.get("layout", "")
        if isinstance(text, str) and text:
            try:
                layout = BitfieldLayout.from_json(text)
            except ValueError:
                return
            self._layout = text
            self._layout_label.setText(f"{len(layout.fields)} fields · {layout.width} bits")
            self.translate_ui()
