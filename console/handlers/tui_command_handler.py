from dataclasses import replace
from pathlib import Path
from typing import Callable, ClassVar, Mapping

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.agent_command import AgentCommand
from ai_models_manager.console.commands.chat_command import ChatCommand
from ai_models_manager.console.commands.install_command import InstallCommand
from ai_models_manager.console.commands.image_command import ImageCommand
from ai_models_manager.console.commands.help_command import HelpCommand
from ai_models_manager.console.commands.purge_command import PurgeCommand
from ai_models_manager.console.commands.setup_command import SetupCommand
from ai_models_manager.console.commands.run_command import RunCommand
from ai_models_manager.console.commands.set_base_command import SetBaseCommand
from ai_models_manager.console.commands.stop_command import StopCommand
from ai_models_manager.console.commands.tool_command import ToolCommand
from ai_models_manager.console.commands.update_command import UpdateCommand
from ai_models_manager.console.commands.update_model_command import UpdateModelCommand
from ai_models_manager.console.commands.models_refresh_command import ModelsRefreshCommand
from ai_models_manager.console.commands.tui_command import TUICommand
from ai_models_manager.console.commands.uninstall_command import (
    UninstallCommand,
)
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.console.local_models_service import LocalModelsService
from ai_models_manager.console.tui_command_executor import TUICommandExecutor
from ai_models_manager.config import (
    DEFAULT_CONTEXT_LENGTH,
    DEFAULT_IMAGE_HEIGHT,
    DEFAULT_IMAGE_WIDTH,
)
from ai_models_manager.core.storage.settings_storage import SettingsStorage
from ai_models_manager.core.version_service import VersionService
from ai_models_manager.core.agent.tool_service import ToolService
from ai_models_manager.enums.exit_code import ExitCode
from ai_models_manager.enums.list_target import ListTarget
from ai_models_manager.enums.model_backend import ModelBackend
from ai_models_manager.enums.purge_component import PurgeComponent
from ai_models_manager.enums.setup_component import SetupComponent
from ai_models_manager.enums.install_source_type import InstallSourceType
from ai_models_manager.exceptions.cli_error import CLIError
from ai_models_manager.models.local_model import LocalModel
from ai_models_manager.models.component_version_data_model import (
    ComponentVersionDataModel,
)
from ai_models_manager.views.dependencies_view import DependenciesView
from ai_models_manager.views.directory_selection_view import DirectorySelectionView
from ai_models_manager.views.agent_option_item import AgentOptionItem
from ai_models_manager.views.chat_option_item import ChatOptionItem
from ai_models_manager.views.catalog_models_view import CatalogModelsView
from ai_models_manager.views.catalog_model_action_item import CatalogModelActionItem
from ai_models_manager.views.catalog_model_actions_view import CatalogModelActionsView
from ai_models_manager.views.agent_options_view import AgentOptionsView
from ai_models_manager.views.agent_tools_view import AgentToolsView
from ai_models_manager.views.dtos.agent_tools_dto import (
    AgentToolDto,
    AgentToolsDto,
)
from ai_models_manager.views.dtos.agent_options_dto import AgentOptionsDto
from ai_models_manager.views.chat_options_view import ChatOptionsView
from ai_models_manager.views.component_selection_view import ComponentSelectionView
from ai_models_manager.views.component_checklist_view import ComponentChecklistView
from ai_models_manager.views.dtos.component_checklist_dto import ComponentChecklistDto
from ai_models_manager.views.dtos.directory_selection_dto import DirectorySelectionDto
from ai_models_manager.views.dtos.component_selection_dto import (
    ComponentSelectionDto,
)
from ai_models_manager.views.dtos.chat_options_dto import ChatOptionsDto
from ai_models_manager.views.dialog import Dialog
from ai_models_manager.views.dtos.install_models_menu_dto import (
    InstallModelsMenuDto,
)
from ai_models_manager.views.dtos.install_confirmation_dto import (
    InstallConfirmationDto,
)
from ai_models_manager.views.dtos.install_source_confirmation_dto import (
    InstallSourceConfirmationDto,
)
from ai_models_manager.views.dtos.install_source_dto import InstallSourceDto
from ai_models_manager.views.dtos.install_source_option_dto import (
    InstallSourceOptionDto,
)
from ai_models_manager.views.dtos.local_models_dto import LocalModelsDto
from ai_models_manager.views.dtos.catalog_model_actions_dto import CatalogModelActionsDto
from ai_models_manager.views.dtos.main_menu_dto import MainMenuDto
from ai_models_manager.views.dtos.model_details_dto import ModelDetailsDto
from ai_models_manager.views.dtos.model_options_dto import ModelOptionsDto
from ai_models_manager.views.dtos.model_sort_dto import ModelSortDto
from ai_models_manager.views.dtos.model_filter_dto import ModelFilterDto
from ai_models_manager.views.dtos.models_menu_dto import ModelsMenuDto
from ai_models_manager.views.dtos.uninstall_confirmation_dto import (
    UninstallConfirmationDto,
)
from ai_models_manager.views.dtos.uninstall_dependency_mode_dto import (
    UninstallDependencyModeDto,
)
from ai_models_manager.views.install_models_menu_item import (
    InstallModelsMenuItem,
)
from ai_models_manager.views.install_models_menu_view import (
    InstallModelsMenuView,
)
from ai_models_manager.views.install_confirmation_view import (
    InstallConfirmationView,
)
from ai_models_manager.views.install_source_confirmation_view import (
    InstallSourceConfirmationView,
)
from ai_models_manager.views.install_source_option_item import (
    InstallSourceOptionItem,
)
from ai_models_manager.views.install_source_option_view import (
    InstallSourceOptionView,
)
from ai_models_manager.views.install_source_view import InstallSourceView
from ai_models_manager.views.install_file_view import InstallFileView
from ai_models_manager.views.help_view import HelpView
from ai_models_manager.views.image_options_view import ImageOptionsView
from ai_models_manager.views.image_option_item import ImageOptionItem
from ai_models_manager.views.dtos.image_options_dto import ImageOptionsDto
from ai_models_manager.views.dtos.input_files_editor_dto import (
    InputFilesEditorDto,
)
from ai_models_manager.views.input_files_editor_view import InputFilesEditorView
from ai_models_manager.views.local_models_view import LocalModelsView
from ai_models_manager.views.main_menu_item import MainMenuItem
from ai_models_manager.views.main_menu_view import MainMenuView
from ai_models_manager.views.model_details_view import ModelDetailsView
from ai_models_manager.views.model_filter_item import ModelFilterItem
from ai_models_manager.views.model_filter_view import ModelFilterView
from ai_models_manager.views.model_option_item import ModelOptionItem
from ai_models_manager.views.model_options_view import ModelOptionsView
from ai_models_manager.views.model_sort_view import ModelSortView
from ai_models_manager.views.models_menu_item import ModelsMenuItem
from ai_models_manager.views.models_menu_view import ModelsMenuView
from ai_models_manager.views.models.model_filters import ModelFilters
from ai_models_manager.views.dtos.system_confirmation_dto import (
    SystemConfirmationDto,
)
from ai_models_manager.views.dtos.system_menu_dto import SystemMenuDto
from ai_models_manager.views.system_confirmation_view import (
    SystemConfirmationView,
)
from ai_models_manager.views.system_menu_item import SystemMenuItem
from ai_models_manager.views.system_menu_view import SystemMenuView
from ai_models_manager.views.uninstall_confirmation_view import (
    UninstallConfirmationView,
)
from ai_models_manager.views.uninstall_dependency_mode_item import (
    UninstallDependencyModeItem,
)
from ai_models_manager.views.uninstall_dependency_mode_view import (
    UninstallDependencyModeView,
)
from ai_models_manager.views.version_view import VersionView
from ai_models_manager.views.dtos.version_dto import VersionDto


class TUICommandHandler(CommandHandler[TUICommand]):
    """Run the dialog TUI navigation loop."""

    command_type: ClassVar[type[CLICommand]] = TUICommand

    def __init__(
        self,
        console: Console,
        agent_options_view: AgentOptionsView,
        agent_tools_view: AgentToolsView,
        catalog_model_actions_view: CatalogModelActionsView,
        catalog_models_views: Mapping[ListTarget, CatalogModelsView],
        chat_options_view: ChatOptionsView,
        component_checklist_view: ComponentChecklistView,
        component_selection_view: ComponentSelectionView,
        dependencies_view: DependenciesView,
        directory_selection_view: DirectorySelectionView,
        dialog: Dialog,
        help_view: HelpView,
        install_file_view: InstallFileView,
        install_confirmation_view: InstallConfirmationView,
        install_models_menu_view: InstallModelsMenuView,
        install_source_confirmation_view: InstallSourceConfirmationView,
        install_source_option_view: InstallSourceOptionView,
        install_source_view: InstallSourceView,
        image_options_view: ImageOptionsView,
        input_files_editor_view: InputFilesEditorView,
        local_models_service: LocalModelsService,
        local_models_view: LocalModelsView,
        main_menu_view: MainMenuView,
        model_details_view: ModelDetailsView,
        model_filter_view: ModelFilterView,
        model_options_view: ModelOptionsView,
        model_sort_view: ModelSortView,
        models_menu_view: ModelsMenuView,
        settings_storage: SettingsStorage,
        system_confirmation_view: SystemConfirmationView,
        system_menu_view: SystemMenuView,
        tool_service: ToolService,
        tui_command_executor: TUICommandExecutor,
        uninstall_confirmation_view: UninstallConfirmationView,
        uninstall_dependency_mode_view: UninstallDependencyModeView,
        version_service: VersionService,
        version_view: VersionView,
    ) -> None:
        self.console = console
        self.agent_options_view = agent_options_view
        self.agent_tools_view = agent_tools_view
        self.catalog_model_actions_view = catalog_model_actions_view
        self.catalog_models_views = catalog_models_views
        self.chat_options_view = chat_options_view
        self.component_checklist_view = component_checklist_view
        self.component_selection_view = component_selection_view
        self.dependencies_view = dependencies_view
        self.directory_selection_view = directory_selection_view
        self.dialog = dialog
        self.help_view = help_view
        self.install_file_view = install_file_view
        self.install_confirmation_view = install_confirmation_view
        self.install_models_menu_view = install_models_menu_view
        self.install_source_confirmation_view = (
            install_source_confirmation_view
        )
        self.install_source_option_view = install_source_option_view
        self.install_source_view = install_source_view
        self.image_options_view = image_options_view
        self.input_files_editor_view = input_files_editor_view
        self.local_models_service = local_models_service
        self.local_models_view = local_models_view
        self.main_menu_view = main_menu_view
        self.model_details_view = model_details_view
        self.model_filter_view = model_filter_view
        self.model_options_view = model_options_view
        self.model_sort_view = model_sort_view
        self.models_menu_view = models_menu_view
        self.settings_storage = settings_storage
        self.system_confirmation_view = system_confirmation_view
        self.system_menu_view = system_menu_view
        self.tool_service = tool_service
        self.tui_command_executor = tui_command_executor
        self.uninstall_confirmation_view = uninstall_confirmation_view
        self.uninstall_dependency_mode_view = uninstall_dependency_mode_view
        self.version_service = version_service
        self.version_view = version_view

    def handle(self, command: TUICommand) -> ExitCode:
        if not self.dialog.is_available():
            raise CLIError(
                "The dialog TUI is not installed. Run: ai --setup",
                ExitCode.ERROR,
            )
        if not self._is_interactive_terminal():
            raise CLIError(
                "The dialog TUI requires an interactive terminal.",
                ExitCode.ERROR,
            )

        default_item: MainMenuItem | None = None
        try:
            while True:
                result = self.main_menu_view.render(
                    MainMenuDto(default_item=default_item)
                )
                selected = result.selected_item
                if result.cancelled or selected is MainMenuItem.EXIT:
                    return ExitCode.SUCCESS
                if selected is None:
                    raise CLIError(
                        "The main dialog menu returned an unexpected result "
                        f"(exit code {result.dialog_result.exit_code}).",
                        ExitCode.ERROR,
                    )
                default_item = selected
                if selected is MainMenuItem.AGENT:
                    self._run_agent_view()
                    continue
                if selected is MainMenuItem.MODELS:
                    self._run_models_menu()
                    continue
                if selected is MainMenuItem.CHAT:
                    self._run_chat_view()
                    continue
                if selected is MainMenuItem.IMAGE:
                    self._run_image_view()
                    continue
                if selected is MainMenuItem.SYSTEM:
                    if self._run_system_menu():
                        return ExitCode.SUCCESS
                    continue
                if selected is MainMenuItem.HELP:
                    result = self.tui_command_executor.run(HelpCommand())
                    self.help_view.render(result.output)
                    continue
                if selected is MainMenuItem.VERSION:
                    self._run_version_view()
                    continue
                raise CLIError(
                    f"Unsupported main menu selection: {selected.value}.",
                    ExitCode.ERROR,
                )
        finally:
            try:
                if self.dialog.is_available():
                    self.dialog.clear()
            finally:
                self.console.restore_terminal_mode()
                self.console.clear_screen()

    def _run_system_menu(self) -> bool:
        default_item: SystemMenuItem | None = None
        while True:
            result = self.system_menu_view.render(
                SystemMenuDto(default_item=default_item)
            )
            if result.cancelled:
                return False
            if result.selected_item is None:
                raise CLIError(
                    "The System menu returned an unexpected result "
                    f"(exit code {result.dialog_result.exit_code}).",
                    ExitCode.ERROR,
                )
            default_item = result.selected_item
            if result.selected_item is SystemMenuItem.TOOLS:
                self._run_agent_tools_view()
                continue
            if result.selected_item is SystemMenuItem.SETUP:
                self._run_setup_view()
                continue
            if result.selected_item is SystemMenuItem.UPDATE:
                self._run_update_view()
                continue
            if result.selected_item is SystemMenuItem.PURGE:
                self._run_purge_view()
                if not self.dialog.is_available():
                    return True

    def _show_command_output(self, title: str, command: CLICommand) -> None:
        result = self.tui_command_executor.run(command)
        self.dialog.render(
            (
                "--title",
                title,
                "--scrolltext",
                "--msgbox",
                result.output,
                "0",
                "0",
            )
        )

    def _run_version_view(self) -> None:
        self.dialog.render(
            (
                "--title",
                "Version",
                "--infobox",
                "\nCollecting component information ...\n",
                "5",
                "40",
            )
        )
        self.version_view.render(
            VersionDto(
                components=self.version_service.components(),
                model_storage=self.version_service.model_storage(),
            )
        )

    def _run_update_view(self) -> None:
        rows = self._component_version_rows("Update")
        selection = self.component_checklist_view.render(
            ComponentChecklistDto(
                title="Update",
                headers=("Component", "Current", "Available"),
                components=tuple(
                    (
                        component.value,
                        (
                            self._component_label(component.value),
                            rows[component].version,
                            rows[component].update,
                        ),
                        rows[component].update != "-",
                    )
                    for component in SetupComponent
                ),
            )
        )
        if selection.cancelled or not selection.components:
            return
        components = tuple(
            component
            for component in SetupComponent
            if component.value in selection.components
        )
        if not self._confirm_components("Update", components):
            return
        for component in components:
            self._run_terminal_command(
                f"Update {self._component_label(component.value)}",
                UpdateCommand(component=component),
            )

    def _run_setup_view(self) -> None:
        rows = self._component_version_rows("Setup")
        selection = self.component_checklist_view.render(
            ComponentChecklistDto(
                title="Setup",
                headers=("Component", "Current"),
                components=tuple(
                    (
                        component.value,
                        (
                            self._component_label(component.value),
                            rows[component].version,
                        ),
                        rows[component].version
                        == self.version_service.NOT_INSTALLED,
                    )
                    for component in SetupComponent
                ),
            )
        )
        if selection.cancelled or not selection.components:
            return
        components = tuple(
            component
            for component in SetupComponent
            if component.value in selection.components
        )
        if not self._confirm_components("Setup", components):
            return
        for component in components:
            self._run_terminal_command(
                f"Setup {self._component_label(component.value)}",
                SetupCommand(component=component),
            )

    def _run_purge_view(self) -> bool:
        component_rows = self._component_version_rows("Purge")
        storage_rows = {
            row.component: row.size
            for row in self.version_service.model_storage()
        }
        purge_components = (
            PurgeComponent.CODEX,
            PurgeComponent.DRAW_THINGS_CLI,
            PurgeComponent.DRAW_THINGS_MODELS,
            PurgeComponent.MODELS,
            PurgeComponent.NPM,
            PurgeComponent.OLLAMA,
            PurgeComponent.DIALOG,
        )
        selection = self.component_checklist_view.render(
            ComponentChecklistDto(
                title="Purge",
                headers=("Component", "Version", "Size"),
                components=tuple(
                    (
                        component.value,
                        self._purge_component_cells(
                            component, component_rows, storage_rows
                        ),
                        False,
                    )
                    for component in purge_components
                ),
            )
        )
        if selection.cancelled or not selection.components:
            return False
        components = tuple(
            component
            for component in purge_components
            if component.value in selection.components
        )
        if not self._confirm_system_action(
            "Confirm Purge",
            "Remove the selected components and model data?\n\n"
            + "\n".join(
                f"  - {self._component_label(component.value)}"
                for component in components
            )
            + "\n\nThis operation cannot be undone.",
            "Purge",
        ):
            return False
        self.dialog.clear()
        self.console.restore_terminal_mode()
        self.console.clear_screen()
        self.console.write("Purge", style="heading")
        self.console.blank_line()
        succeeded = True
        for component in components:
            result = self.tui_command_executor.run_interactive(
                PurgeCommand(component=component, confirmed=True)
            )
            succeeded = result.succeeded and succeeded
        self.console.restore_terminal_mode()
        if self.dialog.is_available():
            self.console.blank_line()
            self.console.wait_for_key(
                "Press any key to return to the System menu..."
            )
        return succeeded

    def _component_version_rows(
        self, title: str
    ) -> dict[SetupComponent, ComponentVersionDataModel]:
        self.dialog.render(
            (
                "--title",
                title,
                "--infobox",
                "\nCollecting component information ...\n",
                "5",
                "40",
            )
        )
        rows_by_name = {
            row.component.casefold(): row
            for row in self.version_service.components()
        }
        component_names = {
            SetupComponent.CODEX: "codex cli",
            SetupComponent.DIALOG: "dialog",
            SetupComponent.DRAW_THINGS_CLI: "draw things cli",
            SetupComponent.IMAGEMAGICK: "imagemagick",
            SetupComponent.NPM: "npm",
            SetupComponent.OLLAMA: "ollama",
        }
        return {
            component: rows_by_name[component_name]
            for component, component_name in component_names.items()
        }

    def _confirm_components(
        self, title: str, components: tuple[SetupComponent, ...]
    ) -> bool:
        message = "Process the selected components?\n\n" + "\n".join(
            f"  - {self._component_label(component.value)}"
            for component in components
        )
        return self._confirm_system_action(
            f"Confirm {title}", message, title
        )

    @staticmethod
    def _purge_component_cells(
        component: PurgeComponent,
        component_rows: dict[SetupComponent, ComponentVersionDataModel],
        storage_rows: dict[str, str],
    ) -> tuple[str, str, str]:
        setup_components = {
            PurgeComponent.CODEX: SetupComponent.CODEX,
            PurgeComponent.DIALOG: SetupComponent.DIALOG,
            PurgeComponent.DRAW_THINGS_CLI: SetupComponent.DRAW_THINGS_CLI,
            PurgeComponent.NPM: SetupComponent.NPM,
            PurgeComponent.OLLAMA: SetupComponent.OLLAMA,
        }
        if component in setup_components:
            row = component_rows[setup_components[component]]
            return (
                TUICommandHandler._purge_component_label(component),
                row.version,
                row.size,
            )
        if component is PurgeComponent.DRAW_THINGS_MODELS:
            size = storage_rows.get("Draw Things models + assets", "-")
            return "Draw Things Models", "N/A", size
        size = storage_rows.get("Ollama models", "-")
        return "Ollama Models", "N/A", size

    @staticmethod
    def _purge_component_label(component: PurgeComponent) -> str:
        labels = {
            PurgeComponent.CODEX: "Codex CLI",
            PurgeComponent.DIALOG: "dialog",
            PurgeComponent.DRAW_THINGS_CLI: "Draw Things CLI",
            PurgeComponent.NPM: "npm",
            PurgeComponent.OLLAMA: "Ollama",
        }
        return labels.get(component, component.value)

    def _run_terminal_command(
        self, title: str, command: CLICommand
    ):
        self.dialog.clear()
        self.console.restore_terminal_mode()
        self.console.clear_screen()
        self.console.write(title, style="heading")
        self.console.blank_line()
        result = self.tui_command_executor.run_interactive(command)
        self.console.restore_terminal_mode()
        self.console.blank_line()
        self.console.wait_for_key(
            f"Press any key to return from {title}..."
        )
        return result

    def _confirm_system_action(
        self, title: str, message: str, label: str
    ) -> bool:
        return self.system_confirmation_view.render(
            SystemConfirmationDto(title, message, label)
        ).accepted

    @staticmethod
    def _component_label(value: str) -> str:
        if value == SetupComponent.IMAGEMAGICK.value:
            return "ImageMagick"
        return value.replace("-", " ").title()

    def _run_models_menu(self) -> None:
        default_item: ModelsMenuItem | None = None
        while True:
            result = self.models_menu_view.render(
                ModelsMenuDto(default_item=default_item)
            )
            selected = result.selected_item
            if result.cancelled:
                return
            if selected is None:
                raise CLIError(
                    "The models dialog menu returned an unexpected result "
                    f"(exit code {result.dialog_result.exit_code}).",
                    ExitCode.ERROR,
                )
            default_item = selected
            if selected is ModelsMenuItem.INSTALL:
                self._run_install_models_menu()
                continue
            if selected is ModelsMenuItem.DEPENDENCIES:
                self._run_dependencies_view()
                continue
            if selected is ModelsMenuItem.LOCAL:
                self._run_local_models_view()
                continue
            if selected is ModelsMenuItem.REFRESH:
                self._run_captured_command(
                    "Refresh Models",
                    ModelsRefreshCommand(),
                )
                continue
            raise CLIError(
                f"Unsupported models menu selection: {selected.value}.",
                ExitCode.ERROR,
            )

    def _run_local_models_view(self) -> None:
        data = self.local_models_service.collect()
        self._run_models_browser(
            self.local_models_view,
            data.models,
            warning=data.warning,
            empty_message=(
                "No local models or Draw Things assets are installed."
            ),
            base_model=self.settings_storage.load().base_model,
            refresh=self._local_models_snapshot,
        )

    def _local_models_snapshot(
        self,
    ) -> tuple[tuple[LocalModel, ...], str | None]:
        data = self.local_models_service.collect()
        return data.models, self.settings_storage.load().base_model

    def _run_dependencies_view(self) -> None:
        data = self.local_models_service.collect_dependencies()
        self._run_models_browser(
            self.dependencies_view,
            data.models,
            empty_message="No Draw Things dependencies are installed.",
            refresh=self._dependencies_snapshot,
        )

    def _dependencies_snapshot(
        self,
    ) -> tuple[tuple[LocalModel, ...], str | None]:
        data = self.local_models_service.collect_dependencies()
        return data.models, None

    def _run_models_browser(
        self,
        view: LocalModelsView,
        models: tuple[LocalModel, ...],
        *,
        warning: str | None = None,
        empty_message: str,
        base_model: str | None = None,
        refresh: Callable[
            [], tuple[tuple[LocalModel, ...], str | None]
        ]
        | None = None,
    ) -> None:
        if warning:
            self.dialog.render(
                (
                    "--title",
                    view.TITLE,
                    "--msgbox",
                    warning,
                    "0",
                    "0",
                )
            )
        if not models:
            self.dialog.render(
                (
                    "--title",
                    view.TITLE,
                    "--msgbox",
                    empty_message,
                    "0",
                    "0",
                )
            )
            return

        default_model_key: str | None = None
        filters = ModelFilters()
        sort_order = self.settings_storage.load().model_sort_order
        all_models = self.local_models_service.sort(models, sort_order)
        models = filters.apply(all_models)
        while True:
            if not models:
                self.dialog.render(
                    (
                        "--title",
                        view.TITLE,
                        "--msgbox",
                        "No models match the selected filters.",
                        "0",
                        "0",
                    )
                )
                updated = self._filter_models(all_models, filters)
                if updated is None:
                    filters = ModelFilters()
                else:
                    filters = updated
                models = filters.apply(all_models)
                continue
            result = view.render(
                LocalModelsDto(
                    models=models,
                    base_model=base_model,
                    default_model_key=default_model_key,
                )
            )
            selected = result.selected_model
            if result.cancelled:
                return
            if result.filter_requested:
                if selected is not None:
                    default_model_key = LocalModelsView.model_key(selected)
                updated = self._filter_models(all_models, filters)
                if updated is not None:
                    filters = updated
                    models = filters.apply(all_models)
                continue
            if result.sort_requested:
                if selected is not None:
                    default_model_key = LocalModelsView.model_key(selected)
                all_models, sort_order = self._sort_models(
                    all_models, sort_order, view.TITLE
                )
                models = filters.apply(all_models)
                continue
            if selected is None:
                raise CLIError(
                    f"The {view.TITLE} view returned an unexpected result "
                    f"(exit code {result.dialog_result.exit_code}).",
                    ExitCode.ERROR,
                )
            default_model_key = LocalModelsView.model_key(selected)
            if self._run_model_options(selected) and refresh is not None:
                refreshed_models, base_model = refresh()
                if not refreshed_models:
                    return
                all_models = self.local_models_service.sort(
                    refreshed_models, sort_order
                )
                models = filters.apply(all_models)

    def _run_model_options(self, model: LocalModel) -> bool:
        default_item: ModelOptionItem | None = None
        while True:
            result = self.model_options_view.render(
                ModelOptionsDto(model=model, default_item=default_item)
            )
            selected = result.selected_item
            if result.cancelled:
                return False
            if selected is None:
                raise CLIError(
                    "The model options view returned an unexpected result "
                    f"(exit code {result.dialog_result.exit_code}).",
                    ExitCode.ERROR,
                )
            default_item = selected
            if selected is ModelOptionItem.AGENT:
                self._run_agent_view(model.model.name)
                continue
            if selected is ModelOptionItem.CHAT:
                self._run_chat_view(model.model.name)
                continue
            if selected is ModelOptionItem.DETAILS:
                self.model_details_view.render(
                    self._model_details_dto(
                        model,
                        self.settings_storage.load().base_model,
                    )
                )
                continue
            if selected is ModelOptionItem.IMAGE:
                self._run_image_view(model.model.name)
                continue
            if selected is ModelOptionItem.UNINSTALL:
                if self._uninstall_model(model):
                    return True
                continue
            if selected is ModelOptionItem.UPDATE:
                confirmation = self.system_confirmation_view.render(
                    SystemConfirmationDto(
                        title="Update Model",
                        message=(
                            f"Update the installed model?\n\n"
                            f"Model: {model.model.name}\n"
                            f"Backend: {model.backend}"
                        ),
                        confirm_label="Update",
                    )
                )
                if not confirmation.accepted:
                    continue
            command = self._model_action_command(model, selected)
            if command is not None:
                if selected is ModelOptionItem.UPDATE:
                    command_result = self._run_terminal_command(
                        "Update Model", command
                    )
                else:
                    command_result = self.tui_command_executor.run(command)
                    self.dialog.render(
                        (
                            "--title",
                            ModelOptionsView.LABELS[selected],
                            "--msgbox",
                            command_result.output,
                            "0",
                            "0",
                        )
                    )
                if command_result.succeeded:
                    return True
                continue
            raise CLIError(
                f"Unsupported model action: {selected.value}.",
                ExitCode.ERROR,
            )

    def _run_agent_view(self, model: str = "") -> None:
        settings = self.settings_storage.load()
        options = AgentOptionsDto(
            model=model,
            directory=settings.agent_directory or "",
            context_length=settings.agent_context_length,
            execution_approvals=settings.agent_execution_approvals,
        )
        while True:
            result = self.agent_options_view.render(options)
            if result.cancelled:
                return
            if result.options is None:
                raise CLIError(
                    "The Agent options view returned an unexpected result "
                    f"(exit code {result.dialog_result.exit_code}).",
                    ExitCode.ERROR,
                )
            options = result.options
            if result.dialog_result.accepted:
                options = self._edit_agent_option(options, result.selected_item)
                continue
            if not result.run_requested:
                continue
            if options.execution_approvals not in {"ask", "auto", "no-ask"}:
                self.dialog.render(
                    (
                        "--title",
                        "Agent Options",
                        "--msgbox",
                        "Execution must be ask, auto, or no-ask.",
                        "0",
                        "0",
                    )
                )
                continue
            settings.agent_context_length = (
                options.context_length or DEFAULT_CONTEXT_LENGTH
            )
            settings.agent_directory = options.directory or None
            settings.agent_execution_approvals = options.execution_approvals
            self.settings_storage.save(settings)
            input_files = tuple(
                Path(value.strip()).expanduser()
                for value in options.input_files.split(",")
                if value.strip()
            )
            command = AgentCommand(
                model=options.model or None,
                directory=(
                    Path(options.directory).expanduser()
                    if options.directory
                    else None
                ),
                context_length=options.context_length or None,
                execution_approvals=options.execution_approvals,
                session_name=options.session_name or None,
                input_files=input_files,
            )
            self.dialog.clear()
            self.console.restore_terminal_mode()
            self.console.clear_screen()
            self.console.blank_line()
            command_result = self.tui_command_executor.run_interactive(command)
            self.console.restore_terminal_mode()
            self.console.blank_line()
            if command_result.succeeded:
                self.console.read("Press Enter to return to the menu...")
                return
            self.console.read("Press Enter to return to Agent Options...")

    def _run_agent_tools_view(self) -> None:
        definitions = self.tool_service.definitions()
        dto = AgentToolsDto(
            tuple(
                AgentToolDto(
                    name=definition.name,
                    enabled=enabled,
                    scope=definition.scope,
                    description=definition.description,
                )
                for definition, enabled in definitions
            )
        )
        result = self.agent_tools_view.render(dto)
        if result.cancelled:
            return
        messages: list[str] = []
        for definition, enabled in definitions:
            requested = definition.name in result.enabled_tools
            if requested == enabled:
                continue
            command_result = self.tui_command_executor.run(
                ToolCommand(tool=definition.name, enabled=requested)
            )
            messages.append(command_result.output)
            if not command_result.succeeded:
                break
        self.dialog.render(
            (
                "--title",
                "Agent Tools",
                "--msgbox",
                "\n".join(messages) or "Tool settings are unchanged.",
                "0",
                "0",
            )
        )

    def _run_chat_view(self, model: str = "") -> None:
        settings = self.settings_storage.load()
        options = ChatOptionsDto(
            model=model or settings.chat_model or "",
            context_length=settings.chat_context_length,
            session_name=settings.chat_session_name or "",
        )
        while True:
            result = self.chat_options_view.render(options)
            if result.cancelled:
                return
            if result.options is None:
                raise CLIError(
                    "The Chat options view returned an unexpected result "
                    f"(exit code {result.dialog_result.exit_code}).",
                    ExitCode.ERROR,
                )
            options = result.options
            if result.dialog_result.accepted:
                options = self._edit_chat_option(options, result.selected_item)
                continue
            if not result.run_requested:
                continue
            settings.chat_context_length = (
                options.context_length or DEFAULT_CONTEXT_LENGTH
            )
            settings.chat_model = options.model or None
            settings.chat_session_name = options.session_name or None
            self.settings_storage.save(settings)
            input_files = tuple(
                Path(value.strip()).expanduser()
                for value in options.input_files.split(",")
                if value.strip()
            )
            command = ChatCommand(
                model=options.model or None,
                context_length=options.context_length or None,
                session_name=options.session_name or None,
                input_files=input_files,
            )
            self.dialog.clear()
            self.console.restore_terminal_mode()
            self.console.clear_screen()
            self.console.blank_line()
            command_result = self.tui_command_executor.run_interactive(command)
            self.console.restore_terminal_mode()
            if command_result.succeeded:
                self.console.blank_line()
                self.console.read("Press Enter to return to the menu...")
                return
            self.console.blank_line()
            self.console.read("Press Enter to return to Chat Options...")

    def _edit_agent_option(
        self,
        options: AgentOptionsDto,
        item: AgentOptionItem | None,
    ) -> AgentOptionsDto:
        if item is AgentOptionItem.MODEL:
            model = self._select_ollama_model("Agent Model", options.model)
            return replace(options, model=model) if model is not None else options
        if item is AgentOptionItem.DIRECTORY:
            selection = self.directory_selection_view.render(
                DirectorySelectionDto(
                    directory=options.directory,
                    title="Agent Directory",
                )
            )
            return (
                replace(options, directory=selection.directory)
                if selection.directory
                else options
            )
        if item is AgentOptionItem.INPUT_FILES:
            return replace(
                options,
                input_files=self._edit_input_files(options.input_files),
            )
        if item is AgentOptionItem.TOOLS:
            self._run_agent_tools_view()
            return options
        if item is AgentOptionItem.EXECUTION:
            selection = self.component_selection_view.render(
                ComponentSelectionDto(
                    title="Execution",
                    prompt="Select command execution approval mode:",
                    components=(
                        ("ask", "Ask before command execution"),
                        ("auto", "Allow automatic command execution"),
                        ("no-ask", "Never ask; deny commands requiring approval"),
                    ),
                    default_component=options.execution_approvals,
                )
            )
            return (
                replace(options, execution_approvals=selection.component)
                if selection.component
                else options
            )
        prompts = {
            AgentOptionItem.CONTEXT_LENGTH: (
                "Context Length",
                "Context length (for example 16K):",
                options.context_length,
                "30",
                "context_length",
            ),
            AgentOptionItem.SESSION: (
                "Session",
                "Session name; leave empty for an ephemeral agent:",
                options.session_name,
                "68",
                "session_name",
            ),
        }
        if item not in prompts:
            return options
        title, prompt, current, width, field_name = prompts[item]
        value = self._prompt_image_value(title, prompt, current, width=width)
        return options if value is None else replace(options, **{field_name: value})

    def _edit_chat_option(
        self,
        options: ChatOptionsDto,
        item: ChatOptionItem | None,
    ) -> ChatOptionsDto:
        if item is ChatOptionItem.MODEL:
            model = self._select_ollama_model("Chat Model", options.model)
            return replace(options, model=model) if model is not None else options
        if item is ChatOptionItem.INPUT_FILES:
            return replace(
                options,
                input_files=self._edit_input_files(options.input_files),
            )
        prompts = {
            ChatOptionItem.CONTEXT_LENGTH: (
                "Context Length",
                "Context length (for example 16K):",
                options.context_length,
                "30",
                "context_length",
            ),
            ChatOptionItem.SESSION: (
                "Session",
                "Session name; leave empty for an ephemeral chat:",
                options.session_name,
                "68",
                "session_name",
            ),
        }
        if item not in prompts:
            return options
        title, prompt, current, width, field_name = prompts[item]
        value = self._prompt_image_value(title, prompt, current, width=width)
        return options if value is None else replace(options, **{field_name: value})

    def _select_ollama_model(
        self,
        title: str,
        current: str,
    ) -> str | None:
        models = tuple(
            model
            for model in self.local_models_service.collect().models
            if model.backend == "Ollama" and model.asset_type == "Model"
        )
        selection = self.component_selection_view.render(
            ComponentSelectionDto(
                title=title,
                prompt="Select an installed Ollama model:",
                components=tuple(
                    (
                        model.model.name,
                        f"{model.model.size}   {model.category}",
                    )
                    for model in models
                ),
                default_component=current,
            )
        )
        return selection.component

    def _run_image_view(self, model: str = "") -> None:
        settings = self.settings_storage.load()
        options = ImageOptionsDto(
            model=model or settings.image_model or "",
            width=str(settings.image_width),
            height=str(settings.image_height),
            output_directory=settings.image_output_directory or "",
        )
        while True:
            view_result = self.image_options_view.render(options)
            if view_result.cancelled:
                return
            if view_result.options is None:
                raise CLIError(
                    "The Image options view returned an unexpected result "
                    f"(exit code {view_result.dialog_result.exit_code}).",
                    ExitCode.ERROR,
                )
            options = view_result.options
            if view_result.dialog_result.accepted:
                options = self._edit_image_option(
                    options, view_result.selected_item
                )
                continue
            if not view_result.run_requested:
                continue
            prompt = self._prompt_image_value(
                "Prompt",
                "Describe the image to generate:",
                options.prompt,
                width="88",
            )
            if prompt is None:
                continue
            options = replace(options, prompt=prompt)
            try:
                width = int(options.width)
                height = int(options.height)
                strength = (
                    float(options.strength) if options.strength else None
                )
            except ValueError:
                self._show_image_error(
                    "Width and height must be integers; strength must be a number."
                )
                continue
            settings.image_model = options.model or None
            settings.image_width = width
            settings.image_height = height
            settings.image_output_directory = options.output_directory or None
            self.settings_storage.save(settings)
            if not options.prompt.strip():
                self._show_image_error("Prompt cannot be empty.")
                continue
            input_files = tuple(
                Path(value.strip()).expanduser()
                for value in options.input_files.split(",")
                if value.strip()
            )
            command = ImageCommand(
                model=options.model or None,
                width=width,
                height=height,
                output_directory=(
                    Path(options.output_directory).expanduser()
                    if options.output_directory
                    else None
                ),
                file_name=options.file_name or None,
                prompt=options.prompt,
                input_files=input_files,
                strength=strength,
            )
            self.dialog.clear()
            self.console.restore_terminal_mode()
            self.console.clear_screen()
            self.console.write("Image Generation", style="heading")
            self.console.blank_line()
            result = self.tui_command_executor.run_interactive(command)
            self.console.restore_terminal_mode()
            self.console.blank_line()
            self.console.wait_for_key("Press any key to return to Image Generation...")
            if result.succeeded:
                options = replace(options, prompt="", file_name="")

    def _edit_image_option(
        self,
        options: ImageOptionsDto,
        item: ImageOptionItem | None,
    ) -> ImageOptionsDto:
        if item is ImageOptionItem.MODEL:
            data = self.local_models_service.collect()
            models = tuple(
                model
                for model in data.models
                if model.asset_type == "Model"
                and (
                    model.backend == "Draw Things"
                    or model.category == "Image"
                )
            )
            selection = self.component_selection_view.render(
                ComponentSelectionDto(
                    title="Image Model",
                    prompt="Select an image-generation model:",
                    components=tuple(
                        (
                            model.model.name,
                            f"{model.backend}   {model.category}",
                        )
                        for model in models
                    ),
                    default_component=options.model,
                )
            )
            return (
                replace(options, model=selection.component)
                if selection.component
                else options
            )
        if item is ImageOptionItem.INPUT_FILES:
            return replace(
                options,
                input_files=self._edit_input_files(options.input_files),
            )
        if item is ImageOptionItem.DIRECTORY:
            selection = self.directory_selection_view.render(
                DirectorySelectionDto(
                    directory=options.output_directory,
                    title="Target Directory",
                )
            )
            return (
                replace(options, output_directory=selection.directory)
                if selection.directory
                else options
            )
        prompts = {
            ImageOptionItem.WIDTH: (
                "Width",
                "Image width in pixels:",
                options.width,
                "20",
            ),
            ImageOptionItem.HEIGHT: (
                "Height",
                "Image height in pixels:",
                options.height,
                "20",
            ),
            ImageOptionItem.FILE_NAME: (
                "File Name",
                "PNG file name. .png is added automatically when omitted.",
                options.file_name,
                "68",
            ),
            ImageOptionItem.STRENGTH: (
                "Strength",
                "Draw Things img2img denoising strength (0..1).",
                options.strength or "0.35",
                "66",
            ),
        }
        if item not in prompts:
            return options
        title, prompt, current, width = prompts[item]
        value = self._prompt_image_value(title, prompt, current, width=width)
        if value is None:
            return options
        if item in {ImageOptionItem.WIDTH, ImageOptionItem.HEIGHT}:
            try:
                if int(value) <= 0:
                    raise ValueError
            except ValueError:
                self._show_image_error("Enter a positive integer.")
                return options
        if item is ImageOptionItem.STRENGTH:
            try:
                if not 0 <= float(value) <= 1:
                    raise ValueError
            except ValueError:
                self._show_image_error("Enter a value from 0 to 1.")
                return options
        field_names = {
            ImageOptionItem.WIDTH: "width",
            ImageOptionItem.HEIGHT: "height",
            ImageOptionItem.FILE_NAME: "file_name",
            ImageOptionItem.STRENGTH: "strength",
        }
        return replace(options, **{field_names[item]: value})

    def _prompt_image_value(
        self,
        title: str,
        prompt: str,
        current: str,
        *,
        width: str,
    ) -> str | None:
        result = self.dialog.render(
            (
                "--title",
                title,
                "--ok-label",
                "Apply",
                "--cancel-label",
                "Back",
                "--inputbox",
                prompt,
                "0",
                width,
                current,
            ),
            capture_output=True,
        )
        return result.output.strip() if result.accepted else None

    def _show_image_error(self, message: str) -> None:
        self.dialog.render(
            (
                "--title",
                "Image Generation",
                "--msgbox",
                message,
                "0",
                "0",
            )
        )

    def _edit_input_files(self, value: str) -> str:
        paths = tuple(
            item.strip() for item in value.split(",") if item.strip()
        )
        while True:
            result = self.input_files_editor_view.render(
                InputFilesEditorDto(paths)
            )
            paths = result.paths
            if result.cancelled:
                return ", ".join(paths)
            if result.add_requested:
                selection = self.install_file_view.render(
                    InstallSourceDto(
                        source=paths[-1] if paths else "",
                        title="Select Input File",
                    )
                )
                if selection.cancelled:
                    continue
                if selection.source is None:
                    continue
                resolved = Path(selection.source).expanduser()
                if not resolved.is_file():
                    self.dialog.render(
                        (
                            "--title",
                            "Input Files",
                            "--msgbox",
                            f"Input file not found: {selection.source}",
                            "0",
                            "0",
                        )
                    )
                    continue
                normalized = str(resolved.resolve())
                if normalized not in paths:
                    paths = (*paths, normalized)
                continue
            return ", ".join(paths)

    def _uninstall_model(self, model: LocalModel) -> bool:
        dependency_mode = UninstallDependencyModeItem.UNUSED
        if model.backend == "Draw Things" and model.asset_type == "Model":
            mode_result = self.uninstall_dependency_mode_view.render(
                UninstallDependencyModeDto(model=model)
            )
            if mode_result.cancelled:
                return False
            if mode_result.selected_item is None:
                raise CLIError(
                    "The dependency mode view returned an unexpected result "
                    f"(exit code {mode_result.dialog_result.exit_code}).",
                    ExitCode.ERROR,
                )
            dependency_mode = mode_result.selected_item

        confirmation = self.uninstall_confirmation_view.render(
            UninstallConfirmationDto(
                model=model,
                dependency_mode=dependency_mode,
            )
        )
        if not confirmation.confirmed:
            return False

        result = self._run_terminal_command(
            "Uninstall Model",
            UninstallCommand(
                model=model.model.name,
                dependency_mode=dependency_mode.value,
                confirmed=True,
            ),
        )
        return result.succeeded

    @staticmethod
    def _model_action_command(
        model: LocalModel,
        action: ModelOptionItem,
    ) -> CLICommand | None:
        if action is ModelOptionItem.UPDATE:
            return UpdateModelCommand(
                model=model.model.name,
                confirmed=True,
            )
        if model.backend != "Ollama":
            return None
        if action is ModelOptionItem.RUN:
            return RunCommand(model=model.model.name, context_length=None)
        if action is ModelOptionItem.STOP:
            return StopCommand(model=model.model.name)
        if action is ModelOptionItem.SET_BASE:
            return SetBaseCommand(model=model.model.name)
        return None

    def _run_install_models_menu(self) -> None:
        default_item: InstallModelsMenuItem | None = None
        while True:
            result = self.install_models_menu_view.render(
                InstallModelsMenuDto(default_item=default_item)
            )
            selected = result.selected_item
            if result.cancelled:
                return
            if selected is None:
                raise CLIError(
                    "The install models dialog menu returned an unexpected "
                    f"result (exit code {result.dialog_result.exit_code}).",
                    ExitCode.ERROR,
                )
            default_item = selected
            target = self._install_catalog_target(selected)
            if target is not None:
                self._run_catalog_models_view(target)
                continue
            if selected is InstallModelsMenuItem.FILE:
                self._run_install_source(from_file=True)
                continue
            if selected is InstallModelsMenuItem.URL:
                self._run_install_source(from_file=False)
                continue
            raise CLIError(
                f"Unsupported install menu selection: {selected.value}.",
                ExitCode.ERROR,
            )

    def _run_install_source(self, *, from_file: bool) -> None:
        source = ""
        while True:
            source_view = (
                self.install_file_view if from_file else self.install_source_view
            )
            source_result = source_view.render(
                InstallSourceDto(source=source)
            )
            if source_result.cancelled:
                return
            if source_result.source is None:
                self.dialog.render(
                    (
                        "--title",
                        source_view.TITLE,
                        "--msgbox",
                        "Select a local file."
                        if from_file
                        else "Enter a model URL.",
                        "0",
                        "0",
                    )
                )
                continue
            source = self._expand_source_path(source_result.source)
            option_result = self.install_source_option_view.render(
                InstallSourceOptionDto(source=source)
            )
            if option_result.cancelled:
                continue
            if option_result.selected_item is None:
                raise CLIError(
                    "The source type view returned an unexpected result "
                    f"(exit code {option_result.dialog_result.exit_code}).",
                    ExitCode.ERROR,
                )
            if self._install_source(source, option_result.selected_item):
                return

    def _install_source(
        self, source: str, option: InstallSourceOptionItem
    ) -> bool:
        confirmation = self.install_source_confirmation_view.render(
            InstallSourceConfirmationDto(source=source, option=option)
        )
        if not confirmation.confirmed:
            return False
        backend, source_type = self._source_install_options(option)
        result = self._run_terminal_command(
            "Install from Source",
            InstallCommand(
                model=None,
                source=source,
                backend=backend,
                source_type=source_type,
                confirmed=True,
            ),
        )
        return result.succeeded

    @staticmethod
    def _expand_source_path(source: str) -> str:
        if "://" in source:
            return source
        return str(Path(source).expanduser())

    @staticmethod
    def _source_install_options(
        option: InstallSourceOptionItem,
    ) -> tuple[ModelBackend, InstallSourceType]:
        options = {
            InstallSourceOptionItem.AUTO: (
                ModelBackend.AUTO,
                InstallSourceType.AUTO,
            ),
            InstallSourceOptionItem.OLLAMA: (
                ModelBackend.OLLAMA,
                InstallSourceType.MODEL,
            ),
            InstallSourceOptionItem.DRAW_THINGS_MODEL: (
                ModelBackend.DRAW_THINGS,
                InstallSourceType.MODEL,
            ),
            InstallSourceOptionItem.DRAW_THINGS_LORA: (
                ModelBackend.DRAW_THINGS,
                InstallSourceType.LORA,
            ),
        }
        return options[option]

    def _run_catalog_models_view(self, target: ListTarget) -> None:
        view = self.catalog_models_views[target]
        data = self.local_models_service.collect_catalog(target)
        if not data.models:
            self.dialog.render(
                (
                    "--title",
                    view.title,
                    "--msgbox",
                    "No model catalog is available.",
                    "0",
                    "0",
                )
            )
            return
        default_model_key: str | None = None
        filters = ModelFilters()
        sort_order = self.settings_storage.load().model_sort_order
        all_models = self.local_models_service.sort(data.models, sort_order)
        models = filters.apply(all_models)
        while True:
            if not models:
                self.dialog.render(
                    (
                        "--title",
                        view.title,
                        "--msgbox",
                        "No models match the selected filters.",
                        "0",
                        "0",
                    )
                )
                updated = self._filter_models(all_models, filters)
                if updated is None:
                    filters = ModelFilters()
                else:
                    filters = updated
                models = filters.apply(all_models)
                continue
            result = view.render(
                LocalModelsDto(
                    models=models,
                    default_model_key=default_model_key,
                )
            )
            if result.cancelled:
                return
            if result.filter_requested:
                if result.selected_model is not None:
                    default_model_key = LocalModelsView.model_key(
                        result.selected_model
                    )
                updated = self._filter_models(all_models, filters)
                if updated is not None:
                    filters = updated
                    models = filters.apply(all_models)
                continue
            if result.sort_requested:
                if result.selected_model is not None:
                    default_model_key = LocalModelsView.model_key(
                        result.selected_model
                    )
                all_models, sort_order = self._sort_models(
                    all_models, sort_order, view.title
                )
                models = filters.apply(all_models)
                continue
            if result.selected_model is None:
                raise CLIError(
                    "The model catalog returned an unexpected result "
                    f"(exit code {result.dialog_result.exit_code}).",
                    ExitCode.ERROR,
                )
            default_model_key = LocalModelsView.model_key(
                result.selected_model
            )
            if self._run_catalog_model_actions(result.selected_model):
                refreshed = self.local_models_service.collect_catalog(target)
                all_models = self.local_models_service.sort(
                    refreshed.models, sort_order
                )
                models = filters.apply(all_models)

    def _run_catalog_model_actions(self, model: LocalModel) -> bool:
        while True:
            result = self.catalog_model_actions_view.render(
                CatalogModelActionsDto(model)
            )
            if result.cancelled:
                return False
            if result.selected_item is CatalogModelActionItem.DETAILS:
                self.model_details_view.render(self._model_details_dto(model))
                continue
            if result.selected_item is CatalogModelActionItem.INSTALL:
                return self._install_catalog_model(model)
            raise CLIError(
                "The catalog model actions view returned an unexpected result "
                f"(exit code {result.dialog_result.exit_code}).",
                ExitCode.ERROR,
            )

    def _install_catalog_model(self, model: LocalModel) -> bool:
        confirmation = self.install_confirmation_view.render(
            InstallConfirmationDto(model=model)
        )
        if not confirmation.confirmed:
            return False
        backend = (
            ModelBackend.DRAW_THINGS
            if model.backend == "Draw Things"
            else ModelBackend.OLLAMA
        )
        result = self._run_terminal_command(
            "Install Model",
            InstallCommand(
                model=model.model.name,
                source=None,
                backend=backend,
                confirmed=True,
            ),
        )
        return result.succeeded

    def _sort_models(
        self,
        models: tuple[LocalModel, ...],
        current_order: str,
        title: str,
    ) -> tuple[tuple[LocalModel, ...], str]:
        result = self.model_sort_view.render(ModelSortDto(current_order))
        if result.cancelled:
            return models, current_order
        if result.order is None:
            self._show_sort_error("Enter at least one sort field.", title)
            return models, current_order
        try:
            sorted_models = self.local_models_service.sort(
                models, result.order
            )
        except ValueError as error:
            self._show_sort_error(str(error), title)
            return models, current_order
        settings = self.settings_storage.load()
        settings.model_sort_order = result.order
        self.settings_storage.save(settings)
        return sorted_models, result.order

    def _filter_models(
        self,
        models: tuple[LocalModel, ...],
        current: ModelFilters,
    ) -> ModelFilters | None:
        working = current
        labels = {
            ModelFilterItem.NAME: "Name",
            ModelFilterItem.BACKEND: "Backend",
            ModelFilterItem.TYPE: "Type",
            ModelFilterItem.STATE: "State",
            ModelFilterItem.CATEGORY: "Category",
        }
        attributes = {
            ModelFilterItem.NAME: "name",
            ModelFilterItem.BACKEND: "backend",
            ModelFilterItem.TYPE: "asset_type",
            ModelFilterItem.STATE: "state",
            ModelFilterItem.CATEGORY: "category",
        }
        while True:
            result = self.model_filter_view.render(ModelFilterDto(working))
            if result.cancelled:
                return None
            if result.clear_requested:
                working = ModelFilters()
                continue
            if result.apply_requested:
                return working
            item = result.selected_item
            if item is None:
                continue
            attribute = attributes[item]
            if item is ModelFilterItem.NAME:
                value = self._prompt_image_value(
                    "Filter by Name",
                    "Enter a fragment of the model name; leave empty for All:",
                    working.name or "",
                    width="68",
                )
                if value is not None:
                    working = working.with_value(
                        attribute,
                        value.strip() or None,
                    )
                continue
            values = tuple(
                sorted(
                    {getattr(model, attribute) for model in models},
                    key=str.casefold,
                )
            )
            selected = self.component_selection_view.render(
                ComponentSelectionDto(
                    title=f"Filter by {labels[item]}",
                    prompt=f"Select {labels[item]} or All:",
                    components=(
                        ("__all__", "All"),
                        *((value, value) for value in values),
                    ),
                    default_component=getattr(working, attribute) or "__all__",
                )
            )
            if selected.component is not None:
                working = working.with_value(
                    attribute,
                    None
                    if selected.component == "__all__"
                    else selected.component,
                )

    def _show_sort_error(self, message: str, title: str) -> None:
        self.dialog.render(
            (
                "--title",
                title,
                "--msgbox",
                message,
                "0",
                "0",
            )
        )

    def _model_details_dto(
        self,
        model: LocalModel,
        base_model: str | None = None,
    ) -> ModelDetailsDto:
        return ModelDetailsDto(
            model=model,
            base_model=base_model,
            details=self.local_models_service.details(model),
        )

    @staticmethod
    def _install_catalog_target(
        item: InstallModelsMenuItem,
    ) -> ListTarget | None:
        targets = {
            InstallModelsMenuItem.DRAW_THINGS: ListTarget.DRAW_THINGS,
            InstallModelsMenuItem.OLLAMA: ListTarget.OLLAMA,
            InstallModelsMenuItem.OLLAMA_EXPERIMENTAL: (
                ListTarget.OLLAMA_EXPERIMENTAL
            ),
        }
        return targets.get(item)

    def _is_interactive_terminal(self) -> bool:
        return bool(
            getattr(self.console.stdin, "isatty", lambda: False)()
            and getattr(self.console.stdout, "isatty", lambda: False)()
        )
