from typing import Any

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.agent_command_handler import AgentCommandHandler
from ai_models_manager.console.handlers.chat_command_handler import ChatCommandHandler
from ai_models_manager.console.handlers.clear_cache_command_handler import ClearCacheCommandHandler
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.console.handlers.details_command_handler import DetailsCommandHandler
from ai_models_manager.console.handlers.help_command_handler import HelpCommandHandler
from ai_models_manager.console.handlers.image_command_handler import ImageCommandHandler
from ai_models_manager.console.handlers.install_command_handler import InstallCommandHandler
from ai_models_manager.console.handlers.models_command_handler import ModelsCommandHandler
from ai_models_manager.console.handlers.models_refresh_command_handler import ModelsRefreshCommandHandler
from ai_models_manager.console.handlers.purge_command_handler import PurgeCommandHandler
from ai_models_manager.console.handlers.run_command_handler import RunCommandHandler
from ai_models_manager.console.handlers.session_command_handler import SessionCommandHandler
from ai_models_manager.console.handlers.set_base_command_handler import SetBaseCommandHandler
from ai_models_manager.console.handlers.setup_command_handler import SetupCommandHandler
from ai_models_manager.console.handlers.stop_all_command_handler import StopAllCommandHandler
from ai_models_manager.console.handlers.stop_command_handler import StopCommandHandler
from ai_models_manager.console.handlers.tool_command_handler import ToolCommandHandler
from ai_models_manager.console.handlers.tools_command_handler import ToolsCommandHandler
from ai_models_manager.console.handlers.tui_command_handler import TUICommandHandler
from ai_models_manager.console.handlers.uninstall_command_handler import UninstallCommandHandler
from ai_models_manager.console.handlers.update_command_handler import UpdateCommandHandler
from ai_models_manager.console.handlers.update_model_command_handler import UpdateModelCommandHandler
from ai_models_manager.console.handlers.version_command_handler import VersionCommandHandler
from ai_models_manager.console.local_models_service import LocalModelsService
from ai_models_manager.console.model_presentation_service import ModelPresentationService
from ai_models_manager.console.ollama_command_support import OllamaCommandSupport
from ai_models_manager.console.process_runner import ProcessRunner
from ai_models_manager.console.tui_command_executor import TUICommandExecutor
from ai_models_manager.core.agent.agent_service import AgentService
from ai_models_manager.core.agent.codex_backend import CodexBackend
from ai_models_manager.core.agent.tool_service import ToolService
from ai_models_manager.core.chat.chat_service import ChatService
from ai_models_manager.core.draw_things.draw_things_backend import DrawThingsBackend
from ai_models_manager.core.disk_space_service import DiskSpaceService
from ai_models_manager.core.hardware_service import HardwareService
from ai_models_manager.core.image_service import ImageService
from ai_models_manager.core.input_file_service import InputFileService
from ai_models_manager.core.model_metadata_service import ModelMetadataService
from ai_models_manager.core.ollama.ollama_backend import OllamaBackend
from ai_models_manager.core.purge_service import PurgeService
from ai_models_manager.core.session.session_manager import SessionManager
from ai_models_manager.core.setup_service import SetupService
from ai_models_manager.core.storage.cache_storage import CacheStorage
from ai_models_manager.core.storage.session_storage import SessionStorage
from ai_models_manager.core.storage.settings_storage import SettingsStorage
from ai_models_manager.core.storage.tool_settings_storage import ToolSettingsStorage
from ai_models_manager.core.version_service import VersionService
from ai_models_manager.enums.exit_code import ExitCode
from ai_models_manager.enums.list_target import ListTarget
from ai_models_manager.views.agent_options_view import AgentOptionsView
from ai_models_manager.views.agent_tools_view import AgentToolsView
from ai_models_manager.views.dependencies_view import DependenciesView
from ai_models_manager.views.catalog_models_view import CatalogModelsView
from ai_models_manager.views.catalog_model_actions_view import CatalogModelActionsView
from ai_models_manager.views.chat_options_view import ChatOptionsView
from ai_models_manager.views.component_selection_view import (
    ComponentSelectionView,
)
from ai_models_manager.views.component_checklist_view import ComponentChecklistView
from ai_models_manager.views.dialog import Dialog
from ai_models_manager.views.help_view import HelpView
from ai_models_manager.views.install_file_view import InstallFileView
from ai_models_manager.views.directory_selection_view import DirectorySelectionView
from ai_models_manager.views.install_models_menu_view import InstallModelsMenuView
from ai_models_manager.views.install_confirmation_view import (
    InstallConfirmationView,
)
from ai_models_manager.views.install_source_confirmation_view import (
    InstallSourceConfirmationView,
)
from ai_models_manager.views.install_source_option_view import (
    InstallSourceOptionView,
)
from ai_models_manager.views.install_source_view import InstallSourceView
from ai_models_manager.views.image_options_view import ImageOptionsView
from ai_models_manager.views.input_files_editor_view import InputFilesEditorView
from ai_models_manager.views.local_models_view import LocalModelsView
from ai_models_manager.views.main_menu_view import MainMenuView
from ai_models_manager.views.model_details_view import ModelDetailsView
from ai_models_manager.views.model_filter_view import ModelFilterView
from ai_models_manager.views.model_options_view import ModelOptionsView
from ai_models_manager.views.model_sort_view import ModelSortView
from ai_models_manager.views.models_menu_view import ModelsMenuView
from ai_models_manager.views.system_confirmation_view import (
    SystemConfirmationView,
)
from ai_models_manager.views.system_menu_view import SystemMenuView
from ai_models_manager.views.uninstall_confirmation_view import (
    UninstallConfirmationView,
)
from ai_models_manager.views.uninstall_dependency_mode_view import (
    UninstallDependencyModeView,
)
from ai_models_manager.views.version_view import VersionView


class CLICommands:
    """Dispatch parsed DTOs to their application-level command handlers."""

    def __init__(
        self,
        console: Console,
        settings_storage: SettingsStorage,
        ollama: OllamaBackend,
        cache_storage: CacheStorage | None = None,
        agent_service: AgentService | None = None,
        chat_service: ChatService | None = None,
        codex: CodexBackend | None = None,
        metadata_service: ModelMetadataService | None = None,
        purge_service: PurgeService | None = None,
        process_runner: ProcessRunner | None = None,
        draw_things: DrawThingsBackend | None = None,
        disk_space_service: DiskSpaceService | None = None,
        hardware_service: HardwareService | None = None,
        input_file_service: InputFileService | None = None,
        image_service: ImageService | None = None,
        session_manager: SessionManager | None = None,
        session_storage: SessionStorage | None = None,
        setup_service: SetupService | None = None,
        tool_service: ToolService | None = None,
        tool_settings_storage: ToolSettingsStorage | None = None,
        version_service: VersionService | None = None,
    ) -> None:
        self.console = console
        self.process_runner = process_runner or ProcessRunner(console.debug)
        self.settings_storage = settings_storage
        self.ollama = ollama
        self.cache_storage = cache_storage or CacheStorage()
        self.session_storage = session_storage or SessionStorage()
        self.session_manager = session_manager or SessionManager(
            self.session_storage
        )
        self.setup_service = setup_service or SetupService(self.process_runner)
        self.codex = codex or CodexBackend(
            self.process_runner, self.ollama.base_url
        )
        self.tool_settings_storage = (
            tool_settings_storage or ToolSettingsStorage()
        )
        self.tool_service = tool_service or ToolService(
            self.tool_settings_storage
        )
        self.agent_service = agent_service or AgentService(
            self.codex,
            self.ollama,
            self.session_manager,
            self.session_storage,
            self.tool_service,
        )
        self.chat_service = chat_service or ChatService(
            self.ollama, self.session_storage, self.console.warning
        )
        self.input_file_service = input_file_service or InputFileService(
            self.process_runner
        )
        self.hardware_service = hardware_service or HardwareService(
            self.process_runner
        )
        self.hardware = None
        self.metadata_service = metadata_service
        self.draw_things = draw_things or DrawThingsBackend(
            self.process_runner, cache_directory=self.cache_storage.directory
        )
        self.disk_space_service = disk_space_service or DiskSpaceService()
        self.image_service = image_service or ImageService(
            self.ollama, self.draw_things, self.settings_storage
        )
        self.purge_service = purge_service or PurgeService(
            self.process_runner,
            self.ollama,
            self.draw_things,
            self.settings_storage,
        )
        self.version_service = version_service or VersionService(
            self.process_runner, self.draw_things
        )
        self.model_presentation = ModelPresentationService(
            self.ollama,
            self.draw_things,
            self.hardware_service,
            self.metadata_service,
        )
        self.local_models_service = LocalModelsService(
            self.ollama,
            self.draw_things,
            self.model_presentation,
        )
        self.ollama_support = OllamaCommandSupport(
            self.console,
            self.ollama,
            self.settings_storage,
        )
        self.dialog = Dialog(self.process_runner)
        self.help_view = HelpView(self.dialog)
        self.agent_options_view = AgentOptionsView(self.dialog)
        self.agent_tools_view = AgentToolsView(self.dialog)
        self.catalog_models_views = {
            ListTarget.DRAW_THINGS: CatalogModelsView(
                self.dialog, "Draw Things Models"
            ),
            ListTarget.OLLAMA: CatalogModelsView(
                self.dialog, "Ollama Models"
            ),
            ListTarget.OLLAMA_EXPERIMENTAL: CatalogModelsView(
                self.dialog, "Ollama Models Experimental"
            ),
        }
        self.catalog_model_actions_view = CatalogModelActionsView(self.dialog)
        self.chat_options_view = ChatOptionsView(self.dialog)
        self.component_checklist_view = ComponentChecklistView(self.dialog)
        self.component_selection_view = ComponentSelectionView(self.dialog)
        self.dependencies_view = DependenciesView(self.dialog)
        self.directory_selection_view = DirectorySelectionView(self.dialog)
        self.install_file_view = InstallFileView(self.dialog)
        self.install_models_menu_view = InstallModelsMenuView(self.dialog)
        self.install_confirmation_view = InstallConfirmationView(self.dialog)
        self.install_source_confirmation_view = InstallSourceConfirmationView(
            self.dialog
        )
        self.install_source_option_view = InstallSourceOptionView(self.dialog)
        self.install_source_view = InstallSourceView(self.dialog)
        self.image_options_view = ImageOptionsView(self.dialog)
        self.input_files_editor_view = InputFilesEditorView(self.dialog)
        self.local_models_view = LocalModelsView(self.dialog)
        self.main_menu_view = MainMenuView(self.dialog)
        self.model_details_view = ModelDetailsView(self.dialog)
        self.model_filter_view = ModelFilterView(self.dialog)
        self.model_options_view = ModelOptionsView(self.dialog)
        self.model_sort_view = ModelSortView(self.dialog)
        self.models_menu_view = ModelsMenuView(self.dialog)
        self.system_confirmation_view = SystemConfirmationView(self.dialog)
        self.system_menu_view = SystemMenuView(self.dialog)
        self.uninstall_confirmation_view = UninstallConfirmationView(
            self.dialog
        )
        self.uninstall_dependency_mode_view = UninstallDependencyModeView(
            self.dialog
        )
        self.version_view = VersionView(self.dialog)
        self.tui_command_executor = TUICommandExecutor(
            self.console,
            self.execute,
        )
        handlers: tuple[CommandHandler[Any], ...] = (
            AgentCommandHandler(
                self.console,
                self.ollama,
                self.codex,
                self.agent_service,
                self.session_manager,
                self.session_storage,
                self.ollama_support,
            ),
            ChatCommandHandler(
                self.console,
                self.ollama,
                self.chat_service,
                self.input_file_service,
                self.session_manager,
                self.session_storage,
                self.ollama_support,
            ),
            ClearCacheCommandHandler(self.console, self.cache_storage),
            DetailsCommandHandler(
                self.console,
                self.ollama,
                self.draw_things,
                self.model_presentation,
                self.ollama_support,
            ),
            HelpCommandHandler(self.console),
            ImageCommandHandler(self.console, self.image_service),
            InstallCommandHandler(
                self.console,
                self.ollama,
                self.draw_things,
                self.ollama_support,
                self.disk_space_service,
            ),
            ModelsCommandHandler(
                self.console,
                self.settings_storage,
                self.ollama,
                self.draw_things,
                self.hardware_service,
                self.local_models_service,
                self.model_presentation,
                self.ollama_support,
            ),
            ModelsRefreshCommandHandler(
                self.console, self.ollama, self.draw_things
            ),
            PurgeCommandHandler(self.console, self.purge_service),
            RunCommandHandler(
                self.console, self.ollama, self.ollama_support
            ),
            SessionCommandHandler(
                self.console, self.codex, self.session_storage
            ),
            SetBaseCommandHandler(
                self.console,
                self.ollama,
                self.settings_storage,
                self.ollama_support,
            ),
            SetupCommandHandler(self.console, self.setup_service),
            StopAllCommandHandler(
                self.console, self.ollama, self.ollama_support
            ),
            StopCommandHandler(
                self.console, self.ollama, self.ollama_support
            ),
            ToolCommandHandler(self.console, self.tool_service),
            ToolsCommandHandler(
                self.console,
                self.tool_service,
                self.tool_settings_storage,
            ),
            TUICommandHandler(
                self.console,
                self.agent_options_view,
                self.agent_tools_view,
                self.catalog_model_actions_view,
                self.catalog_models_views,
                self.chat_options_view,
                self.component_checklist_view,
                self.component_selection_view,
                self.dependencies_view,
                self.directory_selection_view,
                self.dialog,
                self.help_view,
                self.install_file_view,
                self.install_confirmation_view,
                self.install_models_menu_view,
                self.install_source_confirmation_view,
                self.install_source_option_view,
                self.install_source_view,
                self.image_options_view,
                self.input_files_editor_view,
                self.local_models_service,
                self.local_models_view,
                self.main_menu_view,
                self.model_details_view,
                self.model_filter_view,
                self.model_options_view,
                self.model_sort_view,
                self.models_menu_view,
                self.settings_storage,
                self.system_confirmation_view,
                self.system_menu_view,
                self.tool_service,
                self.tui_command_executor,
                self.uninstall_confirmation_view,
                self.uninstall_dependency_mode_view,
                self.version_service,
                self.version_view,
            ),
            UninstallCommandHandler(
                self.console,
                self.ollama,
                self.draw_things,
                self.settings_storage,
                self.ollama_support,
            ),
            UpdateCommandHandler(self.console, self.setup_service),
            UpdateModelCommandHandler(
                self.console,
                self.ollama,
                self.draw_things,
                self.ollama_support,
            ),
            VersionCommandHandler(self.console, self.version_service),
        )
        self.handlers = {
            handler.command_type: handler for handler in handlers
        }

    def execute(self, command: CLICommand) -> ExitCode:
        handler = self.handlers.get(type(command))
        if handler is None:
            raise AssertionError(f"Unhandled command DTO: {command!r}")
        return handler.handle(command)
