# -*- coding: utf-8 -*-
"""
A module containing the Edge Validator functions which can be registered as callbacks to
:class:`~nodeeditor.node_edge.Edge` class.

Example of registering Edge Validator callbacks:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can register validation callbacks once for example on the bottom of node_edge.py file or on the
application start with calling this:

.. code-block:: python

    from nodeeditor.node_edge_validators import *

    Edge.registerEdgeValidator(edge_validator_debug)
    Edge.registerEdgeValidator(edge_cannot_connect_two_outputs_or_two_inputs)
    Edge.registerEdgeValidator(edge_cannot_connect_input_and_output_of_same_node)
    Edge.registerEdgeValidator(edge_cannot_connect_input_and_output_of_different_type)
    Edge.registerEdgeValidator(edge_cannot_create_loop)


"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nodeeditor.node_socket import Socket
    from nodeeditor.node_node import Node


def print_error(*args) -> None:  # type: ignore
    """Helper method which prints to console if `DEBUG` is set to `True`"""


def edge_validator_debug(input: "Socket", output: "Socket") -> bool:  # type: ignore
    """This will consider edge always valid, however writes bunch of debug stuff into console"""
    print("VALIDATING:")
    print(input, "input" if input.is_input else "output", "of node", input.node)
    for s in input.node.inputs + input.node.outputs:
        print("\t", s, "input" if s.is_input else "output")
    print(output, "input" if input.is_input else "output", "of node", output.node)
    for s in output.node.inputs + output.node.outputs:
        print("\t", s, "input" if s.is_input else "output")

    return True


def edge_cannot_connect_two_outputs_or_two_inputs(
    input: "Socket", output: "Socket"
) -> bool:  # type: ignore
    """Edge is invalid if it connects 2 output sockets or 2 input sockets"""
    if input.is_output and output.is_output:
        print_error("Connecting 2 outputs")
        return False

    if input.is_input and output.is_input:
        print_error("Connecting 2 inputs")
        return False

    return True


def edge_cannot_connect_input_and_output_of_same_node(
    input: "Socket", output: "Socket"
) -> bool:  # type: ignore
    """Edge is invalid if it connects the same node"""
    if input.node == output.node:
        print_error("Connecting the same node")
        return False

    return True


def edge_cannot_connect_input_and_output_of_different_type(
    input: "Socket", output: "Socket"
) -> bool:
    """Edge is invalid if it connects sockets with different colors"""

    if input.socket_type != output.socket_type:
        print_error("Connecting sockets with different colors")
        return False

    return True


def edge_cannot_create_loop(input: "Socket", output: "Socket") -> bool:
    """Edge is invalid if it would create a loop in the graph"""

    # Determine which socket is input and which is output
    if input.is_input and output.is_output:
        input_socket = input
        output_socket = output
    elif input.is_output and output.is_input:
        input_socket = output
        output_socket = input
    else:
        # This case should be caught by other validators
        return True

    # Check if connecting output_socket's node to input_socket's node would create a loop
    # We need to check if there's already a path from input_socket's node to output_socket's node

    def has_path_to_node(start_node: "Node", target_node: "Node", visited: set) -> bool:
        """Check if there's a path from start_node to target_node using DFS"""
        if start_node == target_node:
            return True

        if start_node in visited:
            return False

        visited.add(start_node)

        # Follow all output edges from this node
        for output_sock in start_node.outputs:
            for edge in output_sock.edges:
                if edge.end_socket and edge.end_socket.node:
                    next_node = edge.end_socket.node
                    if has_path_to_node(next_node, target_node, visited):
                        return True

        return False

    # Check if there's already a path from input node to output node
    if has_path_to_node(input_socket.node, output_socket.node, set()):
        print_error("Connection would create a loop")
        return False

    return True
