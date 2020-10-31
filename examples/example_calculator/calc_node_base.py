from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from nodeeditor.node_scene import Scene
from nodeeditor.node_node import Node
from nodeeditor.node_content_widget import QDMNodeContentWidget
from nodeeditor.node_graphics_node import QDMGraphicsNode
from nodeeditor.node_socket import LEFT_CENTER, RIGHT_CENTER
from nodeeditor.utils import dumpException


class CalcScene(Scene):
    def __init__(self):
        super().__init__()

        # Extending Scene. Added OnOutputEvaluated to scene.class and is overridden here. This allows for using the
        # values of the output node outside of the node editor. We could move
        # addEvaluatedListener and OnOutputEvaluated functionality to the scene class.

        self._evaluated_listeners = []

    def addEvaluatedlistener(self, callback):
        self._evaluated_listeners.append(callback)

    def OnOutputEvaluated(self, output_node):
        for callback in self._evaluated_listeners: callback(output_node)

class CalcGraphicsNode(QDMGraphicsNode):
    def initSizes(self):
        super().initSizes()
        self.width = 160
        self.height = 74
        self.edge_roundness = 6
        self.edge_padding = 0
        self.title_horizontal_padding = 8
        self.title_vertical_padding = 10

    def initAssets(self):
        super().initAssets()
        self.icons = QImage("icons/status_icons.png")

    def paint(self, painter, QStyleOptionGraphicsItem, widget=None):
        super().paint(painter, QStyleOptionGraphicsItem, widget)

        offset = 24.0
        if self.node.isDirty(): offset = 0.0
        if self.node.isInvalid(): offset = 48.0

        painter.drawImage(
            QRectF(-10, -10, 24.0, 24.0),
            self.icons,
            QRectF(offset, 0, 24.0, 24.0)
        )


class CalcContent(QDMNodeContentWidget):
    def initUI(self):
        lbl = QLabel(self.node.content_label, self)
        lbl.setObjectName(self.node.content_label_objname)


class CalcNode(Node):

    icon = ""
    op_code = 0
    op_title = "Undefined"
    content_label = ""
    content_label_objname = "calc_node_bg"

    GraphicsNode_class = CalcGraphicsNode
    NodeContent_class = CalcContent


    def __init__(self, scene, inputs=[2,2], outputs=[1]):
        super().__init__(scene, self.__class__.op_title, inputs, outputs)

        self.value = None
        self.calcText = ""
        self.textOutput = ""
        self.scene = scene

        # it's really important to mark all nodes Dirty by default
        self.markDirty()

    def initSettings(self):
        super().initSettings()
        self.input_socket_position = LEFT_CENTER
        self.output_socket_position = RIGHT_CENTER

    def evalOperation(self, input1, input2):
        # needs to be overridden, each input exist of a value/text pair
        # needs to be used as input1[0] + input2[0] and input1[1] + "+" input2[1]
        return 123, "123"

    def evalImplementation(self):
        i1 = self.getInput(0)
        i2 = self.getInput(1)

        if i1 is None or i2 is None:
            self.markInvalid()
            self.clearOutputNode()
            self.markDescendantsDirty()
            self.grNode.setToolTip("Connect all inputs")

            return None, None

        else:
            # value and text
            val, calcText = self.evalOperation(i1.eval(), i2.eval())

            self.value = val
            self.calcText = calcText

            self.markDirty(False)
            self.markInvalid(False)
            self.grNode.setToolTip("")
            self.markDescendantsDirty()

            self.evalChildren()

            return val, calcText

    def clearOutputNode(self):
        # If there is a break in the chain, the Output node should be "0" with no result in the result box.
        for other_node in self.getChildrenNodes():
            if other_node.__class__.__name__ == "CalcNode_Output":
                other_node.content.lbl.setText("0")
                other_node.content.val = 0
                other_node.textOutput = None
                self.scene.OnOutputEvaluated(self)

            other_node.clearOutputNode()

    def eval(self):
        val = 0
        txt = ""
        try:
            if not self.isDirty() and not self.isInvalid():
                # print(" _> returning cached %s value:" % self.__class__.__name__, self.value)
                val = self.value
                txt = self.calcText
            else:
                val, txt = self.evalImplementation()
                # txt = str(val)
        except ValueError as e:
            self.markInvalid()
            self.grNode.setToolTip(str(e))
            self.markDescendantsDirty()
        except Exception as e:
            self.markInvalid()
            self.grNode.setToolTip(str(e))
            dumpException(e)
        return val, txt

    def onInputChanged(self, socket=None):
        # print("%s::__onInputChanged" % self.__class__.__name__)
        self.markDirty()
        self.eval()

    def serialize(self):
        res = super().serialize()
        res['op_code'] = self.__class__.op_code
        return res

    def deserialize(self, data, hashmap={}, restore_id=True):
        res = super().deserialize(data, hashmap, restore_id)
        # print("Deserialized CalcNode '%s'" % self.__class__.__name__, "res:", res)
        return res