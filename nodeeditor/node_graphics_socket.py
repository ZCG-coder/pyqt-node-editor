# -*- coding: utf-8 -*-
"""
A module containing Graphics representation of a :class:`~nodeeditor.node_socket.Socket`
"""
from qtpy.QtWidgets import QGraphicsItem, QApplication
from qtpy.QtGui import QColor, QBrush, QPen, QFontMetrics
from qtpy.QtCore import Qt, QRectF, QPoint, QPointF

SOCKET_COLORS = [
    QColor("#FFFF7700"),
    QColor("#FF52e220"),
    QColor("#FF0056a6"),
    QColor("#FFa86db1"),
    QColor("#FFb54747"),
    QColor("#FFdbe220"),
    QColor("#FF888888"),
    QColor("#FFFF7700"),
    QColor("#FF52e220"),
    QColor("#FF0056a6"),
    QColor("#FFa86db1"),
    QColor("#FFb54747"),
    QColor("#FFdbe220"),
    QColor("#FF888888"),
]


class QDMGraphicsSocket(QGraphicsItem):
    """Class representing Graphic `Socket` in ``QGraphicsScene``"""

    def __init__(self, socket: "Socket"):
        """
        :param socket: reference to :class:`~nodeeditor.node_socket.Socket`
        :type socket: :class:`~nodeeditor.node_socket.Socket`
        """
        super().__init__(socket.node.grNode)

        self.socket = socket

        self.isHighlighted = False

        self.radius = 6
        self.outline_width = 1
        self.initAssets()

    @property
    def socket_type(self):
        return self.socket.socket_type

    def getSocketColor(self, key):
        """Returns the ``QColor`` for this ``key``"""
        return SOCKET_COLORS[key]

    def changeSocketType(self):
        """Change the Socket Type"""
        self._color_background = self.getSocketColor(self.socket_type)
        self._brush = QBrush(self._color_background)
        # print("Socket changed to:", self._color_background.getRgbF())
        self.update()

    def initAssets(self):
        """Initialize ``QObjects`` like ``QColor``, ``QPen`` and ``QBrush``"""

        # determine socket color
        self._color_background = self.getSocketColor(self.socket_type)
        self._color_outline = QColor("#FF000000")
        self._color_highlight = QColor("#FF37A6FF")

        self._pen = QPen(self._color_outline)
        self._pen.setWidthF(self.outline_width)
        self._pen_highlight = QPen(self._color_highlight)
        self._pen_highlight.setWidthF(2.0)
        self._brush = QBrush(self._color_background)

    def paint(self, painter, *_):
        """Painting a circle"""
        painter.setBrush(self._brush)
        painter.setPen(self._pen if not self.isHighlighted else self._pen_highlight)
        painter.drawEllipse(
            -self.radius, -self.radius, 2 * self.radius, 2 * self.radius
        )
        painter.setBrush(Qt.NoBrush)

        metrics = QFontMetrics(QApplication.font())
        elided = metrics.elidedText(self.socket.name, Qt.ElideRight, 100)

        painter.setPen(QColor("white"))
        if self.socket.is_input:
            painter.drawText(QPoint(self.radius * 2, int(self.radius / 2)), elided)
        else:
            text_width = metrics.horizontalAdvance(elided)
            x_right = -2 * self.radius - text_width
            painter.drawText(
                QPointF(x_right, int(self.radius / 2)),
                elided,
            )

    def boundingRect(self) -> QRectF:
        """Defining Qt' bounding rectangle"""
        return QRectF(
            -self.radius - self.outline_width,
            -self.radius - self.outline_width,
            2 * (self.radius + self.outline_width),
            2 * (self.radius + self.outline_width),
        )
