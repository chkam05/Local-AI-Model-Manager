# AI Model Manager

**English** | [Polski](README_pl-PL.md)

AI Model Manager is a command-line application for managing local AI models,
conversations, coding agents, and image generation. It provides both a regular
CLI and a terminal user interface powered by `dialog`.

Current version: **2.0.0**  
Author: **Copyright (c) Kamil Karpiński**

## Features

- interactive conversations with local Ollama models;
- Codex CLI running as a local coding agent;
- persistent Chat and Agent sessions with restored context;
- image generation and image-to-image workflows through Draw Things;
- browsing installed models and remote model catalogs;
- installing, updating, and removing models;
- Draw Things models, LoRAs, dependencies, and metadata;
- installation, update, and removal of application components;
- a terminal UI started without command-line arguments;
- model filtering, sorting, details, ratings, and storage information;
- colored output and `--verbose` diagnostics.

## Requirements

The application requires:

- macOS or Linux;
- Python 3.10 or newer;
- a POSIX-compatible `sh` shell.

The Python application currently uses only the standard library and does not
require packages installed with `pip`. If a `requirements.txt` file is added in
the future, the launcher will check its packages and report missing ones before
starting the application.

Other components are required only by the features that use them:

| Component | Purpose |
| --- | --- |
| Ollama | text models, Chat, Agent, and Ollama model management |
| Codex CLI | `--agent` mode |
| Draw Things CLI | image generation and Draw Things models |
| `dialog` | terminal user interface |
| ImageMagick | combining multiple input images |
| npm | installing and updating Codex CLI |

Missing components can be installed with `--setup`.

## Getting started

Make the launcher executable if the permission was not preserved:

```sh
chmod +x ai
```

Start the application from the project directory:

```sh
./ai
```

Running it without arguments opens the terminal UI. To use the regular CLI:

```sh
./ai --help
./ai --version
./ai --models
```

The project root directory may have any name. `_bootstrap.py` registers it under
the application's stable internal package name, `ai_models_manager`.

### Adding `ai` to PATH

The simplest approach is to add the project directory to `PATH`. For `zsh`:

```sh
echo 'export PATH="/absolute/path/to/Local_AI_Model_Manager:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

The command can then be run from any directory:

```sh
ai --version
```

Before startup, the launcher validates Python and the application's Python
requirements. When the process ends—including after an error or `Ctrl+C`—it
removes project-owned `__pycache__` directories and `.pyc`/`.pyo` files.

## Terminal UI

Run the application without arguments:

```sh
ai
```

The main menu provides Agent, Chat, Image Generation, Models, Help, System, and
Version views. Operations that launch external programs temporarily leave
`dialog`, display normal terminal output, and return to the TUI when finished.

## Chat

```sh
ai --chat [MODEL] [--session|-s [NAME]] [--input-file|-i [FILE]]...
                  [--context-length|-l [VALUE]]
```

Examples:

```sh
ai --chat qwen3:4b
ai --chat qwen3:4b --session project
ai --chat qwen3:4b -s project -i README.md -l 16K
```

When `--session` is provided, the named session is resumed or created. Message
history and attachments are saved after every successful response. Without a
session name, the conversation is temporary and its context is discarded after
the chat closes.

## Agent

```sh
ai --agent [MODEL] [--directory|-d [DIR]] [--session|-s [NAME]]
                   [--input-file|-i [FILE]]...
                   [--context-length|-l [VALUE]]
                   [--exec [ask|auto|no-ask]]
```

Example:

```sh
ai --agent qwen3.5:4b -d ~/Projects/example -s refactor --exec ask
```

Agent mode connects Codex CLI to a local Ollama endpoint. A named session keeps
its metadata, attachments, and native Codex rollout. Without `--directory`, an
unnamed Agent session uses a temporary workspace.

## Image generation

```sh
ai --image [MODEL] --prompt|-p [PROMPT]
                   [--width|-w [PX]] [--height|-h [PX]]
                   [--output-dir|-o [DIR]] [--file-name|-n [NAME]]
                   [--input-file|-i [FILE]]... [--strength [0..1]]
```

Examples:

```sh
ai --image model.ckpt -p "Cat on a fence at sunset" -w 1024 -h 768
ai --image model.ckpt -p "Black formal outfit, preserve the face" \
   -i input.png --strength 0.35 -o ~/Pictures
```

The default size is `800x600`. Draw Things dimensions are automatically aligned
to multiples of 64. Multiple input images require ImageMagick.

## Model management

### Browse models

```sh
ai --models [local|ollama|ollama-experimental|draw-things]
            [--order|-o [FIELD[,FIELD...]]] [--asc|--desc]
            [--dependencies|-d]
```

Examples:

```sh
ai --models
ai --models draw-things
ai --models local --dependencies
ai --models -o 'backend<,type<,rating<,size>'
```

`--dependencies` includes Draw Things dependencies and metadata, which are
hidden from concise model lists by default. Append `<` to a field for descending
order or `>` for ascending order. Quote the complete value so the shell does not
interpret these characters as redirection operators.

Available sorting fields include `model`, `backend`, `type`, `state`, `size`,
`rating`, `codex`, `filter`, `category`, and `description`. Their availability
depends on the selected catalog.

### Details and catalog refresh

```sh
ai --details [MODEL]
ai --models-refresh
```

`--models-refresh` refreshes Ollama, Ollama Experimental, and Draw Things
catalogs. If a source is unavailable, the last valid cached catalog is retained.

### Install models

```sh
ai --install [MODEL] [--backend|-b [auto|ollama|draw-things]]
ai --install --source|-s [SOURCE]
             [--backend|-b [auto|ollama|draw-things]]
             [--type|-t [auto|model|lora]]
```

Examples:

```sh
ai --install qwen3.5:4b
ai --install realvisxl_v4.0_q6p_q8p.ckpt
ai --install -s ~/Downloads/style.safetensors -b draw-things -t lora
ai --install -s https://example.com/model.gguf
```

### Update and remove models

```sh
ai --update-model [MODEL]
ai --uninstall [MODEL] [--dependencies|-d [keep|unused|all]]
```

Draw Things dependency removal modes:

- `keep` removes only the selected model;
- `unused` also removes dependencies with no other installed users and is the
  default mode;
- `all` removes every known dependency, including shared dependencies.

Installation, update, and removal operations require confirmation.

### Base model and Ollama runtime state

```sh
ai --set-base [MODEL]
ai --run [MODEL] [--context-length|-l [VALUE]]
ai --stop [MODEL]
ai --stop-all
```

`--run` loads an Ollama model into memory without opening a chat. The default
context length is `16K`.

## Sessions and tools

```sh
ai --session
ai --session [SESSION] --delete|-d
ai --session [SESSION] --rename|-r [NEW_NAME]
ai --tools
ai --tool [TOOL] --enable|-e|--disable|-d
```

Running `ai --session` without a name lists all saved Chat and Agent sessions.
Tool settings are persistent and apply to Agent sessions started by the app.

## Administration

```sh
ai --setup [ollama|npm|codex|dialog|draw-things-cli|imagemagick]
ai --update [ollama|npm|codex|dialog|draw-things-cli|imagemagick]
ai --purge [COMPONENT]
ai --clear-cache
```

`--setup` installs missing components and `--update` updates installed ones.
Automatic setup supports macOS and Linux; automatic Draw Things CLI installation
is available on macOS only.

`--purge` is destructive and requires confirmation with `y`. Supported values:

- `ollama`;
- `models` or `ollama-models`;
- `npm`;
- `codex`;
- `dialog`;
- `draw-things-cli`;
- `draw-things-models`;
- `'*'` for the complete managed toolchain and model data.

Quote `'*'` to prevent shell expansion. `AI_PURGE_FORCE=1` bypasses confirmation
and should be used only deliberately in automation.

`--clear-cache` removes disposable catalog data while preserving settings,
sessions, and installed models.

## Diagnostics

The global `--verbose` option may be placed before or after the command:

```sh
ai --verbose --models
ai --models --verbose
```

Diagnostics are written to `stderr` and include sanitized external commands,
working directories, timeouts, cache decisions, execution time, exit codes, and
captured standard error. They do not change the command result.

## Application data

| Data | Location |
| --- | --- |
| Settings | `~/.config/ai/settings.json` |
| Tool settings | `~/.config/ai/tools.json` |
| Sessions | `~/.config/ai/sessions/` |
| Cache | `${XDG_CACHE_HOME:-~/.cache}/ai/` |

Settings and sessions are stored atomically as JSON. Persistent files are
created with permissions restricted to the current user.

## Environment variables

| Variable | Meaning |
| --- | --- |
| `AI_OLLAMA_URL` | local Ollama API URL |
| `OLLAMA_MODELS` | custom Ollama model storage directory |
| `AI_LIBRARY_CACHE_TTL` | Ollama catalog cache lifetime in seconds |
| `AI_DRAW_THINGS_CACHE_TTL` | Draw Things catalog cache lifetime |
| `DRAWTHINGS_MODELS_DIR` | custom Draw Things Models directory |
| `AI_HW_OS`, `AI_HW_ARCH` | override detected OS and architecture |
| `AI_HW_CHIP`, `AI_HW_MODEL` | override detected CPU/SoC and device |
| `AI_HW_RAM_GB` | override detected memory in GB |
| `AI_PURGE_FORCE=1` | skip interactive purge confirmation |
| `NO_COLOR` | disable ANSI colors |

## Project structure

```text
.
├── ai                     # POSIX shell launcher
├── _bootstrap.py          # directory-name-independent package loader
├── ai.py                  # application entry point
├── config.py              # application constants
├── console/
│   ├── commands/          # CLI command data models
│   ├── handlers/          # command implementations
│   └── models/            # console-layer models
├── core/                  # domain services and backend integrations
│   ├── agent/
│   ├── chat/
│   ├── draw_things/
│   ├── ollama/
│   ├── session/
│   └── storage/
├── enums/                 # shared enumerations
├── exceptions/            # controlled application errors
├── models/                # primary data models
└── views/
    ├── dtos/              # view input and result DTOs
    └── models/            # shared dialog view models
```

CLI execution flow:

```text
launcher → bootstrap → CLIParser → CLICommand → CommandHandler → service/backend
```

TUI views build `dialog` configurations through the shared view and DTO layers.
Operations are executed by the same handlers as their CLI equivalents.

## Safety

- destructive operations require explicit confirmation;
- deletion targets are validated before an operation begins;
- protected targets include the filesystem root, home directory, application
  workspace, mount points, and unsafe symbolic links;
- secrets are redacted from external-command diagnostics;
- model installation and removal plans are shown before confirmation.

For the complete and always current command reference, run:

```sh
ai --help
```
