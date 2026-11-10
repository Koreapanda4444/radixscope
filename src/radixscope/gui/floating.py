from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from radixscope.core.ieee754 import IEEE754Value
from radixscope.core.neighbors import adjacent_float, float_boundaries


class FloatNavigator(QWidget):
    pattern_requested = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.value: IEEE754Value | None = None
        self.previous = QPushButton("Previous value")
        self.next = QPushButton("Next value")
        self.previous.clicked.connect(lambda: self.move_to_neighbor("down"))
        self.next.clicked.connect(lambda: self.move_to_neighbor("up"))
        self.boundary = QComboBox()
        for name in ("positive_zero", "minimum_subnormal", "maximum_subnormal", "minimum_normal",
                     "maximum_finite", "positive_infinity"):
            self.boundary.addItem(name.replace("_", " ").capitalize(), name)
        self.jump = QPushButton("Go to boundary")
        self.jump.clicked.connect(self.jump_to_boundary)
        row = QHBoxLayout()
        row.addWidget(self.previous)
        row.addWidget(self.next)
        row.addStretch()
        boundaries = QHBoxLayout()
        boundaries.addWidget(self.boundary)
        boundaries.addWidget(self.jump)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)
        layout.addLayout(boundaries)
        self.clear()

    def set_value(self, value: IEEE754Value) -> None:
        self.value = value
        self.setEnabled(True)
        self.previous.setEnabled(adjacent_float(value, "down") is not None)
        self.next.setEnabled(adjacent_float(value, "up") is not None)

    def clear(self) -> None:
        self.value = None
        self.setEnabled(False)

    def move_to_neighbor(self, direction: str) -> None:
        if self.value is not None:
            target = adjacent_float(self.value, direction)
            if target is not None:
                self.pattern_requested.emit(target.pattern)

    def jump_to_boundary(self) -> None:
        if self.value is not None:
            target = float_boundaries(self.value.format)[str(self.boundary.currentData())]
            self.pattern_requested.emit(target.pattern)
