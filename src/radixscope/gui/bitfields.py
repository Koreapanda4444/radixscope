from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QGridLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from radixscope.core.bitfields import BitField, BitfieldLayout, inspect_bitfields
from radixscope.core.value import ExactValue
from radixscope.gui.bits import BitEditor


class BitfieldPanel(QWidget):
    pattern_requested = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._pattern: int | None = None
        self._width = 0
        self._initialized = False
        self.fields = QTableWidget(0, 4)
        self.fields.setHorizontalHeaderLabels(["Field", "Offset (LSB0)", "Width", "Signed"])
        self.fields.setMaximumHeight(150)
        self.values = QTableWidget(0, 4)
        self.values.setHorizontalHeaderLabels(["Field", "Value", "Raw Hex", "Bits"])
        self.values.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.values.setMaximumHeight(140)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setObjectName("error")
        self.bits = BitEditor()
        self.bits.pattern_changed.connect(self.pattern_requested.emit)
        add = QPushButton("Add field")
        remove = QPushButton("Remove field")
        analyze = QPushButton("Apply fields")
        save = QPushButton("Save layout")
        load = QPushButton("Load layout")
        add.clicked.connect(lambda: self.add_field())
        remove.clicked.connect(self.remove_field)
        analyze.clicked.connect(self.analyze)
        save.clicked.connect(self.save_layout)
        load.clicked.connect(self.load_layout)
        actions = QGridLayout()
        for index, button in enumerate((add, remove, analyze, save, load)):
            actions.addWidget(button, index // 3, index % 3)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        description = QLabel(
            "Offsets count from the least significant bit after byte-order decoding"
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        layout.addWidget(self.fields)
        layout.addLayout(actions)
        layout.addWidget(self.error)
        layout.addWidget(self.values)
        layout.addWidget(self.bits)

    def add_field(self, field: BitField | None = None) -> None:
        if self.fields.rowCount() >= 256:
            self.error.setText("A layout supports at most 256 fields")
            return
        row = self.fields.rowCount()
        field = field or BitField(f"field_{row + 1}", row * 8, 8)
        self.fields.insertRow(row)
        for column, text in enumerate((field.name, str(field.offset), str(field.width))):
            self.fields.setItem(row, column, QTableWidgetItem(text))
        signed = QTableWidgetItem()
        signed.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        signed.setCheckState(Qt.CheckState.Checked if field.signed else Qt.CheckState.Unchecked)
        self.fields.setItem(row, 3, signed)

    def remove_field(self) -> None:
        row = self.fields.currentRow()
        if row >= 0:
            self.fields.removeRow(row)
            self.analyze()

    def field_definitions(self) -> tuple[BitField, ...]:
        result = []
        for row in range(self.fields.rowCount()):
            cells = [self.fields.item(row, column) for column in range(4)]
            if any(cell is None for cell in cells):
                raise ValueError("all field properties are required")
            name, offset, width, signed = cells
            assert (
                name is not None and offset is not None and width is not None and signed is not None
            )
            result.append(
                BitField(
                    name.text(),
                    int(offset.text()),
                    int(width.text()),
                    signed.checkState() == Qt.CheckState.Checked,
                )
            )
        return tuple(result)

    def set_pattern(self, pattern: int, width: int) -> None:
        self._pattern, self._width = pattern, width
        if width > 4096:
            self.error.setText("Select at most 512 bytes for interactive bitfield editing")
            self.values.setRowCount(0)
            self.bits.clear()
            return
        if not self._initialized:
            self.add_field(BitField("low", 0, min(width, 8)))
            if width > 8:
                self.add_field(BitField("high", 8, width - 8))
            self._initialized = True
        self.analyze()

    def clear(self) -> None:
        self._pattern = None
        self.values.setRowCount(0)
        self.bits.clear()

    def analyze(self) -> None:
        if self._pattern is None or not 1 <= self._width <= 4096:
            return
        try:
            fields = self.field_definitions()
            values = inspect_bitfields(self._pattern, self._width, fields)
        except (ValueError, TypeError) as error:
            self.error.setText(str(error))
            self.values.setRowCount(0)
            self.bits.clear()
            return
        self.error.clear()
        self.values.setRowCount(len(values))
        for row, value in enumerate(values):
            for column, text in enumerate(
                (
                    value.field.name,
                    str(ExactValue(value.integer.value)),
                    format(value.integer.bit_pattern, "X"),
                    value.integer.bits,
                )
            ):
                self.values.setItem(row, column, QTableWidgetItem(text))
        self.values.resizeColumnsToContents()
        self.bits.set_pattern(
            self._pattern,
            self._width,
            {field.name: (field.offset, field.offset + field.width - 1) for field in fields},
        )

    def save_layout(self) -> None:
        try:
            layout = BitfieldLayout(self._width, self.field_definitions())
            path, _ = QFileDialog.getSaveFileName(self, "Save bitfield layout", "", "JSON (*.json)")
            if path:
                Path(path).write_text(layout.to_json(), encoding="utf-8")
        except (ValueError, OSError) as error:
            self.error.setText(str(error))

    def load_layout(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load bitfield layout", "", "JSON (*.json)")
        if not path:
            return
        try:
            if Path(path).stat().st_size > 1024 * 1024:
                raise ValueError("layout exceeds 1 MiB")
            layout = BitfieldLayout.from_json(Path(path).read_text(encoding="utf-8"))
            if layout.width != self._width:
                raise ValueError(f"layout requires a {layout.width}-bit selection")
        except (ValueError, OSError) as error:
            self.error.setText(str(error))
            return
        self.fields.setRowCount(0)
        for field in layout.fields:
            self.add_field(field)
        self._initialized = True
        self.analyze()

    def snapshot(self) -> list[dict[str, object]]:
        return [
            {
                "name": self.cell(row, 0).text(),
                "offset": self.cell(row, 1).text(),
                "width": self.cell(row, 2).text(),
                "signed": self.cell(row, 3).checkState() == Qt.CheckState.Checked,
            }
            for row in range(self.fields.rowCount())
        ]

    def restore_state(self, state: object) -> None:
        if not isinstance(state, list) or len(state) > 256:
            return
        self.fields.setRowCount(0)
        for entry in state:
            if not isinstance(entry, dict):
                continue
            self.add_field()
            row = self.fields.rowCount() - 1
            for column, key in enumerate(("name", "offset", "width")):
                self.cell(row, column).setText(str(entry.get(key, "")))
            self.cell(row, 3).setCheckState(
                Qt.CheckState.Checked if entry.get("signed") is True else Qt.CheckState.Unchecked
            )
        self._initialized = True

    def cell(self, row: int, column: int) -> QTableWidgetItem:
        item = self.fields.item(row, column)
        if item is None:
            item = QTableWidgetItem()
            self.fields.setItem(row, column, item)
        return item
