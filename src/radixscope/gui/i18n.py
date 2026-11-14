"""Translate desktop presentation without changing numeric data or control values."""

import json
import re
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QLocale, QObject, QSignalBlocker, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractButton,
    QComboBox,
    QDockWidget,
    QLabel,
    QLineEdit,
    QTabBar,
    QTableWidget,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

ORIGINAL_ROLE = int(Qt.ItemDataRole.UserRole) + 201
UI_TEXT_ROLE = ORIGINAL_ROLE + 1
UI_CONTEXT_ROLE = ORIGINAL_ROLE + 2
_language = "en"
_KO: dict[str, str] = json.loads(
    (Path(__file__).resolve().parents[1] / "assets" / "ko.json").read_text(encoding="utf-8")
)
_REVERSE: dict[str, str] = {}
for _source, _translated in _KO.items():
    _REVERSE.setdefault(_translated, _source)

_PATTERNS = [
    (r"base must be between (\d+) and (\d+)", r"진법은 \1~\2여야 합니다"),
    (r"digit (.+) is invalid in base (\d+)", r"\2진법에서 잘못된 숫자: \1"),
    (r"unsupported digit: (.+)", r"지원하지 않는 숫자: \1"),
    (r"unexpected character (.+) at position (\d+)", r"위치 \2의 예상하지 못한 문자: \1"),
    (r"unexpected token (.+) at position (\d+)", r"위치 \2의 예상하지 못한 토큰: \1"),
    (r"expected a literal or parenthesis at position (\d+)", r"위치 \1에 숫자나 괄호가 필요합니다"),
    (r"missing closing parenthesis at position (\d+)", r"위치 \1의 닫는 괄호가 없습니다"),
    (r"missing scientific exponent at position (\d+)", r"위치 \1에 지수가 필요합니다"),
    (r"missing fractional digits at position (\d+)", r"위치 \1에 소수부 숫자가 필요합니다"),
    (r"invalid recurring group in literal at position (\d+)", r"위치 \1의 순환 구간 오류"),
    (r"division by zero at position (\d+)", r"위치 \1에서 0으로 나눌 수 없습니다"),
    (r"exponent must be an integer at position (\d+)", r"위치 \1의 지수는 정수여야 합니다"),
    (r"zero cannot have a negative exponent at position (\d+)",
     r"위치 \1의 0의 음수 거듭제곱 오류"),
    (r"bitwise operators require integers at position (\d+)",
     r"위치 \1의 비트 연산에는 정수가 필요합니다"),
    (r"bitwise operators and shifts require integers at position (\d+)",
     r"위치 \1의 비트 연산에는 정수가 필요합니다"),
    (r"shift count cannot be negative at position (\d+)", r"위치 \1의 시프트 횟수는 0 이상입니다"),
    (r"(power|shift|operation) exceeds the computation budget at position (\d+)",
     r"위치 \2의 연산이 계산 한도를 넘습니다"),
    (r"input exceeds (\d+) characters", r"입력이 \1자 한도를 넘습니다"),
    (r"precision exceeds (\d+) digits", r"정밀도가 \1자리 한도를 넘습니다"),
    (r"width exceeds the (\d+)-bit computation budget", r"비트 폭이 \1비트 한도를 넘습니다"),
    (r"(.+) is outside the (\d+)-bit (signed|unsigned) range (.+) through (.+)",
     r"\1은 \2비트 범위(\4~\5)를 벗어납니다"),
    (r"bit pattern must be between (.+) and (.+) for width (\d+)",
     r"\3비트 패턴은 \1~\2 범위여야 합니다"),
    (r"hex bytes require pairs of digits at position (\d+)", r"위치 \1의 Hex는 두 자리 단위입니다"),
    (r"invalid hex byte at position (\d+)", r"위치 \1의 Hex 바이트 오류"),
    (r"selection length does not match (.+)", r"선택 길이가 \1 형식과 맞지 않습니다"),
    (r"duplicate field name: (.+)", r"중복된 필드 이름: \1"),
    (r"field overlaps another field: (.+)", r"다른 필드와 겹칩니다: \1"),
    (r"field exceeds the (\d+)-bit selection: (.+)", r"\1비트 선택 범위를 벗어납니다: \2"),
    (r"layout requires a (\d+)-bit selection", r"레이아웃에 \1비트 선택 범위가 필요합니다"),
    (r"invalid literal for int\(\) with base 10: (.+)", r"10진수 정수가 아닙니다: \1"),
    (r"Bits (\d+) … (\d+) · MSB → LSB", r"비트 \1 … \2 · MSB → LSB"),
    (r"Offset (\d+) \((.+)\)", r"오프셋 \1 (\2)"),
    (r"(\d+) fields · (\d+) bits", r"필드 \1개 · \2비트"),
    (r"(\d+) changed bits · (\d+) changed bytes", r"변경 비트 \1개 · 변경 바이트 \2개"),
    (r"(\d+) / (\d+) rows · (\d+) errors", r"\2행 중 \1행 처리 · 오류 \3개"),
    (r"(\d+)/(\d+) rows · (\d+) errors", r"\2행 중 \1행 처리 · 오류 \3개"),
    (r"(\d+) bits · (\d+) bytes changed", r"변경 비트 \1개 · 변경 바이트 \2개"),
    (r"(\d+) items · Text report / Copy selected", r"항목 \1개 · 텍스트 보고서 또는 선택 복사"),
]


def default_language() -> str:
    return "ko" if QLocale.system().language() == QLocale.Language.Korean else "en"


def set_language(language: object) -> None:
    global _language
    _language = "ko" if language == "ko" else "en"


def _canonical(text: str) -> str:
    return text if text in _KO else _REVERSE.get(text, text)


def tr(text: str) -> str:
    if _language != "ko":
        return text
    if text in _KO:
        return _KO[text]
    plain = text.replace("&", "")
    if plain in _KO:
        return _KO[plain]
    for suffix, translated in (
        (" · Limit reached; some inputs were not processed", " · 한도 도달: 일부 입력 미처리"),
        (" · Large patterns: use byte/text views", " · 큰 패턴은 바이트·텍스트 뷰를 사용하세요"),
    ):
        if text.endswith(suffix):
            return tr(text[:-len(suffix)]) + translated
    match = re.fullmatch(r"invalid literal (.+) at position (\d+): (.+)", text)
    if match:
        return f"위치 {match[2]}의 리터럴 {match[1]} 오류: {tr(match[3])}"
    for prefix, translated in (
        ("Could not start calculation: ", "계산을 시작할 수 없습니다: "),
        ("Could not read calculation result: ", "계산 결과를 읽을 수 없습니다: "),
        ("Could not save preferences: ", "설정을 저장할 수 없습니다: "),
        ("Could not load preferences: ", "설정을 불러올 수 없습니다: "),
        ("Could not export result: ", "결과를 내보낼 수 없습니다: "),
        ("Could not export history: ", "기록을 내보낼 수 없습니다: "),
    ):
        if text.startswith(prefix):
            return translated + tr(text[len(prefix):])
    for name in (
        "Number Inspector", "Programmer", "Conversion", "Trace",
        "IEEE 754", "Batch Conversion",
    ):
        for suffix, translated in (
            (" complete", " 완료"), (" result", " 결과"), (" output items", " 출력 항목"),
        ):
            if text == name + suffix:
                return tr(name) + translated
        if text.startswith(name + " · Ctrl+"):
            return tr(name) + text[len(name):]
    if text.startswith("Ready · Ctrl+1 through Ctrl+8"):
        return "준비 · Ctrl+1~Ctrl+8 화면 이동 · Ctrl+H 기록"
    match = re.fullmatch(r"(Number|Scientific) input · detected base (\d+)", text)
    if match:
        return f"{tr(match[1].lower())} 입력 · 인식 진법 {match[2]}"
    if text == "Hexadecimal digits · Auto uses base 16":
        return "16진수 숫자 · 자동 모드에서는 16진법으로 해석합니다"
    if text == "Exact expression · Auto evaluates operators":
        return "정확한 수식 · 자동 모드에서는 연산자를 계산합니다"
    match = re.fullmatch(r"Sign: (.+) · Exponent: (.+) · Fraction: (.+)", text)
    if match:
        return f"부호: {match[1]} · 지수: {match[2]} · 가수부: {match[3]}"
    match = re.fullmatch(r"Bit (\d+) · (.+?)( · click or press Space to toggle)?", text)
    if match:
        suffix = " · 클릭하거나 Space로 전환" if match[3] else ""
        return f"비트 {match[1]} · {tr(match[2])}{suffix}"
    for pattern, replacement in _PATTERNS:
        if re.fullmatch(pattern, text):
            return re.sub(pattern, replacement, text)
    return text


def tr_field(path: str) -> str:
    if _language != "ko":
        return path.replace("_", " ")
    if re.fullmatch(r"outputs\.\d+", path):
        return path.split(".")[1] + "진수"
    if re.fullmatch(r"base_\d+", path):
        return path.split("_")[1] + "진수"
    return " · ".join(tr(part.replace("_", " ")) for part in path.split("."))


class LocalizedComboBox(QComboBox):
    def currentText(self) -> str:
        source = self.itemData(self.currentIndex(), ORIGINAL_ROLE)
        return source if isinstance(source, str) else super().currentText()

    def findText(
        self, text: str,
        flags: Qt.MatchFlag = Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchCaseSensitive,
    ) -> int:
        for index in range(self.count()):
            if self.itemData(index, ORIGINAL_ROLE) == text:
                return index
        return super().findText(text, flags)

    def setCurrentText(self, text: str) -> None:
        index = self.findText(text)
        if index >= 0:
            self.setCurrentIndex(index)
        else:
            super().setCurrentText(text)


def _text_property(
    obj: QObject, name: str, getter: Callable[[], str], setter: Callable[[str], None],
) -> None:
    current = getter()
    source = obj.property("rs_source_" + name)
    if not isinstance(source, str) or current != obj.property("rs_last_" + name):
        source = _canonical(current)
    translated = tr(source)
    obj.setProperty("rs_source_" + name, source)
    obj.setProperty("rs_last_" + name, translated)
    if current != translated:
        setter(translated)


def localize(root: QObject) -> None:
    for obj in (root, *root.findChildren(QObject)):
        if isinstance(obj, QComboBox):
            blocker = QSignalBlocker(obj)
            for index in range(obj.count()):
                source = obj.itemData(index, ORIGINAL_ROLE)
                if not isinstance(source, str):
                    source = _canonical(obj.itemText(index))
                    obj.setItemData(index, source, ORIGINAL_ROLE)
                obj.setItemText(index, tr(source))
            del blocker
        elif isinstance(obj, (QLabel, QAbstractButton, QAction)):
            _text_property(obj, "text", obj.text, obj.setText)
        if isinstance(obj, QWidget):
            _text_property(obj, "tooltip", obj.toolTip, obj.setToolTip)
            _text_property(obj, "accessible", obj.accessibleName, obj.setAccessibleName)
        if isinstance(obj, QLineEdit):
            _text_property(obj, "placeholder", obj.placeholderText, obj.setPlaceholderText)
        if isinstance(obj, QDockWidget) or (isinstance(obj, QWidget) and obj.isWindow()):
            _text_property(obj, "title", obj.windowTitle, obj.setWindowTitle)
        if isinstance(obj, QTabWidget):
            for index in range(obj.count()):
                source = obj.tabBar().tabData(index)
                if not isinstance(source, str):
                    source = _canonical(obj.tabText(index))
                    obj.tabBar().setTabData(index, source)
                obj.setTabText(index, tr(source))
        if isinstance(obj, QTabBar):
            for index in range(obj.count()):
                source = obj.tabData(index)
                if not isinstance(source, str):
                    source = _canonical(obj.tabText(index))
                    obj.setTabData(index, source)
                obj.setTabText(index, tr(source))
        if isinstance(obj, QTreeWidget):
            for index in range(obj.topLevelItemCount()):
                _tree_item(obj.topLevelItem(index))
        if isinstance(obj, QTableWidget):
            for column in range(obj.columnCount()):
                item = obj.horizontalHeaderItem(column)
                if item is not None:
                    source = item.data(ORIGINAL_ROLE)
                    if not isinstance(source, str) or item.text() != item.data(UI_TEXT_ROLE):
                        source = _canonical(item.text())
                        item.setData(ORIGINAL_ROLE, source)
                    translated = tr_field(source)
                    item.setData(UI_TEXT_ROLE, translated)
                    item.setText(translated)
            for row in range(obj.rowCount()):
                for column in range(obj.columnCount()):
                    item = obj.item(row, column)
                    if item is not None:
                        source = item.data(UI_TEXT_ROLE)
                        if isinstance(source, str):
                            item.setText(
                                tr_field(source) if item.data(UI_CONTEXT_ROLE) == "field"
                                else tr(source)
                            )


def _tree_item(item: QTreeWidgetItem | None) -> None:
    if item is None:
        return
    source = item.data(0, ORIGINAL_ROLE)
    if not isinstance(source, str):
        source = _canonical(item.text(0))
        item.setData(0, ORIGINAL_ROLE, source)
    item.setText(0, tr(source))
    tooltip = item.data(0, UI_TEXT_ROLE)
    if not isinstance(tooltip, str):
        tooltip = item.toolTip(0)
        item.setData(0, UI_TEXT_ROLE, tooltip)
    item.setToolTip(0, tr(tooltip))
    for index in range(item.childCount()):
        _tree_item(item.child(index))


def gui_report(report: dict[str, object], english_text: str | None = None) -> str:
    from radixscope.reports import StructuredReport, render_report

    if _language == "en":
        return english_text if english_text is not None else render_report(report)
    lines = []
    for field in StructuredReport(report).fields:
        value = tr(field.text) if isinstance(field.value, bool) else field.text
        lines.append(f"{tr_field(field.path)}: {value}")
    return "\n".join(lines)
