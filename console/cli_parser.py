from pathlib import Path
from typing import Callable, ClassVar, Sequence

from ai_models_manager.config import (
    APP_NAME,
    DEFAULT_CONTEXT_LENGTH,
    DEFAULT_IMAGE_HEIGHT,
    DEFAULT_IMAGE_WIDTH,
)
from ai_models_manager.console.argument_parser import _ArgumentParser
from ai_models_manager.console.commands.agent_command import AgentCommand
from ai_models_manager.console.commands.chat_command import ChatCommand
from ai_models_manager.console.commands.clear_cache_command import ClearCacheCommand
from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.details_command import DetailsCommand
from ai_models_manager.console.commands.help_command import HelpCommand
from ai_models_manager.console.commands.image_command import ImageCommand
from ai_models_manager.console.commands.install_command import InstallCommand
from ai_models_manager.console.commands.list_command import ListCommand
from ai_models_manager.console.commands.models_refresh_command import ModelsRefreshCommand
from ai_models_manager.console.commands.purge_command import PurgeCommand
from ai_models_manager.console.commands.run_command import RunCommand
from ai_models_manager.console.commands.session_command import SessionCommand
from ai_models_manager.console.commands.set_base_command import SetBaseCommand
from ai_models_manager.console.commands.setup_command import SetupCommand
from ai_models_manager.console.commands.stop_all_command import StopAllCommand
from ai_models_manager.console.commands.stop_command import StopCommand
from ai_models_manager.console.commands.tool_command import ToolCommand
from ai_models_manager.console.commands.tools_command import ToolsCommand
from ai_models_manager.console.commands.tui_command import TUICommand
from ai_models_manager.console.commands.uninstall_command import UninstallCommand
from ai_models_manager.console.commands.update_command import UpdateCommand
from ai_models_manager.console.commands.update_model_command import UpdateModelCommand
from ai_models_manager.console.commands.version_command import VersionCommand
from ai_models_manager.console.help_text import build_help_text
from ai_models_manager.enums.install_source_type import InstallSourceType
from ai_models_manager.enums.list_target import ListTarget
from ai_models_manager.enums.model_backend import ModelBackend
from ai_models_manager.enums.purge_component import PurgeComponent
from ai_models_manager.enums.setup_component import SetupComponent
from ai_models_manager.enums.sort_direction import SortDirection
from ai_models_manager.exceptions.cli_usage_error import CLIUsageError


class CLIParser:
    """Convert raw argv into an immutable, command-specific DTO."""

    COMMAND_AGENT: ClassVar[str] = "--agent"
    COMMAND_CHAT: ClassVar[str] = "--chat"
    COMMAND_CLEAR_CACHE: ClassVar[str] = "--clear-cache"
    COMMAND_DETAILS: ClassVar[str] = "--details"
    COMMAND_HELP: ClassVar[str] = "--help"
    COMMAND_IMAGE: ClassVar[str] = "--image"
    COMMAND_INSTALL: ClassVar[str] = "--install"
    COMMAND_MODELS: ClassVar[str] = "--models"
    COMMAND_MODELS_REFRESH: ClassVar[str] = "--models-refresh"
    COMMAND_PURGE: ClassVar[str] = "--purge"
    COMMAND_RUN: ClassVar[str] = "--run"
    COMMAND_SESSION: ClassVar[str] = "--session"
    COMMAND_SETUP: ClassVar[str] = "--setup"
    COMMAND_SET_BASE: ClassVar[str] = "--set-base"
    COMMAND_STOP: ClassVar[str] = "--stop"
    COMMAND_STOP_ALL: ClassVar[str] = "--stop-all"
    COMMAND_TOOL: ClassVar[str] = "--tool"
    COMMAND_TOOLS: ClassVar[str] = "--tools"
    COMMAND_UNINSTALL: ClassVar[str] = "--uninstall"
    COMMAND_UPDATE: ClassVar[str] = "--update"
    COMMAND_UPDATE_MODEL: ClassVar[str] = "--update-model"
    COMMAND_VERSION: ClassVar[str] = "--version"
    OPTION_VERBOSE: ClassVar[str] = "--verbose"

    OPTION_ASCENDING: ClassVar[str] = "--asc"
    OPTION_BACKEND: ClassVar[str] = "--backend"
    OPTION_BACKEND_SHORT: ClassVar[str] = "-b"
    OPTION_CONTEXT_LENGTH: ClassVar[str] = "--context-length"
    OPTION_CONTEXT_LENGTH_SHORT: ClassVar[str] = "-l"
    OPTION_DESCENDING: ClassVar[str] = "--desc"
    OPTION_DEPENDENCIES: ClassVar[str] = "--dependencies"
    OPTION_DEPENDENCIES_SHORT: ClassVar[str] = "-d"
    OPTION_DIRECTORY: ClassVar[str] = "--directory"
    OPTION_DIRECTORY_SHORT: ClassVar[str] = "-d"
    OPTION_DELETE: ClassVar[str] = "--delete"
    OPTION_DELETE_SHORT: ClassVar[str] = "-d"
    OPTION_INPUT_FILE: ClassVar[str] = "--input-file"
    OPTION_INPUT_FILE_SHORT: ClassVar[str] = "-i"
    OPTION_FILE_NAME: ClassVar[str] = "--file-name"
    OPTION_FILE_NAME_SHORT: ClassVar[str] = "-n"
    OPTION_HEIGHT: ClassVar[str] = "--height"
    OPTION_HEIGHT_SHORT: ClassVar[str] = "-h"
    OPTION_OUTPUT_DIRECTORY: ClassVar[str] = "--output-dir"
    OPTION_OUTPUT_DIRECTORY_SHORT: ClassVar[str] = "-o"
    OPTION_PROMPT: ClassVar[str] = "--prompt"
    OPTION_PROMPT_SHORT: ClassVar[str] = "-p"
    OPTION_STRENGTH: ClassVar[str] = "--strength"
    OPTION_WIDTH: ClassVar[str] = "--width"
    OPTION_WIDTH_SHORT: ClassVar[str] = "-w"
    OPTION_EXECUTION_APPROVALS: ClassVar[str] = "--exec"
    OPTION_ENABLE: ClassVar[str] = "--enable"
    OPTION_ENABLE_SHORT: ClassVar[str] = "-e"
    OPTION_DISABLE: ClassVar[str] = "--disable"
    OPTION_DISABLE_SHORT: ClassVar[str] = "-d"
    OPTION_ORDER: ClassVar[str] = "--order"
    OPTION_ORDER_SHORT: ClassVar[str] = "-o"
    OPTION_RENAME: ClassVar[str] = "--rename"
    OPTION_RENAME_SHORT: ClassVar[str] = "-r"
    OPTION_SESSION: ClassVar[str] = "--session"
    OPTION_SESSION_SHORT: ClassVar[str] = "-s"
    OPTION_SOURCE: ClassVar[str] = "--source"
    OPTION_SOURCE_SHORT: ClassVar[str] = "-s"
    OPTION_TYPE: ClassVar[str] = "--type"
    OPTION_TYPE_SHORT: ClassVar[str] = "-t"

    DEFAULT_LIST_ORDER: ClassVar[str] = "model"
    DEFAULT_IMAGE_HEIGHT: ClassVar[int] = DEFAULT_IMAGE_HEIGHT
    DEFAULT_IMAGE_WIDTH: ClassVar[int] = DEFAULT_IMAGE_WIDTH

    def __init__(self) -> None:
        self.verbose = False
        self.command_parsers: dict[
            str, Callable[[Sequence[str]], CLICommand]
        ] = {
            self.COMMAND_AGENT: self._parse_agent,
            self.COMMAND_CHAT: self._parse_chat,
            self.COMMAND_CLEAR_CACHE: self._parse_clear_cache,
            self.COMMAND_DETAILS: self._parse_details,
            self.COMMAND_HELP: self._parse_help,
            self.COMMAND_IMAGE: self._parse_image,
            self.COMMAND_INSTALL: self._parse_install,
            self.COMMAND_VERSION: self._parse_version,
            self.COMMAND_MODELS: self._parse_models,
            self.COMMAND_MODELS_REFRESH: self._parse_models_refresh,
            self.COMMAND_PURGE: self._parse_purge,
            self.COMMAND_RUN: self._parse_run,
            self.COMMAND_SESSION: self._parse_session,
            self.COMMAND_SETUP: self._parse_setup,
            self.COMMAND_STOP: self._parse_stop,
            self.COMMAND_STOP_ALL: self._parse_stop_all,
            self.COMMAND_TOOL: self._parse_tool,
            self.COMMAND_TOOLS: self._parse_tools,
            self.COMMAND_UNINSTALL: self._parse_uninstall,
            self.COMMAND_UPDATE: self._parse_update,
            self.COMMAND_UPDATE_MODEL: self._parse_update_model,
            self.COMMAND_SET_BASE: self._parse_set_base,
        }

    def parse(self, argv: Sequence[str]) -> CLICommand:
        arguments = list(argv)
        self.verbose = self.OPTION_VERBOSE in arguments
        arguments = [
            argument
            for argument in arguments
            if argument != self.OPTION_VERBOSE
        ]
        if not arguments:
            return TUICommand()

        action = arguments.pop(0)
        command_parser = self.command_parsers.get(action)
        if command_parser is None:
            raise CLIUsageError(
                f"unknown command: {action}. "
                f"Run: {APP_NAME} {self.COMMAND_HELP}"
            )

        return command_parser(arguments)

    @staticmethod
    def _require_no_arguments(action: str, arguments: Sequence[str]) -> None:
        if arguments:
            raise CLIUsageError(
                f"{action} does not accept arguments: {' '.join(arguments)}"
            )

    @staticmethod
    def _parser(prog_suffix: str) -> _ArgumentParser:
        return _ArgumentParser(
            prog=f"{APP_NAME} {prog_suffix}",
            add_help=False,
            allow_abbrev=False,
        )

    def _parse_help(self, arguments: Sequence[str]) -> HelpCommand:
        self._require_no_arguments(self.COMMAND_HELP, arguments)
        return HelpCommand()

    def _parse_agent(self, arguments: Sequence[str]) -> AgentCommand:
        parser = self._parser(self.COMMAND_AGENT)
        parser.add_argument("model", nargs="?")
        parser.add_argument(
            self.OPTION_DIRECTORY,
            self.OPTION_DIRECTORY_SHORT,
            type=Path,
        )
        parser.add_argument(
            self.OPTION_CONTEXT_LENGTH,
            self.OPTION_CONTEXT_LENGTH_SHORT,
        )
        parser.add_argument(
            self.OPTION_EXECUTION_APPROVALS,
            choices=("ask", "auto", "no-ask"),
        )
        parser.add_argument(
            self.OPTION_SESSION,
            self.OPTION_SESSION_SHORT,
            dest="session_name",
        )
        parser.add_argument(
            self.OPTION_INPUT_FILE,
            self.OPTION_INPUT_FILE_SHORT,
            action="append",
            default=[],
            dest="input_files",
        )
        namespace = parser.parse_args(arguments)
        return AgentCommand(
            model=namespace.model,
            directory=namespace.directory,
            context_length=namespace.context_length,
            execution_approvals=namespace.exec,
            session_name=namespace.session_name,
            input_files=tuple(Path(path) for path in namespace.input_files),
        )

    def _parse_chat(self, arguments: Sequence[str]) -> ChatCommand:
        parser = self._parser(self.COMMAND_CHAT)
        parser.add_argument("model", nargs="?")
        parser.add_argument(
            self.OPTION_CONTEXT_LENGTH,
            self.OPTION_CONTEXT_LENGTH_SHORT,
        )
        parser.add_argument(
            self.OPTION_SESSION,
            self.OPTION_SESSION_SHORT,
            dest="session_name",
        )
        parser.add_argument(
            self.OPTION_INPUT_FILE,
            self.OPTION_INPUT_FILE_SHORT,
            action="append",
            default=[],
            dest="input_files",
        )
        namespace = parser.parse_args(arguments)
        return ChatCommand(
            model=namespace.model,
            context_length=namespace.context_length,
            session_name=namespace.session_name,
            input_files=tuple(Path(path) for path in namespace.input_files),
        )

    def _parse_clear_cache(
        self,
        arguments: Sequence[str],
    ) -> ClearCacheCommand:
        self._require_no_arguments(self.COMMAND_CLEAR_CACHE, arguments)
        return ClearCacheCommand()

    def _parse_models_refresh(
        self, arguments: Sequence[str]
    ) -> ModelsRefreshCommand:
        self._require_no_arguments(self.COMMAND_MODELS_REFRESH, arguments)
        return ModelsRefreshCommand()

    def _parse_details(self, arguments: Sequence[str]) -> DetailsCommand:
        parser = self._parser(self.COMMAND_DETAILS)
        parser.add_argument("model")
        namespace = parser.parse_args(arguments)
        return DetailsCommand(model=namespace.model)

    def _parse_version(self, arguments: Sequence[str]) -> VersionCommand:
        self._require_no_arguments(self.COMMAND_VERSION, arguments)
        return VersionCommand()

    def _parse_install(self, arguments: Sequence[str]) -> InstallCommand:
        parser = self._parser(self.COMMAND_INSTALL)
        parser.add_argument("model", nargs="?")
        parser.add_argument(self.OPTION_SOURCE, self.OPTION_SOURCE_SHORT)
        parser.add_argument(
            self.OPTION_BACKEND,
            self.OPTION_BACKEND_SHORT,
            choices=[backend.value for backend in ModelBackend],
            default=ModelBackend.AUTO.value,
        )
        parser.add_argument(
            self.OPTION_TYPE,
            self.OPTION_TYPE_SHORT,
            choices=[source_type.value for source_type in InstallSourceType],
            default=InstallSourceType.AUTO.value,
            dest="source_type",
        )
        namespace = parser.parse_args(arguments)
        if namespace.model and namespace.source:
            raise CLIUsageError("Use either MODEL or --source, not both.")
        if not namespace.model and not namespace.source:
            raise CLIUsageError("Missing model or --source.")
        if (
            namespace.source is None
            and namespace.source_type != InstallSourceType.AUTO.value
        ):
            raise CLIUsageError("--type can only be used with --source.")
        return InstallCommand(
            model=namespace.model,
            source=namespace.source,
            backend=ModelBackend(namespace.backend),
            source_type=InstallSourceType(namespace.source_type),
        )

    def _parse_image(self, arguments: Sequence[str]) -> ImageCommand:
        parser = self._parser(self.COMMAND_IMAGE)
        parser.add_argument("model", nargs="?")
        parser.add_argument(
            self.OPTION_PROMPT,
            self.OPTION_PROMPT_SHORT,
            required=True,
        )
        parser.add_argument(
            self.OPTION_WIDTH,
            self.OPTION_WIDTH_SHORT,
            type=int,
            default=self.DEFAULT_IMAGE_WIDTH,
        )
        parser.add_argument(
            self.OPTION_HEIGHT,
            self.OPTION_HEIGHT_SHORT,
            type=int,
            default=self.DEFAULT_IMAGE_HEIGHT,
        )
        parser.add_argument(
            self.OPTION_OUTPUT_DIRECTORY,
            self.OPTION_OUTPUT_DIRECTORY_SHORT,
            type=Path,
            dest="output_directory",
        )
        parser.add_argument(
            self.OPTION_FILE_NAME,
            self.OPTION_FILE_NAME_SHORT,
            dest="file_name",
        )
        parser.add_argument(
            self.OPTION_INPUT_FILE,
            self.OPTION_INPUT_FILE_SHORT,
            action="append",
            default=[],
            dest="input_files",
        )
        parser.add_argument(self.OPTION_STRENGTH, type=float)
        namespace = parser.parse_args(arguments)
        return ImageCommand(
            model=namespace.model,
            width=namespace.width,
            height=namespace.height,
            output_directory=namespace.output_directory,
            file_name=namespace.file_name,
            prompt=namespace.prompt,
            input_files=tuple(Path(path) for path in namespace.input_files),
            strength=namespace.strength,
        )

    def _parse_models(self, arguments: Sequence[str]) -> ListCommand:
        parser = self._parser(self.COMMAND_MODELS)
        parser.add_argument(
            "target",
            nargs="?",
            choices=[target.value for target in ListTarget],
            default=ListTarget.LOCAL.value,
        )
        parser.add_argument(
            self.OPTION_ORDER,
            self.OPTION_ORDER_SHORT,
            default=self.DEFAULT_LIST_ORDER,
        )
        direction = parser.add_mutually_exclusive_group()
        direction.add_argument(self.OPTION_ASCENDING, action="store_true")
        direction.add_argument(self.OPTION_DESCENDING, action="store_true")
        parser.add_argument(
            self.OPTION_DEPENDENCIES,
            self.OPTION_DEPENDENCIES_SHORT,
            action="store_true",
        )
        namespace = parser.parse_args(arguments)

        order = tuple(
            field.strip()
            for field in namespace.order.split(",")
            if field.strip()
        )
        if not order:
            raise CLIUsageError(
                f"{self.OPTION_ORDER} requires at least one field"
            )

        if namespace.asc:
            sort_direction = SortDirection.ASCENDING
        elif namespace.desc:
            sort_direction = SortDirection.DESCENDING
        else:
            sort_direction = SortDirection.AUTO

        return ListCommand(
            target=ListTarget(namespace.target),
            order=order,
            direction=sort_direction,
            dependencies=namespace.dependencies,
        )

    def _parse_purge(self, arguments: Sequence[str]) -> PurgeCommand:
        parser = self._parser(self.COMMAND_PURGE)
        parser.add_argument(
            "component",
            nargs="?",
            choices=[component.value for component in PurgeComponent],
        )
        namespace = parser.parse_args(arguments)
        return PurgeCommand(
            component=(
                PurgeComponent(namespace.component)
                if namespace.component is not None
                else None
            )
        )

    def _parse_run(self, arguments: Sequence[str]) -> RunCommand:
        parser = self._parser(self.COMMAND_RUN)
        parser.add_argument("model", nargs="?")
        parser.add_argument(
            self.OPTION_CONTEXT_LENGTH,
            self.OPTION_CONTEXT_LENGTH_SHORT,
            default=DEFAULT_CONTEXT_LENGTH,
        )
        namespace = parser.parse_args(arguments)
        return RunCommand(
            model=namespace.model,
            context_length=namespace.context_length,
        )

    def _parse_session(self, arguments: Sequence[str]) -> SessionCommand:
        parser = self._parser(self.COMMAND_SESSION)
        parser.add_argument("session", nargs="?")
        action = parser.add_mutually_exclusive_group()
        action.add_argument(
            self.OPTION_DELETE,
            self.OPTION_DELETE_SHORT,
            action="store_true",
        )
        action.add_argument(
            self.OPTION_RENAME,
            self.OPTION_RENAME_SHORT,
            dest="new_name",
        )
        namespace = parser.parse_args(arguments)
        if (namespace.delete or namespace.new_name is not None) and not namespace.session:
            raise CLIUsageError(
                f"{self.COMMAND_SESSION} requires SESSION when using "
                f"{self.OPTION_DELETE} or {self.OPTION_RENAME}"
            )
        return SessionCommand(
            session=namespace.session,
            delete=namespace.delete,
            new_name=namespace.new_name,
        )

    def _parse_setup(self, arguments: Sequence[str]) -> SetupCommand:
        parser = self._parser(self.COMMAND_SETUP)
        parser.add_argument(
            "component",
            nargs="?",
            choices=[component.value for component in SetupComponent],
        )
        namespace = parser.parse_args(arguments)
        return SetupCommand(
            component=(
                SetupComponent(namespace.component)
                if namespace.component is not None
                else None
            )
        )

    def _parse_stop(self, arguments: Sequence[str]) -> StopCommand:
        parser = self._parser(self.COMMAND_STOP)
        parser.add_argument("model", nargs="?")
        namespace = parser.parse_args(arguments)
        return StopCommand(model=namespace.model)

    def _parse_stop_all(self, arguments: Sequence[str]) -> StopAllCommand:
        self._require_no_arguments(self.COMMAND_STOP_ALL, arguments)
        return StopAllCommand()

    def _parse_tool(self, arguments: Sequence[str]) -> ToolCommand:
        parser = self._parser(self.COMMAND_TOOL)
        parser.add_argument("tool")
        state = parser.add_mutually_exclusive_group(required=True)
        state.add_argument(
            self.OPTION_ENABLE,
            self.OPTION_ENABLE_SHORT,
            action="store_true",
        )
        state.add_argument(
            self.OPTION_DISABLE,
            self.OPTION_DISABLE_SHORT,
            action="store_true",
        )
        namespace = parser.parse_args(arguments)
        return ToolCommand(tool=namespace.tool, enabled=namespace.enable)

    def _parse_tools(self, arguments: Sequence[str]) -> ToolsCommand:
        self._require_no_arguments(self.COMMAND_TOOLS, arguments)
        return ToolsCommand()

    def _parse_uninstall(
        self,
        arguments: Sequence[str],
    ) -> UninstallCommand:
        parser = self._parser(self.COMMAND_UNINSTALL)
        parser.add_argument("model")
        parser.add_argument(
            self.OPTION_DEPENDENCIES,
            self.OPTION_DEPENDENCIES_SHORT,
            choices=("keep", "unused", "all"),
            default="unused",
            dest="dependency_mode",
        )
        namespace = parser.parse_args(arguments)
        return UninstallCommand(
            model=namespace.model,
            dependency_mode=namespace.dependency_mode,
        )

    def _parse_update(self, arguments: Sequence[str]) -> UpdateCommand:
        parser = self._parser(self.COMMAND_UPDATE)
        parser.add_argument(
            "component",
            nargs="?",
            choices=[component.value for component in SetupComponent],
        )
        namespace = parser.parse_args(arguments)
        return UpdateCommand(
            component=(
                SetupComponent(namespace.component)
                if namespace.component is not None
                else None
            )
        )

    def _parse_update_model(
        self, arguments: Sequence[str]
    ) -> UpdateModelCommand:
        parser = self._parser(self.COMMAND_UPDATE_MODEL)
        parser.add_argument("model")
        namespace = parser.parse_args(arguments)
        return UpdateModelCommand(model=namespace.model)

    def _parse_set_base(self, arguments: Sequence[str]) -> SetBaseCommand:
        parser = self._parser(self.COMMAND_SET_BASE)
        parser.add_argument("model")
        namespace = parser.parse_args(arguments)
        return SetBaseCommand(model=namespace.model)

    @classmethod
    def usage(cls) -> str:
        return build_help_text()
