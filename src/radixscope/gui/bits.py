from functools import partial

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class BitEditor(QWidget):
    pattern_changed = Signal(object)
    page_size = 64

    def __init__(self) -> None:
        super().__init__()
        self.pattern: int | None = None
        self.bit_count = 0
        self.fields: dict[str, tuple[int, int]] = {}
        self.buttons: dict[int, QToolButton] = {}
        self.page = QSpinBox()
        self.page.setMinimum(1)
        self.page.valueChanged.connect(self.rebuild)
        self.page.setAccessibleName("Bit editor page")
        self.range_label = QLabel("Run a calculation to edit its result bits")
        self.grid = QGridLayout()
        self.grid.setSpacing(3)
        navigation = QHBoxLayout()
        navigation.addWidget(self.range_label, 1)
        navigation.addWidget(QLabel("Page"))
        navigation.addWidget(self.page)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(navigation)
        layout.addLayout(self.grid)
        self.setStyleSheet(
            'QToolButton { padding: 2px; border: 1px solid #8793a3; border-radius: 3px; }'
            'QToolButton:checked { font-weight: bold; border: 2px solid #3676c8; }'
            'QToolButton[field="sign"] { color: #aa4b00; }'
            'QToolButton[field="exponent"] { color: #287bc1; }'
            'QToolButton[field="fraction"] { color: #9165c9; }'
        )
        self.clear()

    def set_pattern(
        self, pattern: int, width: int, fields: dict[str, tuple[int, int]] | None = None,
    ) -> None:
        if not 1 <= width <= 4096 or not 0 <= pattern < (1 << width):
            raise ValueError("bit editor pattern does not fit its width")
        changed_layout = self.bit_count != width or self.fields != (fields or {})
        self.pattern = pattern
        self.bit_count = width
        self.fields = fields or {}
        self.setEnabled(True)
        self.page.setMaximum((width + self.page_size - 1) // self.page_size)
        if changed_layout or not self.buttons:
            self.rebuild()
        else:
            self.refresh_buttons()

    def clear(self) -> None:
        self.pattern = None
        self.setEnabled(False)
        self.range_label.setText("Run a calculation to edit its result bits")

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
        if self.pattern is None:
            return
        high = self.bit_count - 1 - (self.page.value() - 1) * self.page_size
        low = max(0, high - self.page_size + 1)
        self.range_label.setText(f"Bits {high} … {low} · MSB → LSB")
        for offset, index in enumerate(range(high, low - 1, -1)):
            row, column = divmod(offset, 16)
            label = QLabel(str(index))
            button = QToolButton()
            button.setCheckable(True)
            button.setMinimumSize(24, 24)
            field = self.field_name(index)
            button.setProperty("field", field)
            button.setAccessibleName(f"Bit {index} · {field}")
            button.setToolTip(f"Bit {index} · {field} · click or press Space to toggle")
            button.clicked.connect(partial(self.toggle_bit, index))
            self.grid.addWidget(label, row * 2, column)
            self.grid.addWidget(button, row * 2 + 1, column)
            self.buttons[index] = button
        self.refresh_buttons()

    def refresh_buttons(self) -> None:
        if self.pattern is None:
            return
        high = self.bit_count - 1 - (self.page.value() - 1) * self.page_size
        low = max(0, high - self.page_size + 1)
        self.range_label.setText(f"Bits {high} … {low} · MSB → LSB")
        for index, button in self.buttons.items():
            bit = bool(self.pattern & (1 << index))
            button.setChecked(bit)
            button.setText("1" if bit else "0")

    def toggle_bit(self, index: int) -> None:
        if self.pattern is None or not self.isEnabled() or not 0 <= index < self.bit_count:
            return
        self.pattern ^= 1 << index
        self.refresh_buttons()
        self.pattern_changed.emit(self.pattern)
