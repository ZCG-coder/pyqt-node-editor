from examples.example_calculator.calc_conf import *
from examples.example_calculator.calc_node_base import *


class CalcOutputContent(QDMNodeContentWidget):
    def initUI(self):
        self.lbl = QLabel("0", self)
        self.lbl.setAlignment(Qt.AlignLeft)
        self.lbl.setObjectName(self.node.content_label_objname)


@register_node(OP_NODE_OUTPUT)
class CalcNode_Output(CalcNode):
    icon = "icons/out.png"
    op_code = OP_NODE_OUTPUT
    op_title = "Output"
    content_label_objname = "calc_node_output"

    def __init__(self, scene):
        super().__init__(scene, inputs=[1], outputs=[])

    def initInnerClasses(self):
        super().initInnerClasses()
        self.content = CalcOutputContent(self)
        self.grNode = CalcGraphicsNode(self)

    def evalImplementation(self):
        input_node = self.getInput(0)
        if not input_node:

            self.grNode.setToolTip("Input is not connected")
            self.markInvalid()
            self.content.lbl.setText("0")
            self.textOutput = None
            self.scene.OnOutputEvaluated(self)
            return None, None

        val, txt = input_node.eval()

        if txt:
            self.calcText = txt + " = " + str(round(val, 4)) if val else None
        if not self.calcText == "":
            self.textOutput = self.calcText

        if val is None:
            self.grNode.setToolTip("Input is NaN")
            self.markInvalid()
            return None

        self.content.lbl.setText(str(round(val, 4)))
        self.markInvalid(False)
        self.markDirty(False)
        self.grNode.setToolTip("")

        # sending out the output node after a change
        self.scene.OnOutputEvaluated(self)
        return val, txt




