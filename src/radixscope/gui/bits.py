from functools import partial

from PySide6.QtCore import Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from radixscope.gui.i18n import LocalizedComboBox, localize, tr


class BitEditor(QWidget):
    pattern_changed = Signal(object)
    page_size = 32

    def __init__(self) -> None:
        super().__init__()
        self.pattern: int | None = None
        self.bit_count = 0
        self.fields: dict[str, tuple[int, int]] = {}
        self.buttons: dict[int, QToolButton] = {}
        self.columns = 16
        self.group_labels: dict[QLabel, tuple[int, int]] = {}
        self.read_only = False
        self.changed: set[int] = set()
        self.page = QSpinBox()
        self.page.setMinimum(1)
        self.page.valueChanged.connect(self.rebuild)
        self.page.setAccessibleName("Bit editor page")
        self.range_label = QLabel("Run a calculation to edit its result bits")
        self.grid = QGridLayout()
        self.grid.setSpacing(3)
        navigation = QHBoxLayout()
        self._grouping = LocalizedComboBox()
        self._grouping.addItems(["4 bits", "8 bits"])
        self._grouping.setAccessibleName("Bit grouping")
        self._grouping.currentIndexChanged.connect(self.rebuild)
        self._grouped = QLineEdit()
        self._grouped.setReadOnly(True)
        self._grouped.setAccessibleName("Grouped result bits")
        self._grouped.setPlaceholderText("Grouped result bits")
        navigation.addWidget(self.range_label, 1)
        navigation.addWidget(self._grouping)
        navigation.addWidget(QLabel("Page"))
        navigation.addWidget(self.page)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(navigation)
        layout.addWidget(self._grouped)
        layout.addLayout(self.grid)
        self.setStyleSheet(
            'QToolButton { padding: 2px; border: 1px solid #8793a3; border-radius: 3px; }'
            'QToolButton:checked { font-weight: bold; border: 2px solid #3676c8; }'
            'QToolButton[field="sign"] { color: #aa4b00; border-bottom: 3px solid #aa4b00; }'
            'QToolButton[field="exponent"] { color: #287bc1; }'
            'QToolButton[field="fraction"] { color: #9165c9; }'
        )
        self.clear()

    def set_pattern(
        self, pattern: int, width: int, fields: dict[str, tuple[int, int]] | None = None,
        *, changed: set[int] | None = None,
    ) -> None:
        if not 1 <= width <= 4096 or not 0 <= pattern < (1 << width):
            raise ValueError("bit editor pattern does not fit its width")
        changed_layout = (self.bit_count != width or self.fields != (fields or {})
                          or self.changed != (changed or set()))
        self.pattern = pattern
        self.bit_count = width
        self.fields = fields or {}
        self.changed = changed or set()
        self.setEnabled(True)
        self.page.setMaximum((width + self.page_size - 1) // self.page_size)
        if changed_layout or not self.buttons:
            self.rebuild()
        else:
            self.refresh_buttons()

    def clear(self) -> None:
        self.pattern = None
        self._grouped.clear()
        for button in self.buttons.values():
            button.setText("·")
            button.setChecked(False)
        for label in self.group_labels:
            label.setText("—")
        self.setEnabled(False)
        self.range_label.setText("Run a calculation to edit its result bits")
        localize(self)

    def field_name(self, index: int) -> str:
        for name, (low, high) in self.fields.items():
            if low <= index <= high:
                return name
        return "value"

    def rebuild(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
        self.buttons.clear()
        self.group_labels.clear()
        if self.pattern is None:
            return
        high = self.bit_count - 1 - (self.page.value() - 1) * self.page_size
        low = max(0, high - self.page_size + 1)
        self.range_label.setText(f"Bits {high} … {low} · MSB → LSB")
        for offset, index in enumerate(range(high, low - 1, -1)):
            row, ordinal = divmod(offset, self.columns)
            # Add a gap at each numeric group boundary, even for a partial leading group.
            row_high = high - row * self.columns
            gap_count = row_high // self.group_width - index // self.group_width
            column = ordinal + gap_count
            label = QLabel(str(index))
            button = QToolButton()
            button.setCheckable(True)
            button.setMinimumSize(24, 24)
            field = self.field_name(index)
            if index in self.changed:
                button.setStyleSheet("background-color: #a34e2a; color: #ffffff;")
            button.setProperty("field", field)
            button.setAccessibleName(f"Bit {index} · {field}")
            button.setToolTip(f"Bit {index} · {field}" if self.read_only else (
                f"Bit {index} · {field} · click or press Space to toggle"
            ))
            button.clicked.connect(partial(self.toggle_bit, index))
            self.grid.addWidget(label, row * 3 + 1, column)
            self.grid.addWidget(button, row * 3 + 2, column)
            self.buttons[index] = button
        for row_start in range(high, low - 1, -self.columns):
            row_end = max(low, row_start - self.columns + 1)
            row = (high - row_start) // self.columns
            group_high = row_start
            while group_high >= row_end:
                group_low = max(row_end, (group_high // self.group_width) * self.group_width)
                start_column = (row_start - group_high
                                + row_start // self.group_width - group_high // self.group_width)
                group_label = QLabel()
                self.group_labels[group_label] = (group_low, group_high)
                group_label.setToolTip(
                    tr("Hex digit" if self.group_width == 4 else "Numeric byte")
                    + f" {group_high // self.group_width} · {group_high}…{group_low}"
                )
                self.grid.addWidget(group_label, row * 3, start_column, 1,
                                    group_high - group_low + 1)
                group_high = group_low - 1
        self.refresh_buttons()

    @property
    def group_width(self) -> int:
        return 8 if self._grouping.currentIndex() == 1 else 4

    def set_group_width(self, width: int) -> None:
        self._grouping.setCurrentIndex(1 if width == 8 else 0)

    def resizeEvent(self, event: QResizeEvent) -> None:
        columns = 8 if event.size().width() < 450 else 16
        if columns != self.columns:
            self.columns = columns
            self.rebuild()
        super().resizeEvent(event)

    def refresh_buttons(self) -> None:
        if self.pattern is None:
            return
        high = self.bit_count - 1 - (self.page.value() - 1) * self.page_size
        low = max(0, high - self.page_size + 1)
        self.range_label.setText(f"Bits {high} … {low} · MSB → LSB")
        bits = format(self.pattern, f"0{self.bit_count}b")
        first = len(bits) % self.group_width or self.group_width
        groups = [bits[:first], *[bits[i:i + self.group_width]
                                  for i in range(first, len(bits), self.group_width)]]
        self._grouped.setText(" ".join(groups))
        for label, (low_bit, high_bit) in self.group_labels.items():
            value = (self.pattern >> low_bit) & ((1 << (high_bit - low_bit + 1)) - 1)
            label.setText(format(value, "X" if self.group_width == 4 else "02X"))
        for index, button in self.buttons.items():
            bit = bool(self.pattern & (1 << index))
            button.setChecked(bit)
            button.setText("1" if bit else "0")
        localize(self)

    def toggle_bit(self, index: int) -> None:
        if self.read_only:
            return
        if self.pattern is None or not self.isEnabled() or not 0 <= index < self.bit_count:
            return
        self.pattern ^= 1 << index
        self.refresh_buttons()
        self.pattern_changed.emit(self.pattern)
