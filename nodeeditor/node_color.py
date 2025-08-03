from PyQt6.QtGui import QColor
import enum


class Colors(enum.Enum):
    SELECTED = QColor("#FFBF00")


class SocketTypes:
    MATRIX = QColor("#9A3FFC")
    NUM = QColor("#3FC7FC")
    ULONG = QColor("#1B51BD")
    STR = QColor("#00B75E")


class NodeTypes:
    IO = QColor("#966202")
    COND = QColor("#009B77")
    MATRIX = QColor("#9A3FFC")
    NUM = QColor("#3191B7")
    STR = QColor("#1460C3")
    CUSTOM = QColor("#887F00")
