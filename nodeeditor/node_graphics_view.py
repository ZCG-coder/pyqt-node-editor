# -*- coding: utf-8 -*-
"""
A module containing `Graphics View` for NodeEditor
"""
from typing import Optional
from enum import IntEnum
from qtpy.QtCore import QEvent, QPoint, QPointF, QRectF, Qt, Signal  # type: ignore
from qtpy.QtGui import (
    QDragEnterEvent,
    QDropEvent,
    QInputEvent,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QWheelEvent,
)
from qtpy.QtWidgets import QApplication, QGraphicsView, QWidget

from nodeeditor import _QT_API_NAME as QT_API
from nodeeditor.node_edge_dragging import EdgeDragging
from nodeeditor.node_edge_intersect import EdgeIntersect
from nodeeditor.node_edge_rerouting import EdgeRerouting
from nodeeditor.node_edge_snapping import EdgeSnapping
from nodeeditor.node_graphics_cutline import QDMCutLine
from nodeeditor.node_graphics_edge import QDMGraphicsEdge
from nodeeditor.node_graphics_socket import QDMGraphicsSocket
from nodeeditor.utils import (
    dumpException,
    isALTPressed,
    isCTRLPressed,
    isSHIFTPressed,
    pp,
)


class NodeEditorMode(IntEnum):
    NOOP = 1  #: Mode representing ready state
    EDGE_DRAG = 2  #: Mode representing when we drag edge state
    EDGE_CUT = 3  #: Mode representing when we draw a cutting edge
    EDGES_REROUTING = 4  #: Mode representing when we re-route existing edges
    NODE_DRAG = 5  #: Mode representing when we drag a node to calculate dropping on intersecting edge


STATE_STRING = ["", "Noop", "Edge Drag", "Edge Cut", "Edge Rerouting", "Node Drag"]

#: Distance when click on socket to enable `Drag Edge`
EDGE_DRAG_START_THRESHOLD = 50

#: Enable UnrealEngine style rerouting
EDGE_REROUTING_UE = True

#: Socket snapping distance
EDGE_SNAPPING_RADIUS = 24
#: Enable socket snapping feature
EDGE_SNAPPING = True


class QDMGraphicsView(QGraphicsView):  # type: ignore
    """Class representing NodeEditor's `Graphics View`"""

    #: pyqtSignal emitted when cursor position on the `Scene` has changed
    scenePosChanged = Signal(int, int)

    def __init__(self, grScene: "QDMGraphicsScene", parent: Optional[QWidget] = None):
        """
        :param grScene: reference to the :class:`~nodeeditor.node_graphics_scene.QDMGraphicsScene`
        :type grScene: :class:`~nodeeditor.node_graphics_scene.QDMGraphicsScene`
        :param parent: parent widget
        :type parent: ``QWidget``

        :Instance Attributes:

        - **grScene** - reference to the :class:`~nodeeditor.node_graphics_scene.QDMGraphicsScene`
        - **mode** - state of the `Graphics View`
        - **zoomInFactor**- ``float`` - zoom step scaling, default 1.25
        - **zoomClamp** - ``bool`` - do we clamp zooming or is it infinite?
        - **zoom** - current zoom step
        - **zoomStep** - ``int`` - the relative zoom step when zooming in/out
        - **zoomRange** - ``[min, max]``

        """
        super().__init__(parent)
        self.grScene = grScene

        self.initUI()

        self.setScene(self.grScene)

        self.mode = NodeEditorMode.NOOP
        self.editingFlag = False
        self.rubberBandDraggingRectangle = False

        # edge dragging
        self.dragging = EdgeDragging(self)

        # edges re-routing
        self.rerouting = EdgeRerouting(self)

        # drop a node on an existing edge
        self.edgeIntersect = EdgeIntersect(self)

        # edge snapping
        self.snapping = EdgeSnapping(self, snapping_radius=EDGE_SNAPPING_RADIUS)

        # cutline
        self.cutline = QDMCutLine()
        self.grScene.addItem(self.cutline)

        self.last_scene_mouse_position = QPoint(0, 0)
        self.zoomInFactor = 1.25
        self.zoomClamp = True
        self.zoom = 0
        self.zoomStep = 1
        self.zoomRange = [1, 10]
        self.scale(1, 1)

        # listeners
        self._drag_enter_listeners = []
        self._drop_listeners = []
        self.grabGesture(Qt.PinchGesture)

    def event(self, event):
        if event.type() == QEvent.Gesture:
            return self.gestureEvent(event)
        return super().event(event)

    def gestureEvent(self, event):
        pinch = event.gesture(Qt.PinchGesture)
        if pinch:
            self.handlePinchGesture(pinch)
            return True
        return False

    def handlePinchGesture(self, gesture):
        if gesture.state() == Qt.GestureUpdated:
            scale_factor = gesture.scaleFactor()
            # Compute the new zoom level by multiplying the current zoom by the scale factor
            new_zoom = self.zoomInFactor * scale_factor
            # Clamp the zoom to the specified range
            min_zoom, max_zoom = self.zoomRange
            clamped_zoom = max(min_zoom, min(new_zoom, max_zoom))
            # Determine the actual scale to apply relative to the current zoom
            scale_to_apply = (
                clamped_zoom / self.zoomInFactor if self.zoomInFactor != 0 else 1.0
            )
            self.zoomInFactor = clamped_zoom
            self.scale(scale_to_apply, scale_to_apply)

    def initUI(self):
        """Set up this ``QGraphicsView``"""
        # self.setRenderHints(QPainter.Antialiasing | QPainter.HighQualityAntialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        self.setRenderHints(
            QPainter.Antialiasing
            | QPainter.TextAntialiasing
            | QPainter.SmoothPixmapTransform
        )

        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.RubberBandDrag)

        # enable dropping
        self.setAcceptDrops(True)

    def isSnappingEnabled(self, event: "QInputEvent" = None) -> bool:
        """Returns ``True`` if snapping is currently enabled"""
        if not EDGE_SNAPPING:
            return False

        if event is None:
            return True

        if isCTRLPressed(event):
            return True

        return False

    def resetMode(self):
        """Helper function to re-set the grView's State Machine state to the default"""
        self.mode = NodeEditorMode.NOOP

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Trigger our registered `Drag Enter` events"""
        for callback in self._drag_enter_listeners:
            callback(event)

    def dropEvent(self, event: QDropEvent):
        """Trigger our registered `Drop` events"""
        for callback in self._drop_listeners:
            callback(event)

    def addDragEnterListener(self, callback: "function"):
        """
        Register callback for `Drag Enter` event

        :param callback: callback function
        """
        self._drag_enter_listeners.append(callback)

    def addDropListener(self, callback: "function"):
        """
        Register callback for `Drop` event

        :param callback: callback function
        """
        self._drop_listeners.append(callback)

    def mousePressEvent(self, event: QMouseEvent):
        """Dispatch Qt's mousePress event to corresponding function below"""
        if event.button() == Qt.MiddleButton:
            self.middleMouseButtonPress(event)
        elif event.button() == Qt.LeftButton:
            self.leftMouseButtonPress(event)
        elif event.button() == Qt.RightButton:
            self.rightMouseButtonPress(event)
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Dispatch Qt's mouseRelease event to corresponding function below"""
        if event.button() == Qt.MiddleButton:
            self.middleMouseButtonRelease(event)
        elif event.button() == Qt.LeftButton:
            self.leftMouseButtonRelease(event)
        elif event.button() == Qt.RightButton:
            self.rightMouseButtonRelease(event)
        else:
            super().mouseReleaseEvent(event)

    def middleMouseButtonPress(self, event: QMouseEvent):
        """When Middle mouse button was pressed"""

        item = self.getItemAtClick(event)

        # faking events for enable MMB dragging the scene
        if QT_API in ("pyqt5", "pyside2"):
            releaseEvent = QMouseEvent(
                QEvent.MouseButtonRelease,
                event.localPos(),
                event.screenPos(),
                Qt.LeftButton,
                Qt.NoButton,
                event.modifiers(),
            )
        else:
            releaseEvent = QMouseEvent(
                QEvent.MouseButtonRelease,
                event.localPos(),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.NoButton,
                event.modifiers(),
            )
        super().mouseReleaseEvent(releaseEvent)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        if QT_API in ("pyqt5", "pyside2"):
            fakeEvent = QMouseEvent(
                event.type(),
                event.localPos(),
                event.screenPos(),
                Qt.LeftButton,
                event.buttons() | Qt.LeftButton,
                event.modifiers(),
            )
        else:
            fakeEvent = QMouseEvent(
                event.type(),
                event.localPos(),
                Qt.MouseButton.LeftButton,
                event.buttons() | Qt.MouseButton.LeftButton,
                event.modifiers(),
            )
        super().mousePressEvent(fakeEvent)

    def middleMouseButtonRelease(self, event: QMouseEvent):
        """When Middle mouse button was released"""
        if QT_API in ("pyqt5", "pyside2"):
            fakeEvent = QMouseEvent(
                event.type(),
                event.localPos(),
                event.screenPos(),
                Qt.LeftButton,
                event.buttons() & ~Qt.LeftButton,
                event.modifiers(),
            )
        else:
            fakeEvent = QMouseEvent(
                event.type(),
                event.localPos(),
                Qt.MouseButton.LeftButton,
                event.buttons() & ~Qt.MouseButton.LeftButton,
                event.modifiers(),
            )
        super().mouseReleaseEvent(fakeEvent)
        self.setDragMode(QGraphicsView.RubberBandDrag)

    def leftMouseButtonPress(self, event: QMouseEvent):
        """When Left  mouse button was pressed"""

        # get the item we clicked on
        item = self.getItemAtClick(event)

        # we store the position of last LMB click
        self.last_lmb_click_scene_pos = self.mapToScene(event.pos())

        # logic - Shift + LMB Node
        if hasattr(item, "node") or isinstance(item, QDMGraphicsEdge) or item is None:
            if isSHIFTPressed(event):
                event.ignore()
                if QT_API in ("pyqt5", "pyside2"):
                    fakeEvent = QMouseEvent(
                        QEvent.MouseButtonPress,
                        event.localPos(),
                        event.screenPos(),
                        Qt.LeftButton,
                        event.buttons() | Qt.LeftButton,
                        event.modifiers() | Qt.ControlModifier,
                    )
                else:
                    fakeEvent = QMouseEvent(
                        QEvent.MouseButtonPress,
                        event.localPos(),
                        Qt.MouseButton.LeftButton,
                        event.buttons() | Qt.MouseButton.LeftButton,
                        event.modifiers() | Qt.KeyboardModifier.ControlModifier,
                    )
                super().mousePressEvent(fakeEvent)
                return

        if hasattr(item, "node"):
            if self.mode == NodeEditorMode.NOOP:
                self.mode = NodeEditorMode.NODE_DRAG
                self.edgeIntersect.enterState(item.node)

        # support for snapping
        if self.isSnappingEnabled(event):
            item = self.snapping.getSnappedSocketItem(event)

        if isinstance(item, QDMGraphicsSocket):
            if self.mode == NodeEditorMode.NOOP and isCTRLPressed(event):
                socket = item.socket
                if socket.hasAnyEdge():
                    self.mode = NodeEditorMode.EDGES_REROUTING
                    self.rerouting.startRerouting(socket)
                    return

            if self.mode == NodeEditorMode.NOOP:
                self.mode = NodeEditorMode.EDGE_DRAG
                self.dragging.edgeDragStart(item)
                return

        if self.mode == NodeEditorMode.EDGE_DRAG:
            res = self.dragging.edgeDragEnd(item)
            if res:
                return

        if item is None:
            if isCTRLPressed(event):
                self.mode = NodeEditorMode.EDGE_CUT
                if QT_API in ("pyqt5", "pyside2"):
                    fakeEvent = QMouseEvent(
                        QEvent.MouseButtonRelease,
                        event.localPos(),
                        event.screenPos(),
                        Qt.LeftButton,
                        Qt.NoButton,
                        event.modifiers(),
                    )
                else:
                    fakeEvent = QMouseEvent(
                        QEvent.MouseButtonRelease,
                        event.localPos(),
                        Qt.MouseButton.LeftButton,
                        Qt.MouseButton.NoButton,
                        event.modifiers(),
                    )
                super().mouseReleaseEvent(fakeEvent)
                QApplication.setOverrideCursor(Qt.CrossCursor)
                return
            else:
                self.rubberBandDraggingRectangle = True

        super().mousePressEvent(event)

    def leftMouseButtonRelease(self, event: QMouseEvent):
        """When Left  mouse button was released"""

        # get the item on which we release the mouse button on
        item = self.getItemAtClick(event)

        try:
            # logic - Shift + LMB release (add selection)
            if (
                hasattr(item, "node")
                or isinstance(item, QDMGraphicsEdge)
                or item is None
            ):
                if isSHIFTPressed(event):
                    event.ignore()
                    if QT_API in ("pyqt5", "pyside2"):
                        fakeEvent = QMouseEvent(
                            event.type(),
                            event.localPos(),
                            event.screenPos(),
                            Qt.LeftButton,
                            Qt.NoButton,
                            event.modifiers() | Qt.ControlModifier,
                        )
                    else:
                        fakeEvent = QMouseEvent(
                            event.type(),
                            event.localPos(),
                            Qt.MouseButton.LeftButton,
                            Qt.MouseButton.NoButton,
                            event.modifiers() | Qt.KeyboardModifier.ControlModifier,
                        )
                    super().mouseReleaseEvent(fakeEvent)
                    return

            if self.mode == NodeEditorMode.EDGE_DRAG:
                if self.distanceBetweenClickAndReleaseIsOff(event):
                    if self.isSnappingEnabled(event):
                        item = self.snapping.getSnappedSocketItem(event)

                    res = self.dragging.edgeDragEnd(item)
                    if res:
                        return

            if self.mode == NodeEditorMode.EDGES_REROUTING:
                if self.isSnappingEnabled(event):
                    item = self.snapping.getSnappedSocketItem(event)

                if not EDGE_REROUTING_UE:
                    # version 2 -- more consistent with the nodeeditor?
                    if not self.rerouting.first_mb_release:
                        # for confirmation of first MB release
                        self.rerouting.first_mb_release = True
                        # skip any re-routing until first MB was released
                        return

                self.rerouting.stopRerouting(
                    item.socket if isinstance(item, QDMGraphicsSocket) else None
                )

                # don't forget to end the REROUTING MODE

                self.mode = NodeEditorMode.NOOP

            if self.mode == NodeEditorMode.EDGE_CUT:
                self.cutIntersectingEdges()
                self.cutline.line_points = []
                self.cutline.update()
                QApplication.setOverrideCursor(Qt.ArrowCursor)
                self.mode = NodeEditorMode.NOOP
                return

            if self.mode == NodeEditorMode.NODE_DRAG:
                scenepos = self.mapToScene(event.pos())
                self.edgeIntersect.leaveState(scenepos.x(), scenepos.y())
                self.mode = NodeEditorMode.NOOP
                self.update()

            if self.rubberBandDraggingRectangle:
                self.rubberBandDraggingRectangle = False
                current_selected_items = self.grScene.selectedItems()

                if current_selected_items != self.grScene.scene._last_selected_items:
                    if current_selected_items == []:
                        self.grScene.itemsDeselected.emit()
                    else:
                        self.grScene.itemSelected.emit()
                    self.grScene.scene._last_selected_items = current_selected_items

                # the rubber band rectangle doesn't disappear without handling the event
                super().mouseReleaseEvent(event)
                return

            # otherwise deselect everything
            if item is None:
                self.grScene.itemsDeselected.emit()

        except:
            dumpException()

        super().mouseReleaseEvent(event)

    def rightMouseButtonPress(self, event: QMouseEvent):
        """When Right mouse button was pressed"""
        super().mousePressEvent(event)

    def rightMouseButtonRelease(self, event: QMouseEvent):
        """When Right mouse button was release"""

        ## cannot be because with dragging RMB we spawn Create New Node Context Menu
        ## However, you could use this if you want to cancel with RMB
        # if self.mode == MODE_EDGE_DRAG:
        #     self.dragging.edgeDragEnd(None)
        #     return

        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Overriden Qt's ``mouseMoveEvent`` handling Scene/View logic"""
        scenepos = self.mapToScene(event.pos())

        try:
            modified = self.setSocketHighlights(
                scenepos, highlighted=False, radius=EDGE_SNAPPING_RADIUS + 100
            )
            if self.isSnappingEnabled(event):
                _, scenepos = self.snapping.getSnappedToSocketPosition(scenepos)
            if modified:
                self.update()

            if self.mode == NodeEditorMode.EDGE_DRAG:
                self.dragging.updateDestination(scenepos.x(), scenepos.y())

            if self.mode == NodeEditorMode.NODE_DRAG:
                self.edgeIntersect.update(scenepos.x(), scenepos.y())

            if self.mode == NodeEditorMode.EDGES_REROUTING:
                self.rerouting.updateScenePos(scenepos.x(), scenepos.y())

            if self.mode == NodeEditorMode.EDGE_CUT and self.cutline is not None:
                self.cutline.line_points.append(scenepos)
                self.cutline.update()

        except Exception as e:
            dumpException()

        self.last_scene_mouse_position = scenepos

        self.scenePosChanged.emit(int(scenepos.x()), int(scenepos.y()))

        super().mouseMoveEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        """
        .. note::
            This overridden Qt's method was used for handling key shortcuts, before we implemented proper
            ``QWindow`` with Actions and Menu. Still the commented code serves as an example on how to handle
            key presses without Qt's framework for Actions and shortcuts. There is also an example on
            how to solve the problem when a Node contains Text/LineEdit and we press the `Delete`
            key (also serving to delete `Node`)

        :param event: Qt's Key event
        :type event: ``QKeyEvent``
        :return:
        """
        # Use this code below if you wanna have shortcuts in this widget.
        # You want to use this, when you don't have a window which handles these shortcuts for you

        # if event.key() == Qt.Key_Delete:
        #     if not self.editingFlag:
        #         self.deleteSelected()
        #     else:
        #         super().keyPressEvent(event)
        # elif event.key() == Qt.Key_S and event.modifiers() & Qt.ControlModifier:
        #     self.grScene.scene.saveToFile("graph.json")
        # elif event.key() == Qt.Key_L and event.modifiers() & Qt.ControlModifier:
        #     self.grScene.scene.loadFromFile("graph.json")
        # elif event.key() == Qt.Key_Z and isCTRLPressed(event) and not isSHIFTPressed(event):
        #     self.grScene.scene.history.undo()
        # elif event.key() == Qt.Key_Z and isCTRLPressed(event)  and isSHIFTPressed(event):
        #     self.grScene.scene.history.redo()
        # elif event.key() == Qt.Key_H:
        #     print("HISTORY:     len(%d)" % len(self.grScene.scene.history.history_stack),
        #           " -- current_step", self.grScene.scene.history.history_current_step)
        #     ix = 0
        #     for item in self.grScene.scene.history.history_stack:
        #         print("#", ix, "--", item['desc'])
        #         ix += 1
        # else:
        super().keyPressEvent(event)

    def cutIntersectingEdges(self):
        """Compare which `Edges` intersect with current `Cut line` and delete them safely"""
        for ix in range(len(self.cutline.line_points) - 1):
            p1 = self.cutline.line_points[ix]
            p2 = self.cutline.line_points[ix + 1]

            # @TODO: we could collect all touched nodes, and notify them once after all edges removed
            # we could cut 3 edges leading to a single nodeeditor this will notify it 3x
            # maybe we could use some Notifier class with methods collect() and dispatch()
            for edge in self.grScene.scene.edges.copy():
                if edge.grEdge.intersectsWith(p1, p2):
                    edge.remove()
        self.grScene.scene.history.storeHistory("Delete cutted edges", setModified=True)

    def setSocketHighlights(
        self, scenepos: QPointF, highlighted: bool = True, radius: float = 50
    ):
        """Set/disable socket highlights in Scene area defined by `scenepos` and `radius`"""
        scanrect = QRectF(
            scenepos.x() - radius, scenepos.y() - radius, radius * 2, radius * 2
        )
        items = self.grScene.items(scanrect)
        items = list(filter(lambda x: isinstance(x, QDMGraphicsSocket), items))
        for grSocket in items:
            grSocket.isHighlighted = highlighted
        return items

    def deleteSelected(self):
        """Shortcut for safe deleting every object selected in the `Scene`."""
        for item in self.grScene.selectedItems():
            if isinstance(item, QDMGraphicsEdge):
                item.edge.remove()
            elif hasattr(item, "node"):
                item.node.remove()
        self.grScene.scene.history.storeHistory("Delete selected", setModified=True)

    def debug_modifiers(self, event):
        """Helper function get string if we hold Ctrl, Shift or Alt modifier keys"""
        out = "MODS: "
        if isSHIFTPressed(event):
            out += "SHIFT "
        if isCTRLPressed(event):
            out += "CTRL "
        if isALTPressed(event):
            out += "ALT "
        return out

    def getItemAtClick(self, event: QEvent) -> "QGraphicsItem":
        """Return the object on which we've clicked/release mouse button

        :param event: Qt's mouse or key event
        :type event: ``QEvent``
        :return: ``QGraphicsItem`` which the mouse event happened or ``None``
        """
        pos = event.pos()
        obj = self.itemAt(pos)
        return obj

    def distanceBetweenClickAndReleaseIsOff(self, event: QMouseEvent) -> bool:
        """Measures if we are too far from the last Mouse button click scene position.
        This is used for detection if we release too far after we clicked on a `Socket`

        :param event: Qt's mouse event
        :type event: ``QMouseEvent``
        :return: ``True`` if we released too far from where we clicked before
        """
        new_lmb_release_scene_pos = self.mapToScene(event.pos())
        dist_scene = new_lmb_release_scene_pos - self.last_lmb_click_scene_pos
        edge_drag_threshold_sq = EDGE_DRAG_START_THRESHOLD * EDGE_DRAG_START_THRESHOLD
        return (
            dist_scene.x() * dist_scene.x() + dist_scene.y() * dist_scene.y()
        ) > edge_drag_threshold_sq

    def wheelEvent(self, event: QWheelEvent):
        """overridden Qt's ``wheelEvent``. This handles zooming"""
        if event.pixelDelta() != QPoint(0, 0):
            return super().wheelEvent(event)

        # calculate our zoom Factor
        zoomOutFactor = 1 / self.zoomInFactor

        # calculate zoom
        if event.angleDelta().y() > 0:
            zoomFactor = self.zoomInFactor
            self.zoom += self.zoomStep
        else:
            zoomFactor = zoomOutFactor
            self.zoom -= self.zoomStep

        clamped = False
        if self.zoom < self.zoomRange[0]:
            self.zoom, clamped = self.zoomRange[0], True
        if self.zoom > self.zoomRange[1]:
            self.zoom, clamped = self.zoomRange[1], True

        # set scene scale
        if not clamped or self.zoomClamp is False:
            self.scale(zoomFactor, zoomFactor)
