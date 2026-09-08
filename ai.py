import sys
from typing import Sequence, TextIO

from ai_models_manager.console.cli_commands import CLICommands
from ai_models_manager.console.cli_parser import CLIParser
from ai_models_manager.console.console import Console
from ai_models_manager.console.process_runner import ProcessRunner
from ai_models_manager.core.ollama.ollama_backend import OllamaBackend
from ai_models_manager.core.storage.cache_storage import CacheStorage
from ai_models_manager.core.storage.settings_storage import SettingsStorage
from ai_models_manager.exceptions.cli_error import CLIError


class AI:
    def run(
        self,
        argv: Sequence[str] | None = None,
        *,
        stdin: TextIO = sys.stdin,
        stdout: TextIO = sys.stdout,
        stderr: TextIO = sys.stderr,
    ) -> int:
        console = Console(stdin=stdin, stdout=stdout, stderr=stderr)
        console.blank_line()
        try:
            parser = CLIParser()
            command = parser.parse(sys.argv[1:] if argv is None else argv)
            console.verbose = parser.verbose
            process_runner = ProcessRunner(console.debug)
            console.debug("Verbose diagnostics enabled.")
            cache_storage = CacheStorage()
            commands = CLICommands(
                console=console,
                settings_storage=SettingsStorage(),
                ollama=OllamaBackend(
                    process_runner,
                    cache_directory=cache_storage.directory,
                ),
                cache_storage=cache_storage,
                process_runner=process_runner,
            )
            return int(commands.execute(command))
        except CLIError as error:
            console.error(str(error))
            return int(error.exit_code)
        except KeyboardInterrupt:
            console.warning("Operation interrupted.")
            return 130
        finally:
            console.blank_line()


if __name__ == "__main__":
    ai = AI()
    raise SystemExit(ai.run())
