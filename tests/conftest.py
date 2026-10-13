import os
import time

import pytest
from PySide6.QtWidgets import QApplication

from radixscope.gui.app import create_application
from radixscope.gui.widgets import Workspace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qt_app() -> QApplication:
    return create_application()


def wait_for_workspace(workspace: Workspace, application: QApplication) -> None:
    deadline = time.monotonic() + 20
    while workspace.job is not None and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.005)
    assert workspace.job is None, "desktop calculation did not finish"
