from PySide6.QtWidgets import QCheckBox, QComboBox, QLineEdit, QSpinBox

from radixscope.gui.bits import BitEditor
from radixscope.gui.conversion import base_input
from radixscope.gui.widgets import Workspace


class InspectorWorkspace(Workspace):
    def __init__(self) -> None:
        super().__init__(
            "Number Inspector", "One value, synchronized numeric, signed, bit and byte views"
        )
        self.input = QLineEdit("255")
        self.base = base_input()
        self.data_type = QComboBox()
        self.data_type.addItems(["integer", "binary32", "binary64"])
        self.bit_width = QSpinBox()
        self.bit_width.setRange(1, 4096)
        self.bit_width.setValue(32)
        self.signed = QCheckBox("Signed two's complement")
        self.pattern = QCheckBox("Reinterpret raw bits instead of converting a value")
        self.byteorder = QComboBox()
        self.byteorder.addItems(["big", "little"])
        self.form.addRow("Input", self.input)
        self.form.addRow("Input base", self.base)
        self.form.addRow("Data type", self.data_type)
        self.form.addRow("Bit width", self.bit_width)
        self.form.addRow("Integer interpretation", self.signed)
        self.form.addRow("Input meaning", self.pattern)
        self.form.addRow("Byte order", self.byteorder)
        self.bit_editor = BitEditor()
        self.bit_editor.setToolTip("Raw result bits; numeric conversion uses the input above")
        self.form.addRow("Bit pattern", self.bit_editor)
        self.result_ready.connect(self.show_bits)
        self.result_invalidated.connect(self.bit_editor.clear)
        self.data_type.currentIndexChanged.connect(self.update_controls)
        self.run_button.setText("Inspect number")
        self.run_button.setEnabled(True)
        self.run_button.clicked.connect(self.start_calculation)
        self.input.returnPressed.connect(self.start_calculation)
        self.update_controls()
        self.bind_inputs()

    def update_controls(self) -> None:
        integer = self.data_type.currentText() == "integer"
        self.bit_width.setEnabled(integer)
        self.signed.setEnabled(integer)
        if not integer:
            self.bit_width.setValue(int(self.data_type.currentText().removeprefix("binary")))

    def show_bits(self, title: str, report: dict[str, object]) -> None:
        bits = report.get("bits")
        if isinstance(bits, str):
            self.bit_editor.set_pattern(int(bits, 2), len(bits))
            self.bit_editor.setEnabled(False)

    def restore_state(self, state: dict[str, object]) -> None:
        super().restore_state(state)
        self.update_controls()
