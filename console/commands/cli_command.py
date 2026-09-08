from typing import ClassVar

from ai_models_manager.console.commands.command_name import CommandName


class CLICommand:
    name: ClassVar[CommandName]
