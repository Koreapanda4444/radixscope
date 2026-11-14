"""One vector source family for desktop icons and Windows executable resources."""

from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)
ICON_SOURCE = Path(__file__).resolve().parents[1] / "assets" / "radixscope.svg"


def icon_image(size: int, source: Path = ICON_SOURCE) -> QImage:
    if size not in ICON_SIZES:
        raise ValueError("unsupported application icon size")
    small = source.with_name(source.stem + "-small.svg")
    renderer = QSvgRenderer(str(small if size <= 32 and small.exists() else source))
    if not renderer.isValid():
        raise ValueError("invalid application icon")
    # Supersampling gives the small diagonal strokes clean, consistent edges.
    image = QImage(size * 4, size * 4, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        renderer.render(painter)
    finally:
        painter.end()
    return image.scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)


@lru_cache(maxsize=1)
def application_icon() -> QIcon:
    icon = QIcon()
    for size in ICON_SIZES:
        icon.addPixmap(QPixmap.fromImage(icon_image(size)))
    return icon
