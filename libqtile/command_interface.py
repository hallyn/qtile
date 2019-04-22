# Copyright (c) 2019 Sean Vig
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from abc import abstractmethod, ABCMeta
from typing import Any, Dict, Tuple

from libqtile import ipc
from libqtile.command_graph import CommandGraphCall, CommandGraphNode
from libqtile.command_object import CommandObject, CommandError, CommandException, SelectError
from libqtile.log_utils import logger

SUCCESS = 0
ERROR = 1
EXCEPTION = 2


class CommandInterface(metaclass=ABCMeta):
    """Defines an interface which can be used to evaluate a given call on a command graph.

    The implementations of this may use, for example, an IPC call to access the
    running qtile instance remotely or directly access the qtile instance from
    within the same process, or it may return lazily evaluated results.
    """

    @abstractmethod
    def execute(self, call: CommandGraphCall, args: Tuple, kwargs: Dict) -> Any:
        """Execute the given call, returning the result of the execution

        Perform the given command graph call, calling the function with the
        given arguments and keyword arguments.

        Parameters
        ----------
        call: CommandGraphCall
            The call on the command graph that is to be performed.
        args:
            The arguments to pass into the command graph call.
        kwargs:
            The keyword arguments to pass into the command graph call.
        """
        pass  # pragma: no cover

    @abstractmethod
    def has_command(self, node: CommandGraphNode, command: str) -> bool:
        """Check if the given command exists

        Parameters
        ----------
        node : CommandGraphNode
            The node to check for commands
        command : str
            The name of the command to check for

        Returns
        -------
        bool
            True if the command is resolved on the given node
        """
        pass  # pragma: no cover

    @abstractmethod
    def has_item(self, node: CommandGraphNode, object_type: str, item: str) -> bool:
        """Check if the given item exists

        Parameters
        ----------
        node : CommandGraphNode
            The node to check for items
        object_type : str
            The type of object to check for items.
        command : str
            The name of the item to check for

        Returns
        -------
        bool
            True if the item is resolved on the given node
        """
        pass  # pragma: no cover


class QtileCommandInterface(CommandInterface):
    def __init__(self, command_object: CommandObject):
        """A command object that directly resolves commands

        Parameters
        ----------
        command_object : CommandObject
            The command object to use for resolving the commands and items
            against.
        """
        self._command_object = command_object

    def execute(self, call: CommandGraphCall, args: Tuple, kwargs: Dict) -> Any:
        """Execute the given call, returning the result of the execution

        Perform the given command graph call, calling the function with the
        given arguments and keyword arguments.

        Parameters
        ----------
        call: CommandGraphCall
            The call on the command graph that is to be performed.
        args:
            The arguments to pass into the command graph call.
        kwargs:
            The keyword arguments to pass into the command graph call.
        """
        obj = self._command_object.select(call.selectors)

        cmd = obj.command(call.name)
        if not cmd:
            return "No such command."

        logger.debug("Command: %s(%s, %s)", call.name, args, kwargs)
        return cmd(*args, **kwargs)

    def has_command(self, node: CommandGraphNode, command: str) -> bool:
        """Check if the given command exists

        Parameters
        ----------
        node : CommandGraphNode
            The node to check for commands
        command : str
            The name of the command to check for

        Returns
        -------
        bool
            True if the command is resolved on the given node
        """
        obj = self._command_object.select(node.selectors)
        cmd = obj.command(command)
        return cmd is not None

    def has_item(self, node: CommandGraphNode, object_type: str, item: str) -> bool:
        """Check if the given item exists

        Parameters
        ----------
        node : CommandGraphNode
            The node to check for items
        object_type : str
            The type of object to check for items.
        command : str
            The name of the item to check for

        Returns
        -------
        bool
            True if the item is resolved on the given node
        """
        try:
            self._command_object.select(node.selectors + [(object_type, item)])
        except SelectError:
            return False
        return True


class IPCCommandInterface(CommandInterface):
    def __init__(self, ipc_client: ipc.Client):
        """Build a command object which resolves commands through IPC calls

        Parameters
        ----------
        ipc_client : ipc.Client
            The client that is to be used to resolve the calls.
        """
        self._client = ipc_client

    def execute(self, call: CommandGraphCall, args: Tuple, kwargs: Dict) -> Any:
        """Execute the given call, returning the result of the execution

        Executes the given command over the given IPC client.  Returns the
        result of the execution.

        Parameters
        ----------
        call: CommandGraphCall
            The call on the command graph that is to be performed.
        args:
            The arguments to pass into the command graph call.
        kwargs:
            The keyword arguments to pass into the command graph call.
        """
        status, result = self._client.send((
            call.parent.selectors, call.name, args, kwargs
        ))
        if status == SUCCESS:
            return result
        if status == ERROR:
            raise CommandError(result)
        raise CommandException(result)

    def has_command(self, node: CommandGraphNode, command: str) -> bool:
        """Check if the given command exists

        Resolves the allowed commands over the IPC interface, and returns a
        boolean indicating of the given command is valid.

        Parameters
        ----------
        node : CommandGraphNode
            The node to check for commands
        command : str
            The name of the command to check for

        Returns
        -------
        bool
            True if the command is resolved on the given node
        """
        cmd_call = node.call("commands")
        commands = self.execute(cmd_call, (), {})
        return command in commands

    def has_item(self, node: CommandGraphNode, object_type: str, item: str) -> bool:
        """Check if the given item exists

        Resolves the available commands for the given command node of the given
        command type.  Performs the resolution of the items through the given
        IPC client.

        Parameters
        ----------
        node : CommandGraphNode
            The node to check for items
        object_type : str
            The type of object to check for items.
        command : str
            The name of the item to check for

        Returns
        -------
        bool
            True if the item is resolved on the given node
        """
        items_call = node.call("items")
        _, items = self.execute(items_call, (object_type,), {})
        return items is not None and item in items
