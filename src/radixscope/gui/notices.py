import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTextBrowser, QVBoxLayout, QWidget

from radixscope.gui.i18n import localize


def show_notices(parent: QWidget) -> None:
    dialog = QDialog(parent)
    dialog.setWindowTitle("Open-source notices")
    dialog.resize(720, 520)
    viewer = QTextBrowser()
    viewer.setOpenExternalLinks(True)
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3] / "_internal"))
    notice = root / "licenses/NOTICE.html"
    if notice.is_file():
        viewer.setSource(QUrl.fromLocalFile(str(notice)))
    else:
        viewer.setHtml('<h2>Python · Qt · PySide6 · shiboken</h2><p>Runtime notices are generated '
                       'by build_windows.bat in _internal/licenses.</p><p><a href="'
                       'https://doc.qt.io/qtforpython-6/licenses.html">Qt for Python licenses</a>'
                       '</p><p><a href="https://docs.python.org/3/license.html">'
                       'Python licenses</a></p>')
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dialog.reject)
    layout = QVBoxLayout(dialog)
    layout.addWidget(viewer)
    layout.addWidget(buttons)
    localize(dialog)
    dialog.exec()
