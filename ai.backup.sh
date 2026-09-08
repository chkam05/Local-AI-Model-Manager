#!/usr/bin/env bash
set -Eeuo pipefail

# Keep numeric parsing stable regardless of the user's locale (e.g. 1.9, not 1,9).
export LC_NUMERIC=C

# ai - lightweight manager for local Ollama models
# Version: 1.8.1
#
# Configuration:
#   ~/.config/ai/base_model
#   ~/.config/ai/tools.conf
#
# Optional environment variables:
#   AI_OLLAMA_URL=http://127.0.0.1:11434
#   AI_PURGE_FORCE=1   # skip the interactive PURGE confirmation

SCRIPT_VERSION="1.11.10"

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/ai"
BASE_MODEL_FILE="$CONFIG_DIR/base_model"
TOOLS_CONFIG_FILE="$CONFIG_DIR/tools.conf"
OLLAMA_URL="${AI_OLLAMA_URL:-http://127.0.0.1:11434}"
OLLAMA_LIBRARY_URL="${AI_OLLAMA_LIBRARY_URL:-https://ollama.com/library}"
OLLAMA_EXPERIMENTAL_URL="${AI_OLLAMA_EXPERIMENTAL_URL:-https://ollama.com/x}"
OLLAMA_REGISTRY_URL="${AI_OLLAMA_REGISTRY_URL:-https://registry.ollama.ai}"
OLLAMA_REGISTRY_FALLBACK_URL="${AI_OLLAMA_REGISTRY_FALLBACK_URL:-https://registry.ollama.com}"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/ai"
LIBRARY_CACHE_FILE="$CACHE_DIR/ollama-library-v3.tsv"
LIBRARY_CACHE_TTL="${AI_LIBRARY_CACHE_TTL:-86400}"

if [[ -t 1 && -z "${NO_COLOR:-}" && "${TERM:-}" != "dumb" ]]; then
  # Store a real ESC byte in the ANSI variables. Using literal strings such
  # as '\033[31m' would make heredocs print the backslash sequence verbatim.
  ESC="$(printf '\033')"

  # Text styles.
  RESET="${ESC}[0m"
  BOLD="${ESC}[1m"
  DIM="${ESC}[2m"
  ITALIC="${ESC}[3m"
  UNDERLINE="${ESC}[4m"
  REVERSE="${ESC}[7m"

  # Standard foreground colors (ANSI 30-37).
  BLACK="${ESC}[30m"
  RED="${ESC}[31m"
  GREEN="${ESC}[32m"
  YELLOW="${ESC}[33m"
  BLUE="${ESC}[34m"
  MAGENTA="${ESC}[35m"
  CYAN="${ESC}[36m"
  WHITE="${ESC}[37m"

  # Bright foreground colors (ANSI 90-97).
  BRIGHT_BLACK="${ESC}[90m"
  BRIGHT_RED="${ESC}[91m"
  BRIGHT_GREEN="${ESC}[92m"
  BRIGHT_YELLOW="${ESC}[93m"
  BRIGHT_BLUE="${ESC}[94m"
  BRIGHT_MAGENTA="${ESC}[95m"
  BRIGHT_CYAN="${ESC}[96m"
  BRIGHT_WHITE="${ESC}[97m"

  # Standard background colors (ANSI 40-47).
  BG_BLACK="${ESC}[40m"
  BG_RED="${ESC}[41m"
  BG_GREEN="${ESC}[42m"
  BG_YELLOW="${ESC}[43m"
  BG_BLUE="${ESC}[44m"
  BG_MAGENTA="${ESC}[45m"
  BG_CYAN="${ESC}[46m"
  BG_WHITE="${ESC}[47m"

  # Bright background colors (ANSI 100-107).
  BG_BRIGHT_BLACK="${ESC}[100m"
  BG_BRIGHT_RED="${ESC}[101m"
  BG_BRIGHT_GREEN="${ESC}[102m"
  BG_BRIGHT_YELLOW="${ESC}[103m"
  BG_BRIGHT_BLUE="${ESC}[104m"
  BG_BRIGHT_MAGENTA="${ESC}[105m"
  BG_BRIGHT_CYAN="${ESC}[106m"
  BG_BRIGHT_WHITE="${ESC}[107m"
else
  ESC=''
  RESET='' BOLD='' DIM='' ITALIC='' UNDERLINE='' REVERSE=''
  BLACK='' RED='' GREEN='' YELLOW='' BLUE='' MAGENTA='' CYAN='' WHITE=''
  BRIGHT_BLACK='' BRIGHT_RED='' BRIGHT_GREEN='' BRIGHT_YELLOW=''
  BRIGHT_BLUE='' BRIGHT_MAGENTA='' BRIGHT_CYAN='' BRIGHT_WHITE=''
  BG_BLACK='' BG_RED='' BG_GREEN='' BG_YELLOW='' BG_BLUE='' BG_MAGENTA='' BG_CYAN='' BG_WHITE=''
  BG_BRIGHT_BLACK='' BG_BRIGHT_RED='' BG_BRIGHT_GREEN='' BG_BRIGHT_YELLOW=''
  BG_BRIGHT_BLUE='' BG_BRIGHT_MAGENTA='' BG_BRIGHT_CYAN='' BG_BRIGHT_WHITE=''
fi

# Semantic colors used directly by the help text.
HELP_HEADER="${BOLD}${BRIGHT_YELLOW}"
HELP_COMMAND="${BOLD}${GREEN}"
HELP_SWITCH="${BOLD}${MAGENTA}"
HELP_VALUE="${BOLD}${CYAN}"
HELP_SUBTITLE="${BOLD}${YELLOW}"

# Semantic colors used by `ai --list`. These remain empty automatically when
# stdout is not a TTY or NO_COLOR is set, so redirected output stays plain.
LIST_HEADER="${BOLD}${BRIGHT_YELLOW}"
LIST_LABEL="${BOLD}${CYAN}"
LIST_VALUE="${BRIGHT_WHITE}"
LIST_MODEL="${BRIGHT_CYAN}"
LIST_SIZE="${BRIGHT_BLUE}"
LIST_DESCRIPTION="${DIM}${WHITE}"
LIST_SEPARATOR="${DIM}${BRIGHT_BLACK}"

info()    { printf '%b\n' "${CYAN}==>${RESET} $*"; }
success() { printf '%b\n' "${GREEN}OK${RESET}  $*"; }
warn()    { printf '%b\n' "${YELLOW}WARN${RESET} $*" >&2; }
die()     { printf '%b\n' "${RED}ERR${RESET} $*" >&2; exit 1; }

usage() {
  printf '%s\n' '--------------------------------------------------------------------'
  printf '%s' "${BOLD}${RED}"
  cat <<'ASCII_ART'
                  ___  _    _      _   __  __   _   
                 / _ \| |  | |    /_\ |  \/  | /_\  
                | (_) | |__| |__ / _ \| |\/| |/ _ \ 
                 \___/|____|____/_/ \_\_|  |_/_/ \_\
  __  __  ___  ___  ___ _      __  __   _   _  _   _   ___ ___ ___ 
 |  \/  |/ _ \|   \| __| |    |  \/  | /_\ | \| | /_\ / __| __| _ \
 | |\/| | (_) | |) | _|| |__  | |\/| |/ _ \| .` |/ _ \ (_ | _||   /
 |_|  |_|\___/|___/|___|____| |_|  |_/_/ \_\_|\_/_/ \_\___|___|_|_\
ASCII_ART
  printf '%s' "${RESET}"
  cat <<EOF
--------------------------------------------------------------------
${HELP_HEADER}USAGE:${RESET}

  ${HELP_HEADER}General Purpose:${RESET}
    ${HELP_COMMAND}ai${RESET}
    ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--agent${RESET} ${HELP_VALUE}[MODEL]${RESET} [${HELP_SWITCH}--directory${RESET}|${HELP_SWITCH}-d${RESET} ${HELP_VALUE}DIR${RESET}] [${HELP_SWITCH}--context-length${RESET}|${HELP_SWITCH}-l${RESET} ${HELP_VALUE}VALUE${RESET}] [${HELP_SWITCH}--exec${RESET} ${HELP_VALUE}MODE${RESET}] [${HELP_SWITCH}--session${RESET}|${HELP_SWITCH}-s${RESET} ${HELP_VALUE}FILE${RESET}] [${HELP_SWITCH}--input-file${RESET}|${HELP_SWITCH}-i${RESET} ${HELP_VALUE}FILE${RESET}]...
    ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--chat${RESET} ${HELP_VALUE}[MODEL]${RESET} [${HELP_SWITCH}--context-length${RESET}|${HELP_SWITCH}-l${RESET} ${HELP_VALUE}VALUE${RESET}] [${HELP_SWITCH}--session${RESET}|${HELP_SWITCH}-s${RESET} ${HELP_VALUE}FILE${RESET}] [${HELP_SWITCH}--input-file${RESET}|${HELP_SWITCH}-i${RESET} ${HELP_VALUE}FILE${RESET}]...
    ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--image${RESET} ${HELP_VALUE}[MODEL]${RESET} [${HELP_SWITCH}--width${RESET}|${HELP_SWITCH}-w${RESET} ${HELP_VALUE}PX${RESET}] [${HELP_SWITCH}--height${RESET}|${HELP_SWITCH}-h${RESET} ${HELP_VALUE}PX${RESET}] [${HELP_SWITCH}--output-dir${RESET}|${HELP_SWITCH}-o${RESET} ${HELP_VALUE}DIR${RESET}] [${HELP_SWITCH}--file-name${RESET}|${HELP_SWITCH}-n${RESET} ${HELP_VALUE}NAME${RESET}] [${HELP_SWITCH}--input-file${RESET}|${HELP_SWITCH}-i${RESET} ${HELP_VALUE}FILE${RESET}]... [${HELP_SWITCH}--strength${RESET} ${HELP_VALUE}0..1${RESET}] ${HELP_SWITCH}--prompt${RESET}|${HELP_SWITCH}-p${RESET} ${HELP_VALUE}"PROMPT"${RESET}
    ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--run${RESET} ${HELP_VALUE}[MODEL]${RESET} [${HELP_SWITCH}--context-length${RESET}|${HELP_SWITCH}-l${RESET} ${HELP_VALUE}VALUE${RESET}]
    ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--stop${RESET} ${HELP_VALUE}[MODEL]${RESET}
    ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--stop-all${RESET}
    ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--tools${RESET}
    ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--tool${RESET} ${HELP_VALUE}[TOOL]${RESET} ${HELP_SWITCH}--enable${RESET}|${HELP_SWITCH}-e${RESET}
    ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--tool${RESET} ${HELP_VALUE}[TOOL]${RESET} ${HELP_SWITCH}--disable${RESET}|${HELP_SWITCH}-d${RESET}
    ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--help${RESET}
    ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--version${RESET}

  ${HELP_HEADER}Models Management:${RESET}
    ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--install${RESET} ${HELP_VALUE}[MODEL]${RESET} [${HELP_SWITCH}--backend${RESET}|${HELP_SWITCH}-b${RESET} ${HELP_VALUE}ollama|draw-things${RESET}]
    ai --install --source|-s SOURCE [--backend|-b ollama|draw-things] [--type|-t auto|model|lora]
    ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--list${RESET} [${HELP_VALUE}local|ollama|ollama-experimental|draw-things${RESET}] [${HELP_SWITCH}--order${RESET}|${HELP_SWITCH}-o${RESET} ${HELP_VALUE}FIELD[,FIELD...]${RESET}] [${HELP_SWITCH}--asc${RESET}|${HELP_SWITCH}--desc${RESET}]
    ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--set-base${RESET} ${HELP_VALUE}[MODEL]${RESET}
    ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--uninstall${RESET} ${HELP_VALUE}[MODEL]${RESET}

  ${HELP_HEADER}Setup:${RESET}
    ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--setup${RESET}
    ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--purge${RESET} ${HELP_VALUE}[COMPONENT]${RESET}

${HELP_HEADER}COMMANDS:${RESET}

${HELP_HEADER}General Purpose:${RESET}
  ${HELP_COMMAND}ai${RESET}
      Opens the interactive dialog-based TUI when no command-line arguments
      are provided. Use the arrow keys to navigate, Enter to select, and
      Esc/Cancel to go back.

      The TUI requires the ${HELP_VALUE}dialog${RESET} package. Run ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--setup${RESET} to
      install or update it together with the rest of the AI toolchain.

      In the ${HELP_VALUE}Models${RESET} browser, use ${HELP_VALUE}Enter${RESET} for model actions, ${HELP_VALUE}F1${RESET} for details,
      and ${HELP_VALUE}F2${RESET} for sorting. The sorting screen supports an ordered
      list of columns with an individual ${HELP_VALUE}asc/desc${RESET} direction for each one.
      On some Mac keyboards, function keys may require holding ${HELP_VALUE}Fn${RESET}.

  ${HELP_SWITCH}--agent${RESET} ${HELP_VALUE}[MODEL]${RESET}
      Opens Codex CLI as a local coding agent using the selected Ollama model.
      If ${HELP_VALUE}MODEL${RESET} is omitted, the model configured with ${HELP_SWITCH}--set-base${RESET} is used.

      ${HELP_SUBTITLE}Optional:${RESET}
        ${HELP_SWITCH}--directory${RESET} ${HELP_VALUE}[DIR]${RESET}
        ${HELP_SWITCH}-d${RESET} ${HELP_VALUE}[DIR]${RESET}
            Uses ${HELP_VALUE}DIR${RESET} as the Codex workspace. If the directory does not exist,
            it is created automatically. Codex runs with the workspace-write
            sandbox and can edit files inside that workspace.

            If ${HELP_SWITCH}--directory${RESET} is omitted, Codex starts in a temporary empty
            read-only workspace instead of using the directory from which
            ${HELP_COMMAND}ai${RESET} was launched.

        ${HELP_SWITCH}--context-length${RESET} ${HELP_VALUE}[VALUE]${RESET}
        ${HELP_SWITCH}-l${RESET} ${HELP_VALUE}[VALUE]${RESET}
            Applies the context length when ${HELP_COMMAND}ai${RESET} has to load the model before
            starting the agent. If the model is already running, its current
            context remains unchanged.

        ${HELP_SWITCH}--input-file${RESET} ${HELP_VALUE}[FILE]${RESET}
        ${HELP_SWITCH}-i${RESET} ${HELP_VALUE}[FILE]${RESET}
            Adds a bootstrap input file. Repeat the option for multiple files.
            Files are staged temporarily inside the Codex workspace and referenced
            in the initial prompt. Vision-capable local models can also receive
            image files as initial Codex image attachments.

        ${HELP_SWITCH}--session${RESET} ${HELP_VALUE}[FILE]${RESET}
        ${HELP_SWITCH}-s${RESET} ${HELP_VALUE}[FILE]${RESET}
            Persists/resumes this Agent session. If FILE does not exist, it is
            created and linked to the native Codex session after the first run.
            If it already exists, ${HELP_COMMAND}ai${RESET} resumes the stored Codex session.
            When MODEL/workspace/context/approval options are omitted, metadata stored
            in the session file is reused when available.

        ${HELP_SWITCH}--exec${RESET} ${HELP_VALUE}[MODE]${RESET}
            Controls how Codex handles command-execution approval requests.

            ${HELP_VALUE}MODE:${RESET}
              ${HELP_VALUE}ask${RESET}
                  Codex asks you when an operation needs approval.

              ${HELP_VALUE}auto${RESET}
                  Approval requests are routed to Codex automatic review.
                  This is the default mode.

              ${HELP_VALUE}no-ask${RESET}
                  Codex never asks for approval. Operations allowed by the
                  selected sandbox can run; operations that require sandbox
                  escalation fail instead of prompting.

            ${HELP_SWITCH}--exec${RESET} changes approval behavior only. It does not grant
            danger-full-access and does not widen the workspace sandbox.

      ${HELP_SUBTITLE}Tools:${RESET}
        Agent sessions use the persistent tool selection shown by ${HELP_SWITCH}--tools${RESET}.
        Change it with ${HELP_SWITCH}--tool${RESET} or from the Agent View. Web search is disabled
        by default for local/offline-friendly operation.

      ${HELP_SUBTITLE}Model lifecycle:${RESET}
        If the selected model is not already running, ${HELP_COMMAND}ai${RESET} loads it before
        starting Codex and stops it when the Codex session ends. If the model
        was already running, ${HELP_COMMAND}ai${RESET} leaves it running.

      ${HELP_SUBTITLE}Examples:${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--agent${RESET} ${HELP_VALUE}qwen3.5:4b${RESET} ${HELP_SWITCH}-d${RESET} ${HELP_VALUE}~/Projects/site${RESET} ${HELP_SWITCH}-l${RESET} ${HELP_VALUE}16K${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--agent${RESET} ${HELP_SWITCH}-d${RESET} ${HELP_VALUE}./sandbox${RESET} ${HELP_SWITCH}--exec${RESET} ${HELP_VALUE}ask${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--agent${RESET} ${HELP_SWITCH}-d${RESET} ${HELP_VALUE}./sandbox${RESET} ${HELP_SWITCH}--exec${RESET} ${HELP_VALUE}auto${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--agent${RESET} ${HELP_SWITCH}-d${RESET} ${HELP_VALUE}./sandbox${RESET} ${HELP_SWITCH}--exec${RESET} ${HELP_VALUE}no-ask${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--agent${RESET} ${HELP_SWITCH}-d${RESET} ${HELP_VALUE}./sandbox${RESET} ${HELP_SWITCH}-s${RESET} ${HELP_VALUE}./agent-session.json${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--agent${RESET}

  ${HELP_SWITCH}--chat${RESET} ${HELP_VALUE}[MODEL]${RESET}
      Opens an interactive terminal chat with the selected model.
      If ${HELP_VALUE}MODEL${RESET} is omitted, the model configured with ${HELP_SWITCH}--set-base${RESET} is used.

      ${HELP_SUBTITLE}Optional:${RESET}
        ${HELP_SWITCH}--context-length${RESET} ${HELP_VALUE}[VALUE]${RESET}
        ${HELP_SWITCH}-l${RESET} ${HELP_VALUE}[VALUE]${RESET}

        ${HELP_SWITCH}--input-file${RESET} ${HELP_VALUE}[FILE]${RESET}
        ${HELP_SWITCH}-i${RESET} ${HELP_VALUE}[FILE]${RESET}
            Adds a file to the first chat turn. Repeat for multiple files. Text-like
            files are added as context; images are sent to Ollama vision models.
            PDF text is extracted when ${HELP_VALUE}pdftotext${RESET} is available.

        ${HELP_SWITCH}--session${RESET} ${HELP_VALUE}[FILE]${RESET}
        ${HELP_SWITCH}-s${RESET} ${HELP_VALUE}[FILE]${RESET}
            Persists/resumes the chat history in FILE. A missing file is created
            immediately; an existing chat-session file is loaded. The file is
            updated atomically after each successful assistant response.

      When no input files or session file are provided and a context length is provided, ${HELP_COMMAND}ai${RESET} creates a temporary local
      model profile with that num_ctx value, opens the standard Ollama chat,
      and removes the temporary profile when the chat ends.

      ${HELP_SUBTITLE}Examples:${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--chat${RESET} ${HELP_VALUE}qwen3.5:4b${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--chat${RESET} ${HELP_VALUE}qwen3.5:4b${RESET} ${HELP_SWITCH}-l${RESET} ${HELP_VALUE}16K${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--chat${RESET} ${HELP_SWITCH}-l${RESET} ${HELP_VALUE}16K${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--chat${RESET} ${HELP_VALUE}qwen3.5:4b${RESET} ${HELP_SWITCH}-s${RESET} ${HELP_VALUE}./chat-session.json${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--chat${RESET}

      Session files are mode 600. Chat session files contain conversation text and
      input-file context. Agent session files contain a pointer to Codex native
      session storage under ${HELP_VALUE}~/.codex${RESET}; deleting that Codex session data makes the
      pointer non-resumable. A Chat session file and an Agent session file are not interchangeable.

      Exit the chat with ${HELP_VALUE}/bye${RESET} or ${HELP_VALUE}Ctrl+D${RESET}.

  ${HELP_SWITCH}--image${RESET} ${HELP_VALUE}[MODEL]${RESET}
      Generates a PNG with an installed Ollama or Draw Things image model. If MODEL
      is omitted, an installed compatible image model is selected automatically.

      Ollama image generation remains experimental. Width defaults to ${HELP_VALUE}800${RESET},
      height to ${HELP_VALUE}600${RESET}, output directory to the current directory,
      and file name to ${HELP_VALUE}image_yyyyMMddHHmmsszzz.png${RESET}.

      ${HELP_SUBTITLE}Options:${RESET}
        ${HELP_SWITCH}--width${RESET}, ${HELP_SWITCH}-w${RESET} ${HELP_VALUE}PX${RESET}
        ${HELP_SWITCH}--height${RESET}, ${HELP_SWITCH}-h${RESET} ${HELP_VALUE}PX${RESET}
        ${HELP_SWITCH}--output-dir${RESET}, ${HELP_SWITCH}-o${RESET} ${HELP_VALUE}DIR${RESET}
        ${HELP_SWITCH}--file-name${RESET}, ${HELP_SWITCH}-n${RESET} ${HELP_VALUE}NAME${RESET}
        ${HELP_SWITCH}--input-file${RESET}, ${HELP_SWITCH}-i${RESET} ${HELP_VALUE}FILE${RESET}
            Adds an input/reference image. Repeat for multiple images. Draw Things
            accepts an init image; multiple inputs are auto-composed when ImageMagick
            is available, otherwise the first image is used with a warning.
        ${HELP_SWITCH}--strength${RESET} ${HELP_VALUE}0..1${RESET}
            Draw Things img2img denoising strength. Defaults to ${HELP_VALUE}0.35${RESET} when
            input images are supplied.
        ${HELP_SWITCH}--prompt${RESET}, ${HELP_SWITCH}-p${RESET} ${HELP_VALUE}"PROMPT"${RESET}

      The TUI remembers Image model/width/height/target directory, Chat context
      length, and Agent context/workspace/approval settings in ${HELP_VALUE}~/.config/ai/state.conf${RESET}.
      Agent tool selections are already persisted separately in ${HELP_VALUE}~/.config/ai/tools.conf${RESET}.
      Input files and prompts are intentionally not persisted.

  ${HELP_SWITCH}--run${RESET} ${HELP_VALUE}[MODEL]${RESET}
      Loads a model into memory and keeps it loaded (keep_alive=-1).
      If ${HELP_VALUE}MODEL${RESET} is omitted, the model configured with ${HELP_SWITCH}--set-base${RESET} is used.

      ${HELP_SUBTITLE}Optional:${RESET}
        ${HELP_SWITCH}--context-length${RESET} ${HELP_VALUE}[VALUE]${RESET}
        ${HELP_SWITCH}-l${RESET} ${HELP_VALUE}[VALUE]${RESET}

      ${HELP_VALUE}VALUE${RESET}${HELP_SUBTITLE} may be written as:${RESET}
        ${HELP_VALUE}16384${RESET}  -> 16384 tokens
        ${HELP_VALUE}16K${RESET}    -> 16 * 1024 = 16384 tokens
        ${HELP_VALUE}1M${RESET}     -> 1 * 1024 * 1024 = 1048576 tokens

      ${HELP_SUBTITLE}Examples:${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--run${RESET} ${HELP_VALUE}qwen3.5:4b${RESET} ${HELP_SWITCH}-l${RESET} ${HELP_VALUE}16K${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--run${RESET} ${HELP_SWITCH}-l${RESET} ${HELP_VALUE}32768${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--run${RESET}

  ${HELP_SWITCH}--stop${RESET} ${HELP_VALUE}[MODEL]${RESET}
      Unloads the selected model from memory.
      If ${HELP_VALUE}MODEL${RESET} is omitted, the base model is used.

  ${HELP_SWITCH}--stop-all${RESET}
      Stops every model currently listed by ${HELP_COMMAND}ollama ps${RESET}.

  ${HELP_SWITCH}--help${RESET}
      Shows this help.

  ${HELP_SWITCH}--version${RESET}
      Shows the installed versions and approximate on-disk size of:
        - this ${HELP_COMMAND}ai${RESET} script
        - Ollama
        - npm
        - Codex CLI
        - dialog
        - Draw Things CLI

      It also reports the disk space used by the Ollama model store and the
      Draw Things Models directory, plus their combined total. Missing
      components are shown as "not installed".

${HELP_HEADER}Tools Management:${RESET}
  ${HELP_SWITCH}--tools${RESET}
      Shows the tools managed by ${HELP_COMMAND}ai${RESET}, whether each tool is enabled,
      and whether it is local or uses the network. Tool state is shared by the CLI
      and the Agent View and is stored in ${HELP_VALUE}~/.config/ai/tools.conf${RESET}.

  ${HELP_SWITCH}--tool${RESET} ${HELP_VALUE}[TOOL]${RESET} ${HELP_SWITCH}--enable${RESET}|${HELP_SWITCH}-e${RESET}
  ${HELP_SWITCH}--tool${RESET} ${HELP_VALUE}[TOOL]${RESET} ${HELP_SWITCH}--disable${RESET}|${HELP_SWITCH}-d${RESET}
      Enables or disables one managed Codex tool. Supported tools:

        ${HELP_VALUE}shell${RESET}       Local command execution. Enabled by default.
        ${HELP_VALUE}view-image${RESET}  Local image attachment/view tool. Enabled by default.
        ${HELP_VALUE}web-search${RESET}  Network web search. Disabled by default.

      Enabling ${HELP_VALUE}web-search${RESET} allows Codex to expose live web search to the
      local model. The search provider may require network access, authentication, or
      its own API/service plan. Disabling it removes the Codex web-search tool from
      sessions started through ${HELP_COMMAND}ai${RESET}.

      ${HELP_SUBTITLE}Examples:${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--tools${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--tool${RESET} ${HELP_VALUE}web-search${RESET} ${HELP_SWITCH}--enable${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--tool${RESET} ${HELP_VALUE}web-search${RESET} ${HELP_SWITCH}--disable${RESET}

${HELP_HEADER}Models Management:${RESET}
  ${HELP_SWITCH}--install${RESET} ${HELP_VALUE}[MODEL]${RESET}
      Downloads and installs a named model. Draw Things model IDs ending in ${HELP_VALUE}.ckpt${RESET}
      are routed automatically to Draw Things; other model names default to Ollama.
      Use --backend/-b to select the backend explicitly.
      Use --type/-t to distinguish between a full model checkpoint and a LoRA source when needed.

      ${HELP_SUBTITLE}Examples:${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--install${RESET} ${HELP_VALUE}qwen3.5:4b${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--install${RESET} ${HELP_VALUE}realvisxl_v4.0_q6p_q8p.ckpt${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--install${RESET} ${HELP_VALUE}realvisxl_v4.0_q6p_q8p.ckpt${RESET} ${HELP_SWITCH}--backend${RESET} ${HELP_VALUE}draw-things${RESET}

      ${HELP_SUBTITLE}Install from source:${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--install${RESET} ${HELP_SWITCH}--source${RESET} ${HELP_VALUE}https://huggingface.co/user/model-GGUF${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--install${RESET} ${HELP_SWITCH}-s${RESET} ${HELP_VALUE}https://example.com/model.gguf${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--install${RESET} ${HELP_SWITCH}-s${RESET} ${HELP_VALUE}/Users/kamil/Downloads/model.gguf${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--install${RESET} ${HELP_SWITCH}-s${RESET} ${HELP_VALUE}https://example.com/model.safetensors${RESET} ${HELP_SWITCH}--backend${RESET} ${HELP_VALUE}draw-things${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--install${RESET} ${HELP_SWITCH}-s${RESET} ${HELP_VALUE}/Users/kamil/Downloads/model.safetensors${RESET} ${HELP_SWITCH}--backend${RESET} ${HELP_VALUE}draw-things${RESET}

        ${HELP_SWITCH}--source${RESET} accepts either an HTTP(S) URL or a local file path.
        For Ollama, Hugging Face repository URLs are converted to an Ollama ${HELP_VALUE}huggingface.co/...${RESET}
        reference, and direct ${HELP_VALUE}.gguf${RESET} files are imported with a generated local model name.
        For Draw Things, direct .ckpt and .safetensors sources can be
        downloaded or imported from a local file. When the source is a LoRA rather than a
        full checkpoint, pass --type lora so ai can use the LoRA import flow.

  ${HELP_SWITCH}--list${RESET} ${HELP_VALUE}[local|ollama|ollama-experimental|draw-things]${RESET}
      Lists the selected model catalog. Without a target, ${HELP_VALUE}local${RESET} is used.

      ${HELP_VALUE}local${RESET} shows installed Ollama models plus Draw Things models, LoRAs, and dependency/support files.
      ${HELP_VALUE}ollama${RESET} shows the online Ollama Library catalog.
      ${HELP_VALUE}ollama-experimental${RESET} shows experimental Ollama models.
      ${HELP_VALUE}draw-things${RESET} shows the online Draw Things model catalog.

      Local Draw Things rows include a ${HELP_VALUE}Type${RESET} column: ${HELP_VALUE}Model${RESET}, ${HELP_VALUE}LoRA${RESET}, ${HELP_VALUE}Dependency${RESET}, or ${HELP_VALUE}Metadata${RESET}.
      The size is read from the files currently present in the Draw Things Models directory; a matching
      ${HELP_VALUE}-tensordata${RESET} companion is counted together with its parent file instead of shown twice.
      Tables are hardware-aware and include the existing Rating estimate where size metadata is available.
      The Draw Things catalog also shows Filter: None* means no known runtime prompt/safety gate
      for that model family in the local Draw Things path; Unknown means the catalog metadata is
      insufficient to classify it. This is a technical heuristic, not a license/legal guarantee.

      In the TUI, Install Draw Things Models can sort by Filter. Local Models can sort by Backend
      and Type. Draw Things model details show known dependencies, and Dependency details show the
      installed models that use them. When uninstalling a Draw Things model, dependencies can be
      selected from a checklist. Removing a shared dependency warns about its users and offers to
      keep it, remove only the dependency, or remove the dependency together with those models.


      Previous combined-list description (for reference):

        ${HELP_SUBTITLE}1. Installed models${RESET}
           Exact local model tags from ${HELP_COMMAND}ollama list${RESET}. Status is limited to
           ${HELP_VALUE}Running${RESET}/${HELP_VALUE}Stopped${RESET}; the default model is marked with a green ${HELP_VALUE}*${RESET}
           after its name. Size, hardware Rating, Codex compatibility/coding rating, category, and description are shown.

        ${HELP_SUBTITLE}2. Available models${RESET}
           The complete Ollama Library index without a Status column. The default
           ${HELP_VALUE}latest${RESET} manifest size is fetched from the
           Ollama registry when available and used for the hardware Rating score.

           ${HELP_VALUE}Codex${RESET} first reflects tool/function-calling compatibility. ${HELP_VALUE}No${RESET} means the
           model cannot be used as a Codex agent; compatible models are then rated by
           coding quality. Remote models may show ${HELP_VALUE}Unknown${RESET} until installed.

      ${HELP_SUBTITLE}Optional:${RESET}
        ${HELP_SWITCH}--order${RESET} ${HELP_VALUE}[FIELD[,FIELD...]]${RESET}
        ${HELP_SWITCH}-o${RESET} ${HELP_VALUE}[FIELD[,FIELD...]]${RESET}
            Sorts both model tables by one or more fields, in priority order.

            ${HELP_VALUE}Fields and aliases:${RESET}
              ${HELP_VALUE}model${RESET}       = ${HELP_VALUE}name${RESET}
              ${HELP_VALUE}status${RESET}      = ${HELP_VALUE}state${RESET}
              ${HELP_VALUE}size${RESET}
              ${HELP_VALUE}rating${RESET}
              ${HELP_VALUE}codex${RESET}
              ${HELP_VALUE}category${RESET}    = ${HELP_VALUE}cat${RESET}
              ${HELP_VALUE}description${RESET} = ${HELP_VALUE}desc${RESET}

            Multiple fields use ${HELP_VALUE},${RESET} as a separator. No quoting or escaping is required.

            ${HELP_SUBTITLE}Examples:${RESET}
              ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--list${RESET} ${HELP_SWITCH}-o${RESET} ${HELP_VALUE}rating${RESET}
              ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--list${RESET} ${HELP_SWITCH}-o${RESET} ${HELP_VALUE}category,codex,rating${RESET}
              ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--list${RESET} ${HELP_SWITCH}--order${RESET} ${HELP_VALUE}cat,codex,rating${RESET}


        ${HELP_SWITCH}--asc${RESET}
            Forces ascending order for every selected sort field.

        ${HELP_SWITCH}--desc${RESET}
            Forces descending order for every selected sort field.

      Without ${HELP_SWITCH}--asc${RESET} or ${HELP_SWITCH}--desc${RESET}, each field uses its natural default:
      ${HELP_VALUE}rating${RESET} is descending (best hardware Rating first); all other fields are ascending.
      Without ${HELP_SWITCH}--order${RESET}, models are sorted by ${HELP_VALUE}model${RESET} ascending.

      The current OS, CPU/SoC, architecture, and RAM are detected automatically.
      Hardware Rating percentages are estimates. On Apple Silicon they use unified
      memory; on other systems discrete GPU VRAM is not included in the score.

      A conservative recommended model and context size are selected dynamically
      from a set of local coding/agent candidates using detected system memory.
      This may be a smaller explicit tag (for example ${HELP_VALUE}qwen3.5:4b${RESET}) even when the
      family default ${HELP_VALUE}qwen3.5:latest${RESET} is larger.

      The online Ollama Library catalog is cached for 24 hours by default.
      Set ${HELP_VALUE}AI_LIBRARY_CACHE_TTL${RESET} to another number of seconds to change this.
      If the network is unavailable, a stale cache is used when possible.

  ${HELP_SWITCH}--set-base${RESET} ${HELP_VALUE}[MODEL]${RESET}
      Sets the default model used by ${HELP_SWITCH}--run${RESET}, ${HELP_SWITCH}--chat${RESET}, ${HELP_SWITCH}--agent${RESET},
      and ${HELP_SWITCH}--stop${RESET} when ${HELP_VALUE}MODEL${RESET} is omitted. ${HELP_VALUE}MODEL${RESET} is required for this command
      and must already be installed.

  ${HELP_SWITCH}--uninstall${RESET} ${HELP_VALUE}[MODEL]${RESET}
      Stops the model if it is currently loaded, then removes it.
      ${HELP_VALUE}MODEL${RESET} is required for this command. If it was the base model, the
      base-model setting is cleared.

${HELP_HEADER}SETUP:${RESET}
  ${HELP_SWITCH}--setup${RESET}
      Checks, installs, and updates the local AI toolchain in this order:

        ${HELP_VALUE}1.${RESET} Ollama
        ${HELP_VALUE}2.${RESET} Node.js + npm
        ${HELP_VALUE}3.${RESET} Codex CLI
        ${HELP_VALUE}4.${RESET} dialog TUI

      ${HELP_COMMAND}ai${RESET} checks whether each component is installed and updates it when an
      update can be detected safely. If a checked component is already current,
      no reinstall is performed.

      If npm is missing, ${HELP_COMMAND}ai${RESET} installs nvm (if needed), then installs the
      latest Node.js LTS release with npm. Existing npm installations are
      preserved and updated in place when possible.

      Codex CLI is installed/updated with:
        ${HELP_COMMAND}npm install${RESET} ${HELP_SWITCH}-g${RESET} ${HELP_VALUE}@openai/codex@latest${RESET}

      On macOS, dialog is installed/updated with Homebrew. If Homebrew is
      missing, ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--setup${RESET} installs it first. A clean macOS installation may
      require Apple Command Line Tools; if they are missing, the system
      installer is started and setup asks you to run ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--setup${RESET} again after
      the Apple installation finishes.

      On Linux, common package managers (apt, dnf/yum, pacman, zypper) are
      used to install or update dialog.

  ${HELP_SWITCH}--purge${RESET} ${HELP_VALUE}[COMPONENT]${RESET}
      DESTRUCTIVE. Removes selected components.

      ${HELP_SUBTITLE}Without ${RESET}${HELP_VALUE}COMPONENT${RESET}${HELP_SUBTITLE}:${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--purge${RESET}
            Removes Ollama and all downloaded Ollama models.
            npm and Codex are kept.

      ${HELP_SUBTITLE}Components:${RESET}
        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--purge${RESET} ${HELP_VALUE}ollama${RESET}
            Removes only Ollama. Downloaded models are preserved so they can
            be reused after Ollama is installed again.

        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--purge${RESET} ${HELP_VALUE}models${RESET}
            Removes only downloaded Ollama models and clears the base-model
            setting. Ollama itself is kept.

        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--purge${RESET} ${HELP_VALUE}npm${RESET}
            Removes only the npm CLI. Node.js itself is left installed.

        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--purge${RESET} ${HELP_VALUE}codex${RESET}
            Removes only Codex CLI.

        ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--purge${RESET} ${HELP_VALUE}'*'${RESET}
            Removes Ollama, all models, Codex CLI, and npm.
            dialog and Homebrew are intentionally kept.
            Quote or escape ${HELP_VALUE}*${RESET} because shells expand an unquoted asterisk.
            Equivalent form: ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--purge${RESET} ${HELP_VALUE}\*${RESET}

${HELP_HEADER}PURGE CONFIRMATION:${RESET}
  Destructive ${HELP_SWITCH}--purge${RESET} operations require typing ${HELP_VALUE}PURGE${RESET} interactively.
  Set ${HELP_VALUE}AI_PURGE_FORCE=1${RESET} to skip the confirmation.

${HELP_HEADER}CONFIGURATION:${RESET}
  The base model is stored in:
    ${HELP_VALUE}~/.config/ai/base_model${RESET}

  The local Ollama API URL can be overridden with:
    ${HELP_VALUE}AI_OLLAMA_URL=http://127.0.0.1:11434${RESET} ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--list${RESET}

${HELP_HEADER}NOTES:${RESET}
  ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--run${RESET} does not open an interactive chat. It preloads the model so it
  is ready for Codex or any other tool using Ollama's local API.

  ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--chat${RESET} opens the standard interactive Ollama chat in the terminal.

  ${HELP_COMMAND}ai${RESET} ${HELP_SWITCH}--agent${RESET} uses Codex CLI with Ollama as the local model provider.
  A directory passed with ${HELP_SWITCH}--directory${RESET}/${HELP_SWITCH}-d${RESET} becomes the writable Codex workspace.
  Use ${HELP_SWITCH}--exec${RESET} ${HELP_VALUE}ask${RESET}|${HELP_VALUE}auto${RESET}|${HELP_VALUE}no-ask${RESET} to control execution approvals (default: ${HELP_VALUE}auto${RESET}).
EOF
  printf '\n'
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

require_no_extra_args() {
  [[ $# -eq 0 ]] || die "Too many arguments: $*"
}

validate_model_name() {
  local model="$1"
  [[ -n "$model" ]] || die "Model name is required."
  [[ "$model" =~ ^[A-Za-z0-9._/@:-]+$ ]] || \
    die "Invalid model name: $model"
}

normalize_model_name() {
  local model="$1"
  if [[ "$model" == *:* ]]; then
    printf '%s\n' "$model"
  else
    printf '%s:latest\n' "$model"
  fi
}

get_base_model() {
  if [[ -f "$BASE_MODEL_FILE" ]]; then
    tr -d '\r\n' < "$BASE_MODEL_FILE"
  fi
}

clear_base_if_matches() {
  local removed="$1"
  local base
  base="$(get_base_model)"

  [[ -n "$base" ]] || return 0

  if [[ "$(normalize_model_name "$removed")" == "$(normalize_model_name "$base")" ]]; then
    rm -f "$BASE_MODEL_FILE"
    warn "The removed model was the base model. The base-model setting was cleared."
  fi
}

ensure_ollama_cli() {
  command -v ollama >/dev/null 2>&1 || \
    die "Ollama is not installed. Run: ai --setup"
}

ensure_codex_cli() {
  command -v codex >/dev/null 2>&1 || \
    die "Codex CLI is not installed. Install it with: npm install -g @openai/codex"
}

api_is_ready() {
  command -v curl >/dev/null 2>&1 || return 1
  curl -fsS --connect-timeout 1 --max-time 2 "$OLLAMA_URL/api/tags" >/dev/null 2>&1
}

start_ollama_if_possible() {
  if api_is_ready; then
    return 0
  fi

  if [[ "$(uname -s 2>/dev/null || true)" == "Darwin" ]] && command -v open >/dev/null 2>&1; then
    if [[ -d /Applications/Ollama.app ]] || [[ -d "$HOME/Applications/Ollama.app" ]]; then
      info "Ollama API is not responding. Starting Ollama..."
      open -gj -a Ollama >/dev/null 2>&1 || true
    fi
  elif command -v systemctl >/dev/null 2>&1; then
    systemctl is-active --quiet ollama 2>/dev/null || sudo systemctl start ollama 2>/dev/null || true
  fi

  local i
  for ((i = 0; i < 24; i++)); do
    sleep 0.25
    api_is_ready && return 0
  done

  return 1
}

ensure_ollama_api() {
  require_cmd curl
  start_ollama_if_possible || \
    die "Ollama is not responding at $OLLAMA_URL. Start Ollama and try again."
}

model_is_installed() {
  local model="$1" installed

  command -v ollama >/dev/null 2>&1 || return 1

  # `ollama list` is the authoritative check for locally pulled models.
  # In particular, experimental image models under x/* can be present in the
  # local model store even when `ollama show` is not a reliable existence
  # probe for that model type/version. Normalize omitted tags to :latest so
  # namespaced models such as x/flux2-klein are handled consistently.
  installed="$(ollama list 2>/dev/null | awk 'NR > 1 {print $1}' || true)"
  if [[ -n "$installed" ]] && name_list_contains "$model" "$installed"; then
    return 0
  fi

  # Keep show as a compatibility fallback for Ollama versions where a model
  # may be addressable before it appears in the formatted list output.
  ollama show "$model" >/dev/null 2>&1
}

# Query a model capability from Ollama's local /api/show endpoint.  Current
# Ollama versions expose capabilities such as tools, vision, embedding and image.
# Keep this dependency-free for macOS/Bash 3.2.
model_has_capability() {
  local model="$1" capability="$2" response capabilities

  response="$(curl -fsS --connect-timeout 2 --max-time 8 \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"$model\"}" \
    "$OLLAMA_URL/api/show" 2>/dev/null)" || return 1

  capabilities="$(printf '%s' "$response" | tr '\n' ' ' | \
    sed -n 's/.*"capabilities"[[:space:]]*:[[:space:]]*\[\([^]]*\)\].*/\1/p')"
  [[ -n "$capabilities" ]] || return 1
  printf '%s\n' "$capabilities" | grep -Eq "(^|[,[:space:]])\"${capability}\"([,[:space:]]|$)"
}

# Codex agents require function/tool calling. Query the local Ollama API rather
# than Ollama's registry so unsupported models fail before Codex is started.
# Return 0 when the model advertises the `tools` capability, 1 otherwise.
model_supports_tools() {
  model_has_capability "$1" tools
}

model_supports_image_generation() {
  model_has_capability "$1" image
}

model_is_running() {
  local target running
  target="$(normalize_model_name "$1")"

  while IFS= read -r running; do
    [[ -n "$running" ]] || continue
    if [[ "$(normalize_model_name "$running")" == "$target" ]]; then
      return 0
    fi
  done < <(ollama ps 2>/dev/null | awk 'NR > 1 {print $1}')

  return 1
}

parse_context_length() {
  local raw="$1"
  local number result

  if [[ "$raw" =~ ^[0-9]+$ ]]; then
    result=$((10#$raw))
  elif [[ "$raw" =~ ^([0-9]+)[Kk]$ ]]; then
    number="${BASH_REMATCH[1]}"
    result=$((10#$number * 1024))
  elif [[ "$raw" =~ ^([0-9]+)[Mm]$ ]]; then
    number="${BASH_REMATCH[1]}"
    result=$((10#$number * 1024 * 1024))
  else
    die "Invalid context length: $raw (examples: 16384, 16K, 1M)"
  fi

  (( result > 0 )) || die "Context length must be greater than 0."
  printf '%s\n' "$result"
}

remote_library_models() {
  local html models

  command -v curl >/dev/null 2>&1 || return 1

  html="$(curl -fsSL --connect-timeout 4 --max-time 15 "${OLLAMA_LIBRARY_URL}?sort=popular" 2>/dev/null || true)"
  [[ -n "$html" ]] || return 1

  models="$(
    printf '%s' "$html" \
      | grep -oE 'href="/library/[A-Za-z0-9._-]+"' \
      | sed -E 's#href="/library/([^\"]+)"#\1#' \
      | awk '!seen[$0]++' \
      || true
  )"

  [[ -n "$models" ]] || return 1
  printf '%s\n' "$models"
}

fallback_library_models() {
  cat <<'MODELS'
qwen3.5
qwen3
qwen2.5-coder
gemma3
llama3.2
mistral
deepseek-r1
gpt-oss
qwen3-coder
codellama
starcoder2
phi4
MODELS
}

file_mtime() {
  local file="$1"
  if stat -f '%m' "$file" >/dev/null 2>&1; then
    stat -f '%m' "$file"
  elif stat -c '%Y' "$file" >/dev/null 2>&1; then
    stat -c '%Y' "$file"
  else
    printf '0\n'
  fi
}

library_cache_is_fresh() {
  [[ -s "$LIBRARY_CACHE_FILE" ]] || return 1
  [[ "$LIBRARY_CACHE_TTL" =~ ^[0-9]+$ ]] || return 1

  local now mtime age
  now="$(date +%s)"
  mtime="$(file_mtime "$LIBRARY_CACHE_FILE")"
  [[ "$mtime" =~ ^[0-9]+$ ]] || return 1
  age=$((now - mtime))
  (( age >= 0 && age < LIBRARY_CACHE_TTL ))
}

refresh_library_cache() {
  command -v curl >/dev/null 2>&1 || return 1

  local tmp_names tmp_catalog family_count jobs
  tmp_names="$(mktemp "${TMPDIR:-/tmp}/ai-library-names.XXXXXX")"
  tmp_catalog="$(mktemp "${TMPDIR:-/tmp}/ai-library-catalog.XXXXXX")"

  if ! remote_library_models > "$tmp_names"; then
    rm -f "$tmp_names" "$tmp_catalog"
    return 1
  fi

  family_count="$(awk 'NF{n++} END{print n+0}' "$tmp_names")"
  if (( family_count <= 0 )); then
    rm -f "$tmp_names" "$tmp_catalog"
    return 1
  fi

  info "Refreshing Ollama Library catalog (${family_count} model families)..." >&2

  jobs="${AI_LIBRARY_JOBS:-12}"
  [[ "$jobs" =~ ^[0-9]+$ ]] || jobs=12
  (( jobs > 0 )) || jobs=1

  # Fetch the default :latest manifest directly from Ollama's OCI registry.
  # Some networks resolve registry.ollama.ai and others registry.ollama.com,
  # so both are tried. The model layer is the useful on-disk size estimate.
  # If neither registry endpoint yields a usable manifest, scrape the public
  # model page as a fallback and read the size shown next to MODEL:latest.
  xargs -P "$jobs" -I '{}' sh -c '
    name="$1"
    registry1="$2"
    registry2="$3"
    library="$4"

    fetch_manifest() {
      curl -fsSL --connect-timeout 4 --max-time 15 \
        -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
        "$1/v2/library/$name/manifests/latest" 2>/dev/null || true
    }

    json="$(fetch_manifest "$registry1")"
    if [ -z "$json" ] || ! printf "%s" "$json" | grep -q "application/vnd.ollama.image.model"; then
      json="$(fetch_manifest "$registry2")"
    fi

    bytes=0
    for n in $(printf "%s" "$json" \
      | grep -Eo "\"size\"[[:space:]]*:[[:space:]]*[0-9]+" \
      | grep -Eo "[0-9]+"); do
      bytes=$((bytes + n))
    done

    [ -n "$bytes" ] || bytes=0

    if [ "$bytes" = "0" ]; then
      html="$(curl -fsSL --connect-timeout 4 --max-time 15 "$library/$name/tags" 2>/dev/null || true)"
      if [ -n "$html" ]; then
        flat="$(printf "%s" "$html" \
          | sed -E "s/<[^>]*>/ /g" \
          | sed "s/&nbsp;/ /g; s/&quot;/\"/g; s/&middot;/ /g" \
          | tr "\n\r\t" "   " \
          | tr -s " ")"

        size_text="$(printf "%s" "$flat" \
          | grep -Eo "$name:latest.{0,220}[0-9]+([.][0-9]+)?[[:space:]]*(TB|GB|MB)" \
          | head -n 1 \
          | grep -Eo "[0-9]+([.][0-9]+)?[[:space:]]*(TB|GB|MB)" \
          | head -n 1 \
          | tr -d " " || true)"

        if [ -n "$size_text" ]; then
          number="$(printf "%s" "$size_text" | sed -E "s/(TB|GB|MB)$//")"
          unit="$(printf "%s" "$size_text" | sed -nE "s/^.*(TB|GB|MB)$/\\1/p")"
          case "$unit" in
            TB) bytes="$(LC_NUMERIC=C awk -v n="$number" '"'"'BEGIN{printf "%.0f", n*1000000000000}'"'"')" ;;
            GB) bytes="$(LC_NUMERIC=C awk -v n="$number" '"'"'BEGIN{printf "%.0f", n*1000000000}'"'"')" ;;
            MB) bytes="$(LC_NUMERIC=C awk -v n="$number" '"'"'BEGIN{printf "%.0f", n*1000000}'"'"')" ;;
          esac
        fi
      fi
    fi

    [ -n "$bytes" ] || bytes=0
    printf "%s|%s\n" "$name" "$bytes"
  ' _ '{}' "$OLLAMA_REGISTRY_URL" "$OLLAMA_REGISTRY_FALLBACK_URL" "$OLLAMA_LIBRARY_URL" < "$tmp_names" > "$tmp_catalog"

  if [[ ! -s "$tmp_catalog" ]]; then
    rm -f "$tmp_names" "$tmp_catalog"
    return 1
  fi

  mkdir -p "$CACHE_DIR"
  LC_ALL=C sort -t '|' -k1,1 "$tmp_catalog" > "$LIBRARY_CACHE_FILE"
  rm -f "$tmp_names" "$tmp_catalog"

  local sized_count
  sized_count="$(awk -F'|' '$2 ~ /^[0-9]+$/ && $2 > 0 {n++} END{print n+0}' "$LIBRARY_CACHE_FILE")"
  success "Ollama Library catalog cached (${family_count} families, ${sized_count} with detected size)." >&2
}

remote_library_catalog() {
  if library_cache_is_fresh; then
    cat "$LIBRARY_CACHE_FILE"
    return 0
  fi

  if refresh_library_cache; then
    cat "$LIBRARY_CACHE_FILE"
    return 0
  fi

  if [[ -s "$LIBRARY_CACHE_FILE" ]]; then
    warn "Could not refresh the Ollama Library catalog. Using the cached copy."
    cat "$LIBRARY_CACHE_FILE"
    return 0
  fi

  warn "Could not download the Ollama Library catalog. Available-model sizes will be unknown."
  fallback_library_models | awk 'NF{print $0 "|0"}'
}

remote_experimental_models() {
  local html models
  command -v curl >/dev/null 2>&1 || return 1

  html="$(curl -fsSL --connect-timeout 4 --max-time 15 "$OLLAMA_EXPERIMENTAL_URL" 2>/dev/null || true)"
  [[ -n "$html" ]] || return 1

  models="$(printf '%s' "$html" \
    | grep -oE 'href="/x/[A-Za-z0-9._-]+"' \
    | sed -E 's#href="/x/([^\"]+)"#\1#' \
    | awk '!seen[$0]++' \
    || true)"

  [[ -n "$models" ]] || return 1
  printf '%s\n' "$models"
}

fallback_experimental_models() {
  cat <<'MODELS'
flux2-klein
z-image-turbo
MODELS
}

experimental_model_size_bytes() {
  local family="$1" registry json bytes=0 html flat size_text number unit

  command -v curl >/dev/null 2>&1 || {
    case "$family" in
      flux2-klein)  printf '5700000000\n' ;;
      z-image-turbo) printf '13000000000\n' ;;
      *) printf '0\n' ;;
    esac
    return 0
  }

  # Prefer the OCI manifest. Experimental models live under the x/ namespace,
  # so querying /v2/x/<family>/manifests/latest gives a more stable size source
  # than scraping the rendered model page.
  for registry in "$OLLAMA_REGISTRY_URL" "$OLLAMA_REGISTRY_FALLBACK_URL"; do
    json="$(curl -fsSL --connect-timeout 4 --max-time 15 \
      -H 'Accept: application/vnd.docker.distribution.manifest.v2+json' \
      "$registry/v2/x/$family/manifests/latest" 2>/dev/null || true)"
    [[ -n "$json" ]] || continue

    bytes="$(printf '%s' "$json" \
      | grep -Eo '"size"[[:space:]]*:[[:space:]]*[0-9]+' \
      | grep -Eo '[0-9]+' \
      | LC_ALL=C awk '{sum+=$1} END{printf "%.0f", sum+0}' || true)"
    if [[ "$bytes" =~ ^[0-9]+$ ]] && (( bytes > 0 )); then
      printf '%s\n' "$bytes"
      return 0
    fi
  done

  # Fallback: the experimental tags pages currently expose the default model
  # size directly (for example 5.7GB or 13GB). Do not depend on the model name
  # and size being adjacent in the HTML because the page layout changes often.
  html="$(curl -fsSL --connect-timeout 4 --max-time 15 "$OLLAMA_EXPERIMENTAL_URL/$family/tags" 2>/dev/null || true)"
  if [[ -n "$html" ]]; then
    flat="$(printf '%s' "$html" \
      | sed -E 's/<[^>]*>/ /g' \
      | sed 's/&nbsp;/ /g; s/&quot;/"/g; s/&middot;/ /g' \
      | tr '\n\r\t' '   ' | tr -s ' ')"
    size_text="$(printf '%s' "$flat" \
      | grep -Eo '[0-9]+([.][0-9]+)?[[:space:]]*(TB|GB|MB)' \
      | head -n 1 | tr -d ' ' || true)"

    if [[ -n "$size_text" ]]; then
      number="$(printf '%s' "$size_text" | sed -E 's/(TB|GB|MB)$//')"
      unit="$(printf '%s' "$size_text" | sed -nE 's/^.*(TB|GB|MB)$/\1/p')"
      case "$unit" in
        TB) bytes="$(LC_NUMERIC=C awk -v n="$number" 'BEGIN{printf "%.0f", n*1000000000000}')" ;;
        GB) bytes="$(LC_NUMERIC=C awk -v n="$number" 'BEGIN{printf "%.0f", n*1000000000}')" ;;
        MB) bytes="$(LC_NUMERIC=C awk -v n="$number" 'BEGIN{printf "%.0f", n*1000000}')" ;;
      esac
      if [[ "$bytes" =~ ^[0-9]+$ ]] && (( bytes > 0 )); then
        printf '%s\n' "$bytes"
        return 0
      fi
    fi
  fi

  # Last-resort defaults for the currently published image-generation families.
  # These only prevent a transient page/registry failure from degrading Rating
  # to N/A; registry/page metadata still wins whenever it is available.
  case "$family" in
    flux2-klein)   printf '5700000000\n' ;;
    z-image-turbo) printf '13000000000\n' ;;
    *)             printf '0\n' ;;
  esac
}
remote_experimental_catalog() {
  local names family bytes
  names="$(remote_experimental_models 2>/dev/null || true)"
  [[ -n "$names" ]] || names="$(fallback_experimental_models)"

  while IFS= read -r family; do
    [[ -n "$family" ]] || continue
    bytes="$(experimental_model_size_bytes "$family")"
    printf 'x/%s:latest|%s\n' "$family" "${bytes:-0}"
  done <<< "$names"
}

human_os_name() {
  case "$1" in
    Darwin) printf 'macOS\n' ;;
    Linux) printf 'Linux\n' ;;
    *) printf '%s\n' "$1" ;;
  esac
}

detect_hardware() {
  local os arch chip model ram_bytes ram_gb hw
  os="${AI_HW_OS:-$(uname -s 2>/dev/null || printf 'Unknown')}"
  arch="${AI_HW_ARCH:-$(uname -m 2>/dev/null || printf 'Unknown')}"
  chip="${AI_HW_CHIP:-}"
  model="${AI_HW_MODEL:-}"

  if [[ -n "${AI_HW_RAM_GB:-}" ]]; then
    ram_gb="$AI_HW_RAM_GB"
  else
    ram_bytes=""
    case "$os" in
      Darwin)
        ram_bytes="$(sysctl -n hw.memsize 2>/dev/null || true)"
        if [[ -z "$chip" ]]; then
          chip="$(sysctl -n machdep.cpu.brand_string 2>/dev/null || true)"
        fi
        if command -v system_profiler >/dev/null 2>&1 && { [[ -z "$chip" ]] || [[ -z "$model" ]]; }; then
          hw="$(system_profiler SPHardwareDataType -detailLevel mini 2>/dev/null || true)"
          [[ -n "$chip" ]] || chip="$(printf '%s\n' "$hw" | awk -F': ' '/^[[:space:]]*Chip:/{print $2; exit}')"
          [[ -n "$chip" ]] || chip="$(printf '%s\n' "$hw" | awk -F': ' '/^[[:space:]]*Processor Name:/{print $2; exit}')"
          [[ -n "$model" ]] || model="$(printf '%s\n' "$hw" | awk -F': ' '/^[[:space:]]*Model Name:/{print $2; exit}')"
        fi
        ;;
      Linux)
        if [[ -r /proc/meminfo ]]; then
          ram_bytes="$(awk '/^MemTotal:/{printf "%.0f", $2 * 1024; exit}' /proc/meminfo)"
        fi
        if [[ -z "$chip" ]] && command -v lscpu >/dev/null 2>&1; then
          chip="$(lscpu 2>/dev/null | awk -F: '/Model name:/{sub(/^[[:space:]]+/, "", $2); print $2; exit}')"
        fi
        ;;
    esac

    if [[ "$ram_bytes" =~ ^[0-9]+$ ]] && (( ram_bytes > 0 )); then
      ram_gb="$(LC_NUMERIC=C awk -v b="$ram_bytes" 'BEGIN { printf "%.0f", b / 1073741824 }')"
    else
      ram_gb="0"
    fi
  fi

  [[ -n "$chip" ]] || chip="$arch processor"
  [[ -n "$model" ]] || model="$(human_os_name "$os") device"
  printf '%s|%s|%s|%s|%s\n' "$os" "$arch" "$chip" "$model" "$ram_gb"
}

hardware_rating() {
  local size_gb ram_gb
  size_gb="$(normalize_decimal "$1")"
  ram_gb="$(normalize_decimal "$2")"

  if ! [[ "$size_gb" =~ ^[0-9]+([.][0-9]+)?$ ]] || ! LC_NUMERIC=C awk -v n="$size_gb" 'BEGIN{exit !(n>0)}'; then
    printf 'N/A\n'
    return 0
  fi

  if ! [[ "$ram_gb" =~ ^[0-9]+([.][0-9]+)?$ ]] || ! LC_NUMERIC=C awk -v n="$ram_gb" 'BEGIN{exit !(n>0)}'; then
    printf 'N/A\n'
    return 0
  fi

  # Convert model-size / system-memory pressure into a continuous 0-100 score.
  # The breakpoints preserve the meaning of the previous categorical scale:
  #   <=20%% Excellent, <=35%% Great, <=47%% Very good, <=55%% Good,
  #   <=65%% Tight, <=80%% Poor, >80%% No.
  # Scores are interpolated between those boundaries so the value remains
  # useful instead of merely replacing each label with a fixed number.
  LC_NUMERIC=C awk -v size="$size_gb" -v ram="$ram_gb" 'BEGIN {
    r = size / ram

    if      (r <= 0.20) score = 100 - (r / 0.20) * 5
    else if (r <= 0.35) score = 95 - ((r - 0.20) / 0.15) * 10
    else if (r <= 0.47) score = 85 - ((r - 0.35) / 0.12) * 10
    else if (r <= 0.55) score = 75 - ((r - 0.47) / 0.08) * 15
    else if (r <= 0.65) score = 60 - ((r - 0.55) / 0.10) * 20
    else if (r <= 0.80) score = 40 - ((r - 0.65) / 0.15) * 20
    else if (r <  1.00) score = 20 - ((r - 0.80) / 0.20) * 20
    else                score = 0

    if (score < 0) score = 0
    if (score > 100) score = 100
    printf "%.0f%%\n", score
  }'
}

code_rating() {
  case "$1" in
    5) printf 'Excellent\n' ;;
    4) printf 'Very good\n' ;;
    3) printf 'Good\n' ;;
    2) printf 'General\n' ;;
    *) printf 'Limited\n' ;;
  esac
}

model_category_for() {
  case "$1" in
    x/flux2-klein*|flux2-klein*|x/z-image-turbo*|z-image-turbo*) printf 'Image\n' ;;
    *embed*|bge-*) printf 'Embedding\n' ;;
    *ocr*) printf 'OCR\n' ;;
    *coder*|*code*|starcoder*|devstral*|opencoder*) printf 'Coding\n' ;;
    *vision*|llava*|minicpm-v*|*vl) printf 'Vision\n' ;;
    *translate*) printf 'Translation\n' ;;
    qwen3.5*|gemma4*|gpt-oss*) printf 'Agentic\n' ;;
    deepseek-r1*|qwq*|*reason*) printf 'Reasoning\n' ;;
    *) printf 'General\n' ;;
  esac
}

model_description_for() {
  case "$1" in
    x/flux2-klein*|flux2-klein*) printf 'FLUX.2 Klein experimental text-to-image model family\n' ;;
    x/z-image-turbo*|z-image-turbo*) printf 'Z-Image Turbo experimental photorealistic text-to-image model\n' ;;
    x/canary*|canary*) printf 'Experimental Ollama model family\n' ;;
    qwen3.6*) printf 'Qwen agentic coding and reasoning family\n' ;;
    qwen3-coder*) printf 'Qwen family specialized for agentic coding\n' ;;
    qwen2.5-coder*) printf 'Code-focused Qwen generation and fixing family\n' ;;
    qwen3.5*) printf 'Multimodal Qwen with tools and reasoning\n' ;;
    qwen3*) printf 'Qwen reasoning and tool-use family\n' ;;
    gemma4*) printf 'Google agentic, coding, reasoning and multimodal family\n' ;;
    gemma3*) printf 'Google general-purpose text and vision family\n' ;;
    gemma*) printf 'Google general-purpose language model family\n' ;;
    deepseek-coder*) printf 'DeepSeek family specialized for code\n' ;;
    deepseek-r1*) printf 'DeepSeek reasoning-focused model family\n' ;;
    codellama*) printf 'Llama-family models specialized for code\n' ;;
    starcoder2*) printf 'BigCode code-generation model family\n' ;;
    llama*) printf 'Meta general-purpose Llama model family\n' ;;
    mistral*) printf 'Mistral language model family\n' ;;
    phi*) printf 'Microsoft compact language model family\n' ;;
    *embed*|bge-*) printf 'Embedding model for search and retrieval\n' ;;
    *ocr*) printf 'Document/OCR understanding model\n' ;;
    *vision*|llava*|minicpm-v*|*vl) printf 'Vision-language model family\n' ;;
    *translate*) printf 'Translation-focused language model\n' ;;
    *) printf 'Ollama Library model family\n' ;;
  esac
}

code_score_for_model() {
  case "$1" in
    *embed*|bge-*|*ocr*) printf '1\n' ;;
    qwen3.6*|qwen3-coder*|qwen2.5-coder*|deepseek-coder*|codellama*|starcoder2*|codegemma*|devstral*|opencoder*|qwen3.5*) printf '5\n' ;;
    qwen3*|gemma4*|gpt-oss*|deepseek-r1*) printf '4\n' ;;
    qwen*|mistral*|llama*|gemma*|phi*) printf '3\n' ;;
    *) printf '2\n' ;;
  esac
}


# Return a best-effort tool-calling compatibility hint for models that are not
# installed yet. Installed models are always checked against /api/show instead.
# Exit 0 = tools known/supported, 1 = known unsupported, 2 = unknown.
model_tools_hint() {
  case "$1" in
    *embed*|bge-*|*ocr*|x/flux2-klein*|x/z-image-turbo*|flux2-klein*|z-image-turbo*|gemma3*|gemma2*|gemma:*|codellama*|starcoder*|codegemma*|deepseek-coder*) return 1 ;;
    qwen3*|qwen2.5-coder*|llama3.2*|llama3.1*|llama3-groq-tool-use*|functiongemma*|firefunction-v2*) return 0 ;;
    *) return 2 ;;
  esac
}

# Codex column semantics:
#   No       -> model cannot provide tool/function calling required by Codex
#   Unknown  -> remote model has not been installed and compatibility is unknown
#   Limited..Excellent -> Codex-compatible, then rated for coding quality.
codex_rating_for_model() {
  local model="$1" mode="${2:-remote}" score hint_status
  score="$(code_score_for_model "$model")"

  if [[ "$mode" == "installed" ]]; then
    if model_supports_tools "$model"; then
      code_rating "$score"
    else
      printf 'No\n'
    fi
    return 0
  fi

  if model_tools_hint "$model"; then
    code_rating "$score"
    return 0
  else
    hint_status=$?
  fi
  if (( hint_status == 1 )); then
    printf 'No\n'
  else
    printf 'Unknown\n'
  fi
}

name_list_contains() {
  local target="$1" names="$2" name
  target="$(normalize_model_name "$target")"
  while IFS= read -r name; do
    [[ -n "$name" ]] || continue
    if [[ "$(normalize_model_name "$name")" == "$target" ]]; then
      return 0
    fi
  done <<< "$names"
  return 1
}

model_status() {
  local model="$1" base="$2" installed="$3" running="$4"
  local is_base=0 is_installed=0 is_running=0

  [[ -n "$base" ]] && [[ "$(normalize_model_name "$base")" == "$(normalize_model_name "$model")" ]] && is_base=1
  name_list_contains "$model" "$installed" && is_installed=1 || true
  name_list_contains "$model" "$running" && is_running=1 || true

  if (( is_base && is_running )); then printf 'base/run\n'
  elif (( is_base && is_installed )); then printf 'base\n'
  elif (( is_running )); then printf 'running\n'
  elif (( is_installed )); then printf 'installed\n'
  else printf 'available\n'
  fi
}

normalize_decimal() {
  local value="$1"
  value="${value//,/.}"
  printf '%s\n' "$value"
}

installed_models_data() {
  command -v ollama >/dev/null 2>&1 || return 0
  # Force a neutral numeric locale and normalize again as a defensive fallback.
  LC_ALL=C ollama list 2>/dev/null \
    | awk 'NR > 1 && NF >= 4 { print $1 "|" $3 " " $4 }' \
    | tr ',' '.'
}

size_to_gb() {
  local value unit
  value="$(normalize_decimal "$1")"
  unit="$(printf '%s' "$2" | tr '[:lower:]' '[:upper:]')"
  LC_NUMERIC=C awk -v n="$value" -v u="$unit" 'BEGIN {
    if (n <= 0) { print "0"; exit }
    if (u == "TB" || u == "TIB") printf "%.4f", n * 1024
    else if (u == "GB" || u == "GIB") printf "%.4f", n
    else if (u == "MB" || u == "MIB") printf "%.4f", n / 1024
    else if (u == "KB" || u == "KIB") printf "%.6f", n / 1048576
    else printf "0"
  }'
}

bytes_to_gb() {
  local bytes="$1"
  if ! [[ "$bytes" =~ ^[0-9]+$ ]] || (( bytes <= 0 )); then
    printf '0\n'
    return 0
  fi
  LC_NUMERIC=C awk -v b="$bytes" 'BEGIN { printf "%.4f", b / 1000000000 }'
}

format_size_gb() {
  local gb
  gb="$(normalize_decimal "$1")"
  if ! LC_NUMERIC=C awk -v n="$gb" 'BEGIN{exit !(n>0)}'; then
    printf '%s\n' '-'
  elif LC_NUMERIC=C awk -v n="$gb" 'BEGIN{exit !(n>=10)}'; then
    LC_NUMERIC=C awk -v n="$gb" 'BEGIN{printf "%.0f GB\n", n}'
  else
    LC_NUMERIC=C awk -v n="$gb" 'BEGIN{printf "%.1f GB\n", n}'
  fi
}

normalize_list_order() {
  local raw="${1:-}" part lower canonical normalized=""
  local -a parts

  [[ -n "$raw" ]] || die "--order requires at least one field."

  # Comma is the public separator for sort priority. The function returns
  # canonical keys joined by | internally because model rows already use that
  # delimiter elsewhere in the script.
  IFS=',' read -r -a parts <<< "$raw"
  [[ ${#parts[@]} -gt 0 ]] || die "--order requires at least one field."

  for part in "${parts[@]}"; do
    part="$(printf '%s' "$part" | tr -d '[:space:]')"
    [[ -n "$part" ]] || die "Invalid empty field in --order: $raw"
    lower="$(printf '%s' "$part" | tr '[:upper:]' '[:lower:]')"

    case "$lower" in
      model|name) canonical="model" ;;
      status|state) canonical="status" ;;
      size) canonical="size" ;;
      rating|fit) canonical="rating" ;;
      codex|code) canonical="codex" ;;
      category|cat) canonical="category" ;;
      description|desc) canonical="description" ;;
      *)
        die "Unknown --order field: $part. Expected: model/name, status/state, size, rating, codex, category/cat, or description/desc."
        ;;
    esac

    # Keep the first occurrence only; repeated sort keys add no useful
    # information and can make the effective ordering harder to understand.
    case "|$normalized|" in
      *"|$canonical|"*) ;;
      *)
        if [[ -n "$normalized" ]]; then
          normalized="${normalized}|${canonical}"
        else
          normalized="$canonical"
        fi
        ;;
    esac
  done

  printf '%s\n' "$normalized"
}

normalize_tui_sort_spec() {
  local raw="${1:-}" token key direction normalized=""
  local -a tokens

  [[ -n "$raw" ]] || raw="status:desc|rating:desc|size:asc|model:asc|codex:asc|category:asc"
  IFS='|' read -r -a tokens <<< "$raw"

  for token in "${tokens[@]}"; do
    key="${token%%:*}"
    direction="${token#*:}"

    case "$key" in
      model|status|size|rating|codex|category) ;;
      *) die "Internal error: unsupported TUI sort field: $key" ;;
    esac

    if [[ "$token" != *:* ]]; then
      if [[ "$key" == "rating" ]]; then direction="desc"; else direction="asc"; fi
    fi
    [[ "$direction" == "asc" || "$direction" == "desc" ]] || \
      die "Internal error: unsupported TUI sort direction: $direction"

    case "|$normalized|" in
      *"|$key:"*) ;;
      *)
        if [[ -n "$normalized" ]]; then
          normalized="${normalized}|${key}:${direction}"
        else
          normalized="${key}:${direction}"
        fi
        ;;
    esac
  done

  printf '%s\n' "$normalized"
}

sort_model_rows() {
  local input="$1" output="$2" order_spec="$3" direction_override="$4"
  local enriched tab token key token_direction direction spec has_model=0
  local -a keys sort_args

  enriched="$(mktemp "${TMPDIR:-/tmp}/ai-sort.XXXXXX")"
  tab="$(printf '\t')"

  # Append semantic numeric keys after the seven display columns:
  #   8 = status lifecycle rank
  #   9 = size in GB
  #  10 = hardware Rating percentage
  #  11 = Codex compatibility/coding-quality rank
  LC_ALL=C awk -F '\t' 'BEGIN { OFS="\t" }
    NF >= 7 {
      status_rank=0
      if      ($2=="available") status_rank=1
      else if ($2=="stopped" || $2=="Stopped")   status_rank=2
      else if ($2=="installed") status_rank=2
      else if ($2=="running" || $2=="Running")   status_rank=3
      else if ($2=="base")      status_rank=4
      else if ($2=="base/run")  status_rank=5

      size_num=$3
      gsub(/[^0-9.]/,"",size_num)
      if (size_num=="") size_num=0

      rating_num=$4
      gsub(/[^0-9.]/,"",rating_num)
      if (rating_num=="") rating_num=-1

      codex_rank=0
      if      ($5=="No")        codex_rank=0
      else if ($5=="Unknown")   codex_rank=1
      else if ($5=="Limited")   codex_rank=2
      else if ($5=="General")   codex_rank=3
      else if ($5=="Good")      codex_rank=4
      else if ($5=="Very good") codex_rank=5
      else if ($5=="Excellent") codex_rank=6

      print $0, status_rank, size_num, rating_num, codex_rank
    }
  ' "$input" > "$enriched"

  IFS='|' read -r -a keys <<< "$order_spec"
  sort_args=( -s -t "$tab" )

  for token in "${keys[@]}"; do
    key="${token%%:*}"
    token_direction=""
    if [[ "$token" == *:* ]]; then
      token_direction="${token#*:}"
    fi

    if [[ "$direction_override" == "per-field" ]]; then
      direction="$token_direction"
      if [[ "$direction" != "asc" && "$direction" != "desc" ]]; then
        if [[ "$key" == "rating" ]]; then direction="desc"; else direction="asc"; fi
      fi
    else
      direction="$direction_override"
      if [[ "$direction" == "auto" ]]; then
        if [[ "$key" == "rating" ]]; then direction="desc"; else direction="asc"; fi
      fi
    fi

    case "$key" in
      model)       spec="1,1"; has_model=1 ;;
      status)      spec="8,8n" ;;
      size)        spec="9,9n" ;;
      rating)      spec="10,10n" ;;
      codex)       spec="11,11n" ;;
      category)    spec="6,6" ;;
      description) spec="7,7" ;;
      *) rm -f "$enriched"; die "Internal error: unsupported sort field: $key" ;;
    esac

    if [[ "$direction" == "desc" ]]; then
      spec="${spec}r"
    fi
    sort_args+=( "-k${spec}" )
  done

  # Stable sorting preserves source order for ties. Add model as a deterministic
  # final key only when it was not explicitly requested.
  if (( has_model == 0 )); then
    sort_args+=( "-k1,1" )
  fi

  if ! LC_ALL=C sort "${sort_args[@]}" "$enriched" | cut -f1-7 > "$output"; then
    rm -f "$enriched"
    return 1
  fi
  rm -f "$enriched"
}

terminal_columns() {
  local cols=""

  if [[ "${AI_TERMINAL_COLUMNS_OVERRIDE:-}" =~ ^[0-9]+$ ]] && (( AI_TERMINAL_COLUMNS_OVERRIDE >= 20 )); then
    printf '%s
' "$AI_TERMINAL_COLUMNS_OVERRIDE"
    return 0
  fi

  # Prefer the live TTY geometry. Shell variables such as COLUMNS may be
  # inherited with a stale value (commonly 80) after the terminal is resized.
  # stty asks the controlling terminal directly and is therefore the most
  # reliable source on macOS Terminal, iTerm2 and VS Code integrated terminals.
  if [[ -r /dev/tty ]]; then
    cols="$(stty size < /dev/tty 2>/dev/null | awk '{print $2}' || true)"
  fi

  # Fallback to tput if no controlling TTY is available or stty failed.
  if [[ ! "$cols" =~ ^[0-9]+$ ]] || (( cols < 20 )); then
    cols="$(tput cols 2>/dev/null || true)"
  fi

  # Only then trust COLUMNS. It is useful for redirected/test output, but can
  # be stale in interactive shells after a window resize.
  if [[ ! "$cols" =~ ^[0-9]+$ ]] || (( cols < 20 )); then
    cols="${COLUMNS:-}"
  fi

  if [[ ! "$cols" =~ ^[0-9]+$ ]] || (( cols < 20 )); then
    cols=120
  fi

  printf '%s\n' "$cols"
}

print_dynamic_model_table() {
  local file="$1" mode="${2:-installed}" base="${3:-}" cols normalized_base=""
  cols="$(terminal_columns)"

  if [[ -n "$base" ]]; then
    normalized_base="$(normalize_model_name "$base")"
  fi

  LC_ALL=C awk -F '	' -v term="$cols" \
    -v mode="$mode" -v base="$normalized_base" \
    -v reset="$RESET" \
    -v header_color="$LIST_HEADER" \
    -v model_color="$LIST_MODEL" \
    -v size_color="$LIST_SIZE" \
    -v description_color="$LIST_DESCRIPTION" \
    -v separator_color="$LIST_SEPARATOR" \
    -v star_color="$BRIGHT_GREEN" \
    -v white="$WHITE" -v bright_white="$BRIGHT_WHITE" \
    -v red="$RED" -v bright_red="$BRIGHT_RED" \
    -v green="$GREEN" -v bright_green="$BRIGHT_GREEN" \
    -v yellow="$YELLOW" -v bright_yellow="$BRIGHT_YELLOW" \
    -v blue="$BLUE" -v bright_blue="$BRIGHT_BLUE" \
    -v magenta="$MAGENTA" -v bright_magenta="$BRIGHT_MAGENTA" \
    -v cyan="$CYAN" -v bright_cyan="$BRIGHT_CYAN" \
    -v dim="$DIM" '
    BEGIN {
      if (term > 1) term = term - 1

      if (mode == "available") {
        ncols=6
        src[1]=1; src[2]=3; src[3]=4; src[4]=5; src[5]=6; src[6]=7
        h[1]="Model"; h[2]="Size"; h[3]="Rating"; h[4]="Codex"; h[5]="Category"; h[6]="Description"
      } else if (mode == "experimental") {
        ncols=5
        src[1]=1; src[2]=3; src[3]=4; src[4]=6; src[5]=7
        h[1]="Model"; h[2]="Size"; h[3]="Rating"; h[4]="Category"; h[5]="Description"
      } else {
        ncols=7
        for(i=1;i<=7;i++) src[i]=i
        h[1]="Model"; h[2]="Status"; h[3]="Size"; h[4]="Rating"
        h[5]="Codex"; h[6]="Category"; h[7]="Description"
      }

      for(i=1;i<=ncols;i++) maxw[i]=length(h[i])
    }
    function normalized_model(v){
      if (index(v, ":") == 0) return v ":latest"
      return v
    }
    function is_base_model(v){
      return (mode == "installed" && base != "" && normalized_model(v) == base)
    }
    function cut_description(s,w){
      if (w <= 0) return ""
      if (length(s) <= w) return s
      if (w <= 3) return substr(s,1,w)
      return substr(s,1,w-3) "..."
    }
    function dashes(w,   x,i){ x=""; for(i=0;i<w;i++) x=x "-"; return x }
    function status_color(v){
      if (v=="Running" || v=="running") return bright_green
      if (v=="Stopped" || v=="stopped") return dim white
      if (v=="base/run")  return bright_magenta
      if (v=="base")      return magenta
      if (v=="installed") return green
      if (v=="available") return dim white
      return white
    }
    function fit_color(v, n){
      n=v; gsub(/[^0-9.]/,"",n)
      if (n=="") return dim white
      n+=0
      if (n>=80) return bright_green
      if (n>=60) return green
      if (n>=40) return yellow
      if (n>=20) return bright_yellow
      return bright_red
    }
    function code_color(v){
      if (v=="Excellent") return bright_green
      if (v=="Very good") return green
      if (v=="Good") return bright_cyan
      if (v=="General") return yellow
      if (v=="Limited") return bright_red
      return white
    }
    function category_color(v){
      if (v=="Coding") return bright_cyan
      if (v=="Agentic") return bright_magenta
      if (v=="Reasoning") return magenta
      if (v=="Vision") return bright_blue
      if (v=="Embedding") return blue
      if (v=="OCR") return bright_yellow
      if (v=="Translation") return cyan
      if (v=="Image") return bright_yellow
      return bright_white
    }
    function source_color(idx,v){
      if (idx==2) return status_color(v)
      if (idx==3) return size_color
      if (idx==4) return fit_color(v)
      if (idx==5) return code_color(v)
      if (idx==6) return category_color(v)
      if (idx==7) return description_color
      return white
    }
    function print_model_cell(v,w, marked, used){
      marked=is_base_model(v)
      printf "%s%s%s", model_color, v, reset
      used=length(v)
      if (marked) {
        printf " %s*%s", star_color, reset
        used+=2
      }
      if (w>used) printf "%*s", w-used, ""
    }
    function print_plain_cell(v,w,color,right){
      if (right) printf "%s%*s%s", color,w,v,reset
      else       printf "%s%-*s%s", color,w,v,reset
    }
    NF >= 7 {
      row[++n]=$0
      for(j=1;j<=ncols;j++) {
        idx=src[j]
        val=$idx
        extra=(j==1 && is_base_model(val)) ? 2 : 0
        if (length(val)+extra > maxw[j]) maxw[j]=length(val)+extra
      }
    }
    END {
      desc=ncols
      sep=2*(ncols-1)
      fixed=sep
      for(i=1;i<desc;i++) { w[i]=maxw[i]; fixed+=w[i] }
      remaining=term-fixed

      if (remaining >= maxw[desc]) w[desc]=maxw[desc]
      else if (remaining >= length(h[desc])) w[desc]=remaining
      else w[desc]=0

      visible=ncols
      if (w[desc] <= 0) visible=ncols-1

      for(j=1;j<=visible;j++) {
        if (j>1) printf "  "
        if (j==2 && (mode=="available" || mode=="experimental"))
          print_plain_cell(h[j],w[j],header_color,1)
        else
          print_plain_cell(cut_description(h[j],w[j]),w[j],header_color,0)
      }
      printf "\n"

      for(j=1;j<=visible;j++) {
        if (j>1) printf "  "
        print_plain_cell(dashes(w[j]),w[j],separator_color,(j==2 && (mode=="available" || mode=="experimental")))
      }
      printf "\n"

      for(r=1;r<=n;r++) {
        split(row[r],a,"\t")
        for(j=1;j<=visible;j++) {
          if (j>1) printf "  "
          idx=src[j]
          val=a[idx]
          if (j==1) {
            print_model_cell(val,w[j])
          } else {
            if (j==visible && idx==7) val=cut_description(val,w[j])
            print_plain_cell(val,w[j],source_color(idx,val),(idx==3))
          }
        }
        printf "\n"
      }
    }
  ' "$file"
}

recommended_model_for_hardware() {
  local ram_gb
  ram_gb="$(normalize_decimal "$1")"

  if ! [[ "$ram_gb" =~ ^[0-9]+([.][0-9]+)?$ ]] || ! LC_NUMERIC=C awk -v n="$ram_gb" 'BEGIN{exit !(n>0)}'; then
    printf 'unknown\n'
    return 0
  fi

  # Candidate list: model|size_GB|coding_score|agent_bonus.
  # Models above ~48% of system RAM are rejected to leave room for the OS,
  # KV/context cache, editor, Docker, and other development tools.
  LC_NUMERIC=C awk -F'|' -v ram="$ram_gb" '
    {
      ratio=$2/ram
      if(ratio<=0.48){
        score=($3*100)+($4*20)+(ratio*30)
        if(score>best){best=score; model=$1}
      }
    }
    END{ if(model!="") print model; else print "qwen3.5:0.8b" }
  ' <<'CANDIDATES'
qwen3.5:0.8b|1.0|4|2
qwen3.5:2b|2.7|4|2
qwen3.5:4b|3.4|5|2
qwen3.5:9b|6.6|5|2
qwen3:4b|2.5|4|1
qwen3:8b|5.2|4|1
qwen2.5-coder:3b|1.9|5|1
qwen2.5-coder:7b|4.7|5|1
gemma3:4b|3.3|3|0
CANDIDATES
}

recommended_context_for_hardware() {
  local ram_gb="$1"
  ram_gb="$(normalize_decimal "$ram_gb")"
  if ! [[ "$ram_gb" =~ ^[0-9]+([.][0-9]+)?$ ]] || ! LC_NUMERIC=C awk -v n="$ram_gb" 'BEGIN{exit !(n>0)}'; then
    printf '16K\n'
    return 0
  fi
  awk -v ram="$ram_gb" 'BEGIN {
    if      (ram >= 32) print "64K"
    else if (ram >= 16) print "32K"
    else                print "16K"
  }'
}

collect_experimental_model_rows() {
  local output="$1" order_spec="$2" direction="$3" ram_gb="$4" skip_installed="${5:-0}"
  local catalog unsorted installed model bytes size_gb display_size rating category description
  catalog="$(mktemp -t ai-experimental-catalog.XXXXXX)"
  unsorted="$(mktemp -t ai-experimental-unsorted.XXXXXX)"
  : > "$catalog"
  : > "$unsorted"

  remote_experimental_catalog > "$catalog" 2>/dev/null || true
  installed=""
  if (( skip_installed == 1 )) && command -v ollama >/dev/null 2>&1; then
    installed="$(ollama list 2>/dev/null | awk 'NR > 1 {print $1}' || true)"
  fi

  while IFS='|' read -r model bytes; do
    [[ -n "$model" ]] || continue
    if (( skip_installed == 1 )) && name_list_contains "$model" "$installed"; then
      continue
    fi
    size_gb="$(bytes_to_gb "$bytes")"
    display_size="$(format_size_gb "$size_gb")"
    rating="$(hardware_rating "$size_gb" "$ram_gb")"
    category="$(model_category_for "$model")"
    description="$(model_description_for "$model")"
    printf '%s\tavailable\t%s\t%s\tN/A\t%s\t%s\n' \
      "$model" "$display_size" "$rating" "$category" "$description" >> "$unsorted"
  done < "$catalog"

  sort_model_rows "$unsorted" "$output" "$order_spec" "$direction"
  rm -f "$catalog" "$unsorted"
}

list_models() {
  local order_spec="${1:-model}" sort_direction="${2:-auto}" include_experimental="${3:-0}"
  local hw os arch chip device ram_gb base installed running
  local name size_text size_value size_unit size_gb fit code_score code category description status
  local family bytes display_size
  local catalog_file installed_rows available_rows installed_sorted available_sorted recommendation recommendation_context

  order_spec="$(normalize_list_order "$order_spec")"

  hw="$(detect_hardware)"
  IFS='|' read -r os arch chip device ram_gb <<< "$hw"
  base="$(get_base_model)"

  installed=""
  running=""
  if command -v ollama >/dev/null 2>&1; then
    if start_ollama_if_possible; then
      installed="$(ollama list 2>/dev/null | awk 'NR > 1 {print $1}' || true)"
      running="$(ollama ps 2>/dev/null | awk 'NR > 1 {print $1}' || true)"
    else
      warn "Ollama is installed, but its local API is not responding. Running status may be incomplete."
      installed="$(ollama list 2>/dev/null | awk 'NR > 1 {print $1}' || true)"
    fi
  fi

  catalog_file="$(mktemp "${TMPDIR:-/tmp}/ai-library.XXXXXX")"
  installed_rows="$(mktemp "${TMPDIR:-/tmp}/ai-installed-rows.XXXXXX")"
  available_rows="$(mktemp "${TMPDIR:-/tmp}/ai-available-rows.XXXXXX")"
  installed_sorted="$(mktemp "${TMPDIR:-/tmp}/ai-installed-sorted.XXXXXX")"
  available_sorted="$(mktemp "${TMPDIR:-/tmp}/ai-available-sorted.XXXXXX")"
  trap 'rm -f "$catalog_file" "$installed_rows" "$available_rows" "$installed_sorted" "$available_sorted"' RETURN 2>/dev/null || true

  # Resolve/refresh the online catalog before printing the Available-models
  # section so progress messages never appear inside the table.
  remote_library_catalog > "$catalog_file"

  while IFS='|' read -r name size_text; do
    [[ -n "$name" ]] || continue
    size_value="${size_text%% *}"
    size_unit="${size_text##* }"
    size_gb="$(size_to_gb "$size_value" "$size_unit")"
    fit="$(hardware_rating "$size_gb" "$ram_gb")"
    code_score="$(code_score_for_model "$name")"
    code="$(codex_rating_for_model "$name" installed)"
    category="$(model_category_for "$name")"
    description="$(model_description_for "$name")"
    if name_list_contains "$name" "$running"; then
      status="Running"
    else
      status="Stopped"
    fi
    display_size="$(format_size_gb "$size_gb")"
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$name" "$status" "$display_size" "$fit" "$code" "$category" "$description" >> "$installed_rows"
  done < <(installed_models_data)

  while IFS='|' read -r family bytes; do
    [[ -n "$family" ]] || continue
    name="${family}:latest"
    size_gb="$(bytes_to_gb "$bytes")"
    display_size="$(format_size_gb "$size_gb")"
    fit="$(hardware_rating "$size_gb" "$ram_gb")"
    code_score="$(code_score_for_model "$family")"
    code="$(codex_rating_for_model "$family" remote)"
    category="$(model_category_for "$family")"
    description="$(model_description_for "$family")"
    status="$(model_status "$name" "$base" "$installed" "$running")"
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$name" "$status" "$display_size" "$fit" "$code" "$category" "$description" >> "$available_rows"
  done < "$catalog_file"

  sort_model_rows "$installed_rows" "$installed_sorted" "$order_spec" "$sort_direction"
  sort_model_rows "$available_rows" "$available_sorted" "$order_spec" "$sort_direction"

  recommendation="$(recommended_model_for_hardware "$ram_gb")"
  recommendation_context="$(recommended_context_for_hardware "$ram_gb")"

  printf '%s%b%s\n' "$LIST_HEADER" 'Hardware:' "$RESET"
  printf '  %s%-13s%s %s%s%s\n' "$LIST_LABEL" 'Device:' "$RESET" "$LIST_VALUE" "$device" "$RESET"
  printf '  %s%-13s%s %s%s%s\n' "$LIST_LABEL" 'CPU / SoC:' "$RESET" "$LIST_VALUE" "$chip" "$RESET"
  printf '  %s%-13s%s %s%s%s\n' "$LIST_LABEL" 'Architecture:' "$RESET" "$LIST_VALUE" "$arch" "$RESET"
  if [[ "$ram_gb" != "0" ]]; then
    if [[ "$os" == "Darwin" && "$arch" == "arm64" ]]; then
      printf '  %s%-13s%s %s%s GB unified%s\n' "$LIST_LABEL" 'Memory:' "$RESET" "$LIST_VALUE" "$ram_gb" "$RESET"
    else
      printf '  %s%-13s%s %s%s GB RAM%s\n' "$LIST_LABEL" 'Memory:' "$RESET" "$LIST_VALUE" "$ram_gb" "$RESET"
    fi
  else
    printf '  %s%-13s%s %sunknown%s\n' "$LIST_LABEL" 'Memory:' "$RESET" "$LIST_VALUE" "$RESET"
  fi
  printf '  %s%-13s%s %s%s%s\n' "$LIST_LABEL" 'Base model:' "$RESET" "$LIST_VALUE" "${base:-not set}" "$RESET"
  printf '  %s%-13s%s %s%s%s %s(suggested context: %s)%s\n' \
    "$LIST_LABEL" 'Recommended:' "$RESET" "$BRIGHT_GREEN" "$recommendation" "$RESET" \
    "$DIM" "$recommendation_context" "$RESET"

  printf '\n%s%s%s\n' "$LIST_HEADER" 'Installed models:' "$RESET"
  if [[ -s "$installed_sorted" ]]; then
    print_dynamic_model_table "$installed_sorted" installed "$base"
  else
    printf '%s%s%s\n' "$DIM" '(no local models installed)' "$RESET"
  fi

  printf '\n%s%s%s\n' "$LIST_HEADER" 'Available models (complete Ollama Library):' "$RESET"
  if [[ -s "$available_sorted" ]]; then
    print_dynamic_model_table "$available_sorted" available
  else
    printf '%s%s%s\n' "$DIM" '(no available models could be loaded)' "$RESET"
  fi

  if (( include_experimental == 1 )); then
    local experimental_rows
    experimental_rows="$(mktemp -t ai-experimental-rows.XXXXXX)"
    : > "$experimental_rows"
    collect_experimental_model_rows "$experimental_rows" "$order_spec" "$sort_direction" "$ram_gb" 0
    printf '\n%s%s%s\n' "$LIST_HEADER" 'Experimental Ollama models:' "$RESET"
    if [[ -s "$experimental_rows" ]]; then
      print_dynamic_model_table "$experimental_rows" experimental
    else
      printf '%s%s%s\n' "$DIM" '(no experimental models could be loaded)' "$RESET"
    fi
    rm -f "$experimental_rows"
  fi

  local known_size total_count
  total_count="$(awk 'NF{n++} END{print n+0}' "$catalog_file")"
  known_size="$(awk -F'|' '$2 ~ /^[0-9]+$/ && $2 > 0 {n++} END{print n+0}' "$catalog_file")"

  printf '\n%b\n' "${DIM}Rating is a 0-100% hardware compatibility score calculated from model size versus detected system memory;${RESET}"
  printf '%b\n' "${DIM}Context length adds additional memory pressure.${RESET}"
  printf '%b\n' "${DIM}Catalog size metadata detected for ${known_size}/${total_count} families.${RESET}"
  printf '%b\n' "${DIM}A dash/N/A means Ollama did not expose a usable local size for that default model.${RESET}"
  printf '%b\n' "${DIM}Recommended model is a conservative local coding/agent choice and leaves memory headroom${RESET}"
  printf '%b\n' "${DIM}for the OS, editor, context cache, and Docker.${RESET}"
  printf '%b\n' "${DIM}Available rows rate each family's default :latest tag;${RESET}"
  printf '%b\n' "${DIM}The recommendation may intentionally select a smaller explicit tag better suited to this hardware.${RESET}"
  printf '%b\n' "${DIM}Library catalog entries are cached in ~/.cache/ai/ollama-library-v3.tsv for 24 hours by default.${RESET}"

  rm -f "$catalog_file" "$installed_rows" "$available_rows" "$installed_sorted" "$available_sorted"
  trap - RETURN 2>/dev/null || true
}

extract_version() {
  grep -Eo '[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z]+)*' | head -n 1
}

component_version_or_missing() {
  local command_name="$1"
  shift

  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf '%s\n' 'not installed'
    return 0
  fi

  local version
  version="$("$@" 2>/dev/null | extract_version || true)"
  if [[ -n "$version" ]]; then
    printf 'v%s\n' "$version"
  else
    printf '%s\n' 'installed (version unknown)'
  fi
}

show_versions() {
  local ollama_version npm_version codex_version

  ollama_version="$(component_version_or_missing ollama ollama --version)"

  if command -v npm >/dev/null 2>&1; then
    npm_version="$(npm --version 2>/dev/null || true)"
    if [[ -n "$npm_version" ]]; then
      npm_version="v$npm_version"
    else
      npm_version="installed (version unknown)"
    fi
  else
    npm_version="not installed"
  fi

  codex_version="$(component_version_or_missing codex codex --version)"

  printf '%-22s %s\n' 'AI Model Manager:' "v$SCRIPT_VERSION"
  printf '%-22s %s\n' 'Ollama:' "$ollama_version"
  printf '%-22s %s\n' 'npm:' "$npm_version"
  printf '%-22s %s\n' 'Codex:' "$codex_version"
}

latest_github_release_version() {
  local repo="$1"
  local url tag

  url="$(curl -fsSL -o /dev/null -w '%{url_effective}' "https://github.com/$repo/releases/latest" 2>/dev/null || true)"
  [[ -n "$url" ]] || return 1
  url="${url%/}"
  tag="${url##*/}"
  tag="${tag#v}"
  [[ "$tag" =~ ^[0-9]+\.[0-9]+\.[0-9]+ ]] || return 1
  printf '%s
' "$tag"
}

load_homebrew_if_present() {
  if command -v brew >/dev/null 2>&1; then
    return 0
  fi

  local brew_bin
  for brew_bin in /opt/homebrew/bin/brew /usr/local/bin/brew /home/linuxbrew/.linuxbrew/bin/brew; do
    if [[ -x "$brew_bin" ]]; then
      # Load Homebrew into the current process even if the user's shell profile
      # has not yet been updated after a fresh Homebrew installation.
      eval "$("$brew_bin" shellenv)"
      command -v brew >/dev/null 2>&1 && return 0
    fi
  done

  return 1
}

ensure_macos_command_line_tools() {
  [[ "$(uname -s 2>/dev/null || true)" == "Darwin" ]] || return 0

  if xcode-select -p >/dev/null 2>&1; then
    return 0
  fi

  info "Apple Command Line Tools are required before Homebrew can be installed."
  info "Starting the macOS Command Line Tools installer..."
  xcode-select --install >/dev/null 2>&1 || true
  die "Complete the Apple Command Line Tools installation, then run: ai --setup"
}

install_homebrew_if_needed() {
  load_homebrew_if_present && return 0

  [[ "$(uname -s 2>/dev/null || true)" == "Darwin" ]] || \
    die "Homebrew auto-install is only used on macOS."

  require_cmd curl
  ensure_macos_command_line_tools

  local installer
  installer="$(mktemp -t ai-homebrew-install.XXXXXX)"

  info "Homebrew is not installed. Installing it now..."
  curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh -o "$installer"

  # The official Homebrew installer may ask for confirmation/sudo in an
  # interactive terminal. Do not force NONINTERACTIVE here.
  /bin/bash "$installer"
  rm -f "$installer"

  load_homebrew_if_present || \
    die "Homebrew installation finished, but brew could not be loaded. Open a new terminal and run: ai --setup"

  success "Homebrew is installed."
}

dialog_version_string() {
  if ! command -v dialog >/dev/null 2>&1; then
    printf '%s\n' 'not installed'
    return 0
  fi

  local version
  version="$(dialog --version 2>&1 | head -n 1 | sed -E 's/^[Vv]ersion:[[:space:]]*//')"
  [[ -n "$version" ]] || version="installed"
  printf '%s\n' "$version"
}

install_or_update_dialog() {
  local os
  os="$(uname -s 2>/dev/null || true)"

  case "$os" in
    Darwin)
      # If a non-Homebrew dialog is already available, keep it rather than
      # replacing an installation we do not own.
      if command -v dialog >/dev/null 2>&1; then
        load_homebrew_if_present || true
        if ! command -v brew >/dev/null 2>&1 || ! brew list --formula dialog >/dev/null 2>&1; then
          success "dialog is already installed ($(dialog_version_string))."
          return 0
        fi
      fi

      install_homebrew_if_needed

      info "Refreshing Homebrew metadata for dialog..."
      brew update --quiet >/dev/null 2>&1 || warn "Homebrew metadata refresh failed; continuing with the current metadata."

      if brew list --formula dialog >/dev/null 2>&1; then
        if brew outdated --formula dialog 2>/dev/null | grep -qx 'dialog'; then
          info "Updating dialog..."
          brew upgrade dialog
          success "dialog updated ($(dialog_version_string))."
        else
          success "dialog is already installed and up to date ($(dialog_version_string))."
        fi
      else
        info "dialog is not installed. Installing it through Homebrew..."
        brew install dialog
        command -v dialog >/dev/null 2>&1 || load_homebrew_if_present || true
        command -v dialog >/dev/null 2>&1 || die "Homebrew installed dialog, but the dialog command is not available in PATH."
        success "dialog installed ($(dialog_version_string))."
      fi
      ;;

    Linux)
      # Package-manager install commands also upgrade dialog when a newer
      # repository version is available.
      if command -v apt-get >/dev/null 2>&1; then
        info "Installing/updating dialog with apt..."
        if [[ "$(id -u)" == "0" ]]; then
          apt-get update
          apt-get install -y dialog
        else
          require_cmd sudo
          sudo apt-get update
          sudo apt-get install -y dialog
        fi
      elif command -v dnf >/dev/null 2>&1; then
        info "Installing/updating dialog with dnf..."
        if [[ "$(id -u)" == "0" ]]; then dnf install -y dialog; else require_cmd sudo; sudo dnf install -y dialog; fi
      elif command -v yum >/dev/null 2>&1; then
        info "Installing/updating dialog with yum..."
        if [[ "$(id -u)" == "0" ]]; then yum install -y dialog; else require_cmd sudo; sudo yum install -y dialog; fi
      elif command -v pacman >/dev/null 2>&1; then
        info "Installing/updating dialog with pacman..."
        if [[ "$(id -u)" == "0" ]]; then pacman -Sy --needed --noconfirm dialog; else require_cmd sudo; sudo pacman -Sy --needed --noconfirm dialog; fi
      elif command -v zypper >/dev/null 2>&1; then
        info "Installing/updating dialog with zypper..."
        if [[ "$(id -u)" == "0" ]]; then zypper --non-interactive install dialog; else require_cmd sudo; sudo zypper --non-interactive install dialog; fi
      elif command -v dialog >/dev/null 2>&1; then
        success "dialog is already installed ($(dialog_version_string))."
        return 0
      else
        die "Could not install dialog automatically: no supported package manager was found."
      fi

      command -v dialog >/dev/null 2>&1 || die "dialog installation finished, but the dialog command is not available."
      success "dialog is ready ($(dialog_version_string))."
      ;;

    *)
      if command -v dialog >/dev/null 2>&1; then
        success "dialog is already installed ($(dialog_version_string))."
      else
        die "Automatic dialog installation currently supports macOS and Linux only."
      fi
      ;;
  esac
}

install_or_update_ollama() {
  require_cmd curl

  local os local_version latest_version installer
  os="$(uname -s 2>/dev/null || true)"
  case "$os" in
    Darwin|Linux) ;;
    *) die "--setup currently supports macOS and Linux only." ;;
  esac

  latest_version="$(latest_github_release_version ollama/ollama || true)"

  if command -v ollama >/dev/null 2>&1; then
    local_version="$(ollama --version 2>/dev/null | extract_version || true)"

    if [[ -n "$latest_version" && "$local_version" == "$latest_version" ]]; then
      success "Ollama is already installed and up to date (v$local_version)."
      start_ollama_if_possible || true
      return 0
    fi

    if [[ -n "$latest_version" ]]; then
      info "Ollama update available: ${local_version:-unknown} -> $latest_version"
    else
      warn "Could not determine the latest Ollama version. Re-running the official installer to check/update it."
    fi
  else
    info "Ollama is not installed. Installing it now..."
  fi

  installer="$(mktemp -t ai-ollama-install.XXXXXX)"
  curl -fsSL https://ollama.com/install.sh -o "$installer"
  sh "$installer"
  rm -f "$installer"

  command -v ollama >/dev/null 2>&1 || \
    die "The Ollama installer finished, but the ollama command is not available in PATH."

  local_version="$(ollama --version 2>/dev/null | extract_version || true)"
  if [[ -n "$latest_version" && -n "$local_version" && "$local_version" != "$latest_version" ]]; then
    warn "Ollama installed, but the detected version is $local_version while latest is $latest_version."
  else
    success "Ollama is installed${local_version:+ (v$local_version)}."
  fi

  if [[ "$os" == "Darwin" ]]; then
    start_ollama_if_possible || warn "Ollama is installed, but the app/API did not start automatically."
  else
    start_ollama_if_possible || warn "Ollama is installed, but the API is not responding yet."
  fi
}

load_nvm() {
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  [[ -s "$NVM_DIR/nvm.sh" ]] || return 1

  # nvm is not written for `set -u`, so disable nounset while sourcing it.
  set +u
  # shellcheck disable=SC1090
  . "$NVM_DIR/nvm.sh"
  set -u
  command -v nvm >/dev/null 2>&1
}

install_nvm_if_needed() {
  require_cmd curl

  if load_nvm; then
    return 0
  fi

  local latest_nvm
  latest_nvm="$(latest_github_release_version nvm-sh/nvm || true)"
  [[ -n "$latest_nvm" ]] || die "Could not determine the latest nvm release."

  info "Installing nvm v$latest_nvm..."
  curl -fsSL "https://raw.githubusercontent.com/nvm-sh/nvm/v${latest_nvm}/install.sh" | bash

  load_nvm || die "nvm was installed, but could not be loaded in the current shell. Open a new terminal and run ai --setup again."
}

install_npm_via_nvm() {
  install_nvm_if_needed

  info "Installing the latest Node.js LTS release with npm..."
  set +u
  nvm install --lts --latest-npm
  nvm alias default 'lts/*' >/dev/null
  nvm use --lts >/dev/null
  set -u

  command -v npm >/dev/null 2>&1 || die "Node.js was installed through nvm, but npm is still unavailable."
  success "npm installed ($(npm --version))."
}

npm_global_prefix_is_writable() {
  local prefix
  prefix="$(npm config get prefix 2>/dev/null || true)"
  [[ -n "$prefix" ]] || return 1

  if [[ "$prefix" == "$HOME" || "$prefix" == "$HOME/"* ]]; then
    return 0
  fi
  [[ -w "$prefix" ]] && return 0
  [[ -w "$(dirname "$prefix")" ]] && return 0
  return 1
}

run_npm_global() {
  local npm_bin
  npm_bin="$(command -v npm)"

  if npm_global_prefix_is_writable; then
    "$npm_bin" "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$npm_bin" "$@"
  else
    "$npm_bin" "$@"
  fi
}

install_or_update_npm() {
  require_cmd curl

  if ! command -v npm >/dev/null 2>&1; then
    info "npm is not installed. Installing Node.js LTS and npm through nvm..."
    install_npm_via_nvm
    return 0
  fi

  local local_version latest_version
  local_version="$(npm --version 2>/dev/null || true)"
  latest_version="$(npm view npm version --silent 2>/dev/null | tail -n 1 || true)"

  if [[ -z "$latest_version" ]]; then
    warn "npm is installed (v${local_version:-unknown}), but the latest registry version could not be checked."
    return 0
  fi

  if [[ "$local_version" == "$latest_version" ]]; then
    success "npm is already installed and up to date (v$local_version)."
    return 0
  fi

  info "npm update available: ${local_version:-unknown} -> $latest_version"
  if run_npm_global install -g npm@latest; then
    local_version="$(npm --version 2>/dev/null || true)"
    if [[ "$local_version" == "$latest_version" ]]; then
      success "npm updated to v$local_version."
    else
      warn "npm update command completed, but detected version is ${local_version:-unknown}; expected $latest_version."
    fi
    return 0
  fi

  warn "Updating npm in the current Node.js installation failed. Falling back to Node.js LTS through nvm."
  install_npm_via_nvm

  # nvm's --latest-npm installs the newest npm supported by the selected LTS.
  success "npm is ready (v$(npm --version))."
}

install_or_update_codex() {
  command -v npm >/dev/null 2>&1 || die "npm is required to install Codex CLI."

  local local_version latest_version
  latest_version="$(npm view @openai/codex version --silent 2>/dev/null | tail -n 1 || true)"
  [[ -n "$latest_version" ]] || die "Could not determine the latest @openai/codex version from npm."

  if command -v codex >/dev/null 2>&1; then
    local_version="$(codex --version 2>/dev/null | extract_version || true)"
    if [[ "$local_version" == "$latest_version" ]]; then
      success "Codex CLI is already installed and up to date (v$local_version)."
      return 0
    fi
    info "Codex CLI update available: ${local_version:-unknown} -> $latest_version"
  else
    info "Codex CLI is not installed. Installing it now..."
  fi

  run_npm_global install -g @openai/codex@latest
  command -v codex >/dev/null 2>&1 || die "Codex installation finished, but the codex command is not available in PATH."

  local_version="$(codex --version 2>/dev/null | extract_version || true)"
  if [[ "$local_version" == "$latest_version" ]]; then
    success "Codex CLI is installed and up to date (v$local_version)."
  else
    warn "Codex installation completed, but detected version is ${local_version:-unknown}; expected $latest_version."
  fi
}

setup_all() {
  require_cmd curl

  printf '%b
' "${BOLD}AI toolchain setup${RESET}"
  printf '
'

  info "[1/4] Checking Ollama..."
  install_or_update_ollama

  printf '
'
  info "[2/4] Checking Node.js + npm..."
  install_or_update_npm

  printf '
'
  info "[3/4] Checking Codex CLI..."
  install_or_update_codex

  printf '
'
  info "[4/4] Checking dialog TUI..."
  install_or_update_dialog

  printf '
'
  success "AI toolchain setup is complete."
}

install_model() {
  local model="$1"
  validate_model_name "$model"
  ensure_ollama_cli
  ensure_ollama_api

  if model_is_installed "$model"; then
    warn "Model $model is already installed. `ollama pull` will check for updates."
  fi

  info "Downloading model: $model"
  ollama pull "$model"
  success "Model installed: $model"
}

source_model_name_from_url() {
  local source="$1" base name
  base="${source%%\?*}"
  base="${base%%\#*}"
  base="${base##*/}"
  base="${base%.gguf}"
  base="${base%.GGUF}"
  name="$(printf '%s' "$base" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9._-]+/-/g; s/^-+//; s/-+$//')"
  [[ -n "$name" ]] || name="imported-model"
  printf '%s\n' "$name"
}

normalize_huggingface_source() {
  local source="$1" ref path
  case "$source" in
    https://huggingface.co/*|http://huggingface.co/*)
      path="${source#*://huggingface.co/}"
      ;;
    https://hf.co/*|http://hf.co/*)
      path="${source#*://hf.co/}"
      ;;
    huggingface.co/*)
      path="${source#huggingface.co/}"
      ;;
    hf.co/*)
      path="${source#hf.co/}"
      ;;
    *) return 1 ;;
  esac

  path="${path%%\?*}"
  path="${path%%\#*}"
  while [[ "$path" == */ ]]; do path="${path%/}"; done

  # Repository pages are directly consumable by Ollama.  Strip common web UI
  # suffixes while preserving an optional Ollama quantization tag.
  case "$path" in
    */tree/*) path="${path%%/tree/*}" ;;
  esac
  [[ "$path" == */blob/* || "$path" == */resolve/* ]] && return 1

  [[ "$path" == */* ]] || return 1
  ref="huggingface.co/$path"
  printf '%s\n' "$ref"
}

install_model_from_source() {
  local source="$1" hf_ref tmpdir url_path gguf modelfile local_name
  [[ -n "$source" ]] || die "--source requires a URL."
  ensure_ollama_cli
  ensure_ollama_api
  require_cmd curl

  if hf_ref="$(normalize_huggingface_source "$source" 2>/dev/null)"; then
    info "Downloading Hugging Face model through Ollama: $hf_ref"
    ollama pull "$hf_ref"
    success "Model installed from source: $hf_ref"
    return 0
  fi

  case "$source" in
    http://*|https://*) ;;
    *) die "Unsupported source: $source. Use an HTTP(S) URL or a Hugging Face repository URL." ;;
  esac

  url_path="${source%%\?*}"
  url_path="${url_path%%\#*}"
  case "$url_path" in
    *huggingface.co/*/blob/*/*.gguf|*huggingface.co/*/blob/*/*.GGUF)
      source="$(printf '%s' "$source" | sed 's#/blob/#/resolve/#')"
      ;;
    *.gguf|*.GGUF) ;;
    *)
      die "Direct URL imports currently support GGUF files. For Hugging Face, pass the repository URL (for example https://huggingface.co/user/model-GGUF)."
      ;;
  esac

  tmpdir="$(mktemp -d -t ai-source-model.XXXXXX)"
  gguf="$tmpdir/model.gguf"
  modelfile="$tmpdir/Modelfile"
  local_name="$(source_model_name_from_url "$source")"

  info "Downloading GGUF source: $source"
  if ! curl -fL --progress-bar "$source" -o "$gguf"; then
    rm -rf "$tmpdir"
    die "Could not download model source: $source"
  fi
  [[ -s "$gguf" ]] || { rm -rf "$tmpdir"; die "Downloaded GGUF file is empty."; }

  printf 'FROM %s\n' "$gguf" > "$modelfile"
  info "Importing GGUF as local model: $local_name"
  if ! ollama create "$local_name" -f "$modelfile"; then
    rm -rf "$tmpdir"
    die "Ollama could not import the downloaded GGUF model."
  fi
  rm -rf "$tmpdir"
  success "Model installed from source as: $local_name"
}

uninstall_model() {
  local model="$1"
  validate_model_name "$model"
  ensure_ollama_cli
  ensure_ollama_api

  model_is_installed "$model" || die "Model is not installed: $model"

  ollama stop "$model" >/dev/null 2>&1 || true

  info "Removing model: $model"
  ollama rm "$model"
  clear_base_if_matches "$model"
  success "Model uninstalled: $model"
}

set_base_model() {
  local model="$1"
  validate_model_name "$model"
  ensure_ollama_cli
  ensure_ollama_api

  model_is_installed "$model" || \
    die "Model $model is not installed. Install it first with: ai --install $model"

  mkdir -p "$CONFIG_DIR"
  printf '%s\n' "$model" > "$BASE_MODEL_FILE"
  success "Base model set to: $model"
}

resolve_model_or_base() {
  local model="${1:-}"

  if [[ -z "$model" ]]; then
    model="$(get_base_model)"
    [[ -n "$model" ]] || \
      die "No model specified and no base model is configured. Run: ai --set-base [MODEL]"
  fi

  validate_model_name "$model"
  printf '%s\n' "$model"
}

validate_exec_mode() {
  local mode="${1:-}"

  case "$mode" in
    ask|auto|no-ask)
      printf '%s\n' "$mode"
      ;;
    *)
      die "Invalid --exec mode: ${mode:-<empty>}. Expected: ask, auto, or no-ask."
      ;;
  esac
}

# Tools managed by ai. Keep this registry dependency-free and compatible with
# macOS Bash 3.2. MCP servers can be layered onto this registry later without
# changing the public --tools/--tool interface.
tool_names() {
  printf '%s\n' 'shell' 'view-image' 'web-search'
}

normalize_tool_name() {
  local raw="${1:-}" lower
  lower="$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]')"
  case "$lower" in
    shell) printf '%s\n' 'shell' ;;
    view-image|view_image|viewimage) printf '%s\n' 'view-image' ;;
    web-search|web_search|websearch) printf '%s\n' 'web-search' ;;
    *) return 1 ;;
  esac
}

tool_default_state() {
  local name="$1"
  case "$name" in
    shell|view-image) printf '%s\n' 'enabled' ;;
    web-search) printf '%s\n' 'disabled' ;;
    *) return 1 ;;
  esac
}

tool_scope() {
  case "$1" in
    shell|view-image) printf '%s\n' 'local' ;;
    web-search) printf '%s\n' 'network' ;;
    *) return 1 ;;
  esac
}

tool_description() {
  case "$1" in
    shell) printf '%s\n' 'Run local shell commands through Codex' ;;
    view-image) printf '%s\n' 'Attach and inspect local images' ;;
    web-search) printf '%s\n' 'Live web search through the configured provider' ;;
    *) return 1 ;;
  esac
}

tool_get_state() {
  local name stored=""
  name="$(normalize_tool_name "$1")" || return 1

  if [[ -f "$TOOLS_CONFIG_FILE" ]]; then
    stored="$(LC_ALL=C awk -F= -v n="$name" '
      $1 == n && ($2 == "enabled" || $2 == "disabled") { value=$2 }
      END { if (value != "") print value }
    ' "$TOOLS_CONFIG_FILE")"
  fi

  if [[ -n "$stored" ]]; then
    printf '%s\n' "$stored"
  else
    tool_default_state "$name"
  fi
}

tool_is_enabled() {
  [[ "$(tool_get_state "$1")" == 'enabled' ]]
}

tool_set_state() {
  local requested="$1" state="$2" name tmp
  name="$(normalize_tool_name "$requested")" || \
    die "Unknown tool: $requested. Run: ai --tools"

  case "$state" in
    enabled|disabled) ;;
    *) die "Internal error: invalid tool state: $state" ;;
  esac

  mkdir -p "$CONFIG_DIR"
  tmp="$(mktemp "${TMPDIR:-/tmp}/ai-tools.XXXXXX")"

  if [[ -f "$TOOLS_CONFIG_FILE" ]]; then
    LC_ALL=C awk -F= -v n="$name" '$1 != n { print }' "$TOOLS_CONFIG_FILE" > "$tmp"
  else
    : > "$tmp"
  fi
  printf '%s=%s\n' "$name" "$state" >> "$tmp"
  mv "$tmp" "$TOOLS_CONFIG_FILE"
}

tools_enabled_summary() {
  local name summary=""
  while IFS= read -r name; do
    [[ -n "$name" ]] || continue
    if tool_is_enabled "$name"; then
      if [[ -n "$summary" ]]; then
        summary="$summary, $name"
      else
        summary="$name"
      fi
    fi
  done <<'AI_TOOL_NAMES'
shell
view-image
web-search
AI_TOOL_NAMES

  if [[ -n "$summary" ]]; then
    printf '%s\n' "$summary"
  else
    printf '%s\n' 'none'
  fi
}

show_tools() {
  local name state scope description state_color
  printf '%s%-14s %-10s %-9s %s%s\n' "$LIST_HEADER" 'Tool' 'State' 'Scope' 'Description' "$RESET"
  printf '%s%-14s %-10s %-9s %s%s\n' "$LIST_SEPARATOR" '--------------' '----------' '---------' '-----------------------------------------------' "$RESET"

  while IFS= read -r name; do
    [[ -n "$name" ]] || continue
    state="$(tool_get_state "$name")"
    scope="$(tool_scope "$name")"
    description="$(tool_description "$name")"
    if [[ "$state" == 'enabled' ]]; then
      state_color="$BRIGHT_GREEN"
    else
      state_color="$DIM"
    fi
    printf '%s%-14s%s %s%-10s%s %-9s %s\n' \
      "$LIST_MODEL" "$name" "$RESET" \
      "$state_color" "$state" "$RESET" \
      "$scope" "$description"
  done <<'AI_TOOL_NAMES'
shell
view-image
web-search
AI_TOOL_NAMES

  printf '\n%sConfig:%s %s\n' "$LIST_LABEL" "$RESET" "$TOOLS_CONFIG_FILE"
}

validate_image_dimension() {
  local label="$1" value="$2" number
  [[ "$value" =~ ^[0-9]+$ ]] || die "$label must be a positive integer."
  number=$((10#$value))
  (( number >= 64 && number <= 8192 )) || die "$label must be between 64 and 8192 pixels."
  printf '%s\n' "$number"
}

image_timestamp_millis() {
  if command -v perl >/dev/null 2>&1; then
    perl -MTime::HiRes=time -MPOSIX=strftime -e '$t=time; $ms=int(($t-int($t))*1000); print strftime("%Y%m%d%H%M%S", localtime($t)), sprintf("%03d",$ms), "\n"'
    return 0
  fi

  local ns
  ns="$(date +%N 2>/dev/null || true)"
  if [[ "$ns" =~ ^[0-9]+$ ]]; then
    printf '%s%s\n' "$(date +%Y%m%d%H%M%S)" "${ns:0:3}"
  else
    printf '%s000\n' "$(date +%Y%m%d%H%M%S)"
  fi
}

default_image_file_name() {
  printf 'image_%s.png\n' "$(image_timestamp_millis)"
}

normalize_image_file_name() {
  local name="$1"
  [[ -n "$name" ]] || name="$(default_image_file_name)"
  case "$name" in
    */*) die "--file-name must be a file name, not a path. Use --output-dir for the directory." ;;
  esac
  case "$name" in
    *.png|*.PNG) ;;
    *) name="${name}.png" ;;
  esac
  printf '%s\n' "$name"
}

json_escape_stdin() {
  LC_ALL=C awk '
    BEGIN { first=1; ORS="" }
    {
      gsub(/\\/, "\\\\")
      gsub(/\"/, "\\\"")
      gsub(/\t/, "\\t")
      gsub(/\r/, "\\r")
      if (!first) printf "\\n"
      printf "%s", $0
      first=0
    }
  '
}

default_image_model() {
  local base name size
  base="$(get_base_model)"
  if [[ -n "$base" ]] && model_is_installed "$base" && model_supports_image_generation "$base"; then
    printf '%s\n' "$base"
    return 0
  fi

  while IFS='|' read -r name size; do
    [[ -n "$name" ]] || continue
    if model_supports_image_generation "$name"; then
      printf '%s\n' "$name"
      return 0
    fi
  done < <(installed_models_data)
  return 1
}

extract_image_base64() {
  local response_file="$1" output_file="$2"
  : > "$output_file"

  if command -v jq >/dev/null 2>&1; then
    jq -r '.image // empty' "$response_file" > "$output_file" 2>/dev/null || true
  elif command -v python3 >/dev/null 2>&1; then
    python3 - "$response_file" > "$output_file" 2>/dev/null <<'PYJSON' || true
import json, sys
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    obj=json.load(f)
print(obj.get('image',''), end='')
PYJSON
  else
    tr -d '\n\r' < "$response_file" \
      | sed -n 's/.*"image"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' > "$output_file"
  fi

  [[ -s "$output_file" ]]
}

base64_decode_to_file() {
  local input="$1" output="$2"
  if base64 --decode < "$input" > "$output" 2>/dev/null; then
    return 0
  fi
  if base64 -D < "$input" > "$output" 2>/dev/null; then
    return 0
  fi
  rm -f "$output"
  return 1
}

generate_image() {
  local model="$1" width="$2" height="$3" output_dir="$4" file_name="$5" prompt="$6"
  local escaped_model escaped_prompt payload response b64 http_code error output_path

  ensure_ollama_cli
  ensure_ollama_api
  require_cmd curl
  require_cmd base64

  [[ "$(uname -s 2>/dev/null || true)" == "Darwin" ]] || \
    warn "Ollama image generation is experimental and may not be available on this operating system."

  [[ -n "$model" ]] || model="$(default_image_model 2>/dev/null || true)"
  [[ -n "$model" ]] || die "No installed image-generation model was found. Install one from Experimental Models first."
  model_is_installed "$model" || die "Image model is not installed: $model"
  model_supports_image_generation "$model" || \
    die "Model $model does not advertise Ollama's image-generation capability."

  width="$(validate_image_dimension width "$width")"
  height="$(validate_image_dimension height "$height")"
  [[ -n "$prompt" ]] || die "--prompt/-p is required and cannot be empty."

  [[ -n "$output_dir" ]] || output_dir="$PWD"
  if [[ "$output_dir" == "~" ]]; then
    output_dir="$HOME"
  elif [[ "$output_dir" == "~/"* ]]; then
    output_dir="$HOME/${output_dir#~/}"
  fi
  mkdir -p "$output_dir" || die "Could not create output directory: $output_dir"
  output_dir="$(cd "$output_dir" && pwd -P)" || die "Could not access output directory: $output_dir"
  file_name="$(normalize_image_file_name "$file_name")"
  output_path="$output_dir/$file_name"

  payload="$(mktemp -t ai-image-payload.XXXXXX)"
  response="$(mktemp -t ai-image-response.XXXXXX)"
  b64="$(mktemp -t ai-image-base64.XXXXXX)"

  escaped_model="$(printf '%s' "$model" | json_escape_stdin)"
  escaped_prompt="$(printf '%s' "$prompt" | json_escape_stdin)"
  printf '{"model":"%s","prompt":"%s","width":%s,"height":%s,"stream":false}\n' \
    "$escaped_model" "$escaped_prompt" "$width" "$height" > "$payload"

  info "Generating image with $model (${width}x${height})..."
  http_code="$(curl -sS -o "$response" -w '%{http_code}' \
    -H 'Content-Type: application/json' --data-binary "@$payload" \
    "$OLLAMA_URL/api/generate" 2>/dev/null || printf '000')"
  [[ "$http_code" =~ ^[0-9][0-9][0-9]$ ]] || http_code="000"

  case "$http_code" in
    2??) ;;
    *)
      error="$(tr '\n\r' '  ' < "$response" | sed -n 's/.*"error"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)"
      rm -f "$payload" "$response" "$b64"
      die "Image generation failed (HTTP $http_code)${error:+: $error}"
      ;;
  esac

  if ! extract_image_base64 "$response" "$b64"; then
    error="$(tr '\n\r' '  ' < "$response" | sed -n 's/.*"error"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)"
    rm -f "$payload" "$response" "$b64"
    die "Ollama did not return an image${error:+: $error}"
  fi

  if ! base64_decode_to_file "$b64" "$output_path"; then
    rm -f "$payload" "$response" "$b64"
    die "Could not decode Ollama's generated image."
  fi

  rm -f "$payload" "$response" "$b64"
  success "Image saved: $output_path"
}

run_model() {
  local model="$1"
  local context_raw="${2:-}"
  local context=""

  ensure_ollama_cli
  ensure_ollama_api
  model_is_installed "$model" || \
    die "Model $model is not installed. Install it first with: ai --install $model"

  if [[ -n "$context_raw" ]]; then
    context="$(parse_context_length "$context_raw")"
  fi

  local payload
  if [[ -n "$context" ]]; then
    payload="{\"model\":\"$model\",\"stream\":false,\"keep_alive\":-1,\"options\":{\"num_ctx\":$context}}"
    info "Loading $model (context: $context tokens)..."
  else
    payload="{\"model\":\"$model\",\"stream\":false,\"keep_alive\":-1}"
    info "Loading $model (Ollama default context)..."
  fi

  curl -fsS \
    -H 'Content-Type: application/json' \
    -d "$payload" \
    "$OLLAMA_URL/api/generate" >/dev/null

  success "Model is running: $model"
  if [[ -n "$context" ]]; then
    printf 'Context: %s tokens\n' "$context"
  fi
  printf 'API: %s\n' "$OLLAMA_URL"
}

chat_model() {
  local model="$1"
  local context_raw="${2:-}"
  local context=""
  local chat_model_name="$model"
  local temp_model=""
  local modelfile=""
  local status=0

  ensure_ollama_cli
  ensure_ollama_api
  model_is_installed "$model" || \
    die "Model $model is not installed. Install it first with: ai --install $model"

  if [[ -n "$context_raw" ]]; then
    context="$(parse_context_length "$context_raw")"
    temp_model="ai-chat-session-$$-${RANDOM}"
    modelfile="$(mktemp -t ai-chat-modelfile.XXXXXX)"

    cat > "$modelfile" <<EOF
FROM $model
PARAMETER num_ctx $context
EOF

    info "Preparing chat with $model (context: $context tokens)..."
    if ! ollama create "$temp_model" -f "$modelfile" >/dev/null; then
      rm -f "$modelfile"
      die "Could not create the temporary chat profile."
    fi
    rm -f "$modelfile"
    modelfile=""
    chat_model_name="$temp_model"
  else
    info "Opening chat with $model (Ollama default context)..."
  fi

  printf '%b\n' "${DIM}Type /bye or press Ctrl+D to exit.${RESET}"

  # Do not let `set -e` skip temporary-profile cleanup when the interactive
  # Ollama process exits with a non-zero status (for example after Ctrl+C).
  set +e
  ollama run "$chat_model_name"
  status=$?
  set -e

  if [[ -n "$temp_model" ]]; then
    info "Removing temporary chat profile..."
    ollama stop "$temp_model" >/dev/null 2>&1 || true
    ollama rm "$temp_model" >/dev/null 2>&1 || \
      warn "Could not remove temporary model profile: $temp_model"
  fi

  return "$status"
}

agent_model() {
  local model="$1"
  local directory="${2:-}"
  local context_raw="${3:-}"
  local exec_mode="${4:-auto}"
  local workspace=""
  local temp_workspace=""
  local sandbox_mode="read-only"
  local started_by_agent=0
  local status=0

  ensure_ollama_cli
  ensure_ollama_api
  ensure_codex_cli
  exec_mode="$(validate_exec_mode "$exec_mode")"

  model_is_installed "$model" || \
    die "Model $model is not installed. Install it first with: ai --install $model"

  if ! model_supports_tools "$model"; then
    die "Model $model does not advertise Ollama's 'tools' capability and cannot be used as a Codex agent. Choose a tool-capable model such as qwen3-coder:30b, qwen3, devstral, qwen2.5-coder, llama3.1, or another model whose 'ollama show' output lists Tools."
  fi

  # Prepare the workspace before loading the model so a bad path cannot leave
  # a model running just because directory setup failed.
  if [[ -n "$directory" ]]; then
    # Expand a literal ~/ prefix as a convenience when the caller quotes it.
    if [[ "$directory" == "~" ]]; then
      directory="$HOME"
    elif [[ "$directory" == "~/"* ]]; then
      directory="$HOME/${directory#~/}"
    fi

    mkdir -p "$directory" || die "Could not create agent directory: $directory"
    workspace="$(cd "$directory" && pwd -P)" || die "Could not access agent directory: $directory"
    sandbox_mode="workspace-write"
    info "Codex workspace: $workspace"
    info "Sandbox: workspace-write"
  else
    temp_workspace="$(mktemp -d -t ai-agent-workspace.XXXXXX)"
    workspace="$temp_workspace"
    sandbox_mode="read-only"
    info "No --directory was provided."
    info "Codex will use an empty temporary read-only workspace: $workspace"
  fi

  if model_is_running "$model"; then
    info "Model is already running: $model"
    if [[ -n "$context_raw" ]]; then
      warn "The model is already running, so --context-length will not reload it or change its current context."
    fi
  else
    run_model "$model" "$context_raw"
    started_by_agent=1
  fi

  info "Starting Codex with local model: $model"
  info "Codex provider: ollama (${OLLAMA_URL%/}/v1)"
  info "Execution approvals: $exec_mode"
  info "Tools: $(tools_enabled_summary)"

  # Keep approval policy separate from the filesystem sandbox. In particular,
  # --exec no-ask never implies danger-full-access.
  local -a codex_exec_args=()
  case "$exec_mode" in
    ask)
      codex_exec_args=(
        --ask-for-approval on-request
        -c 'approvals_reviewer="user"'
      )
      ;;
    auto)
      codex_exec_args=(
        --ask-for-approval on-request
        -c 'approvals_reviewer="auto_review"'
      )
      ;;
    no-ask)
      codex_exec_args=(
        --ask-for-approval never
        -c 'approvals_reviewer="user"'
      )
      ;;
  esac

  # Explicitly project ai's persistent tool state into every Codex session so
  # ~/.codex/config.toml cannot silently re-enable a tool disabled in ai.
  local -a codex_tool_args=()
  if tool_is_enabled 'shell'; then
    codex_tool_args+=( -c 'features.shell_tool=true' )
  else
    codex_tool_args+=( -c 'features.shell_tool=false' )
  fi

  if tool_is_enabled 'view-image'; then
    codex_tool_args+=( -c 'tools.view_image=true' )
  else
    codex_tool_args+=( -c 'tools.view_image=false' )
  fi

  if tool_is_enabled 'web-search'; then
    codex_tool_args+=( -c 'web_search="live"' )
  else
    codex_tool_args+=( -c 'web_search="disabled"' )
  fi

  # Codex's OSS provider uses an OpenAI-compatible /v1 endpoint.
  # Running Codex in a subshell also ensures its process working directory is
  # exactly the selected workspace even if a future Codex version changes -C.
  set +e
  (
    cd "$workspace" || exit 1
    CODEX_OSS_BASE_URL="${OLLAMA_URL%/}/v1" \
      codex --oss --local-provider ollama -m "$model" \
        --sandbox "$sandbox_mode" -C "$workspace" \
        "${codex_tool_args[@]}" \
        "${codex_exec_args[@]}"
  )
  status=$?
  set -e

  if [[ -n "$temp_workspace" ]]; then
    rm -rf "$temp_workspace"
  fi

  if (( started_by_agent == 1 )); then
    info "The model was started by --agent; stopping it now..."
    ollama stop "$model" >/dev/null 2>&1 || \
      warn "Could not stop model after the Codex session: $model"
  fi

  return "$status"
}

stop_model() {
  local model="$1"
  ensure_ollama_cli
  ensure_ollama_api

  info "Stopping model: $model"
  if ollama stop "$model" >/dev/null 2>&1; then
    success "Model stopped: $model"
  else
    warn "Model $model was not running or does not exist."
  fi
}

stop_all_models() {
  ensure_ollama_cli
  ensure_ollama_api

  local models
  models="$(ollama ps 2>/dev/null | awk 'NR > 1 {print $1}' || true)"

  if [[ -z "$models" ]]; then
    success "No running models."
    return 0
  fi

  local model
  while IFS= read -r model; do
    [[ -n "$model" ]] || continue
    info "Stopping: $model"
    ollama stop "$model" >/dev/null 2>&1 || warn "Could not stop: $model"
  done <<< "$models"

  success "All running models stopped."
}

confirm_purge() {
  local description="$1"

  [[ "${AI_PURGE_FORCE:-0}" == "1" ]] && return 0

  [[ -t 0 ]] || \
    die "This purge command requires an interactive terminal. Set AI_PURGE_FORCE=1 to run non-interactively."

  printf '%b
' "${RED}${BOLD}WARNING:${RESET} $description"
  printf 'Type PURGE to continue: '

  local answer
  IFS= read -r answer
  [[ "$answer" == "PURGE" ]] || die "Purge cancelled."
}

remove_all_models_if_possible() {
  command -v ollama >/dev/null 2>&1 || {
    warn "Ollama is not installed; there are no models to remove through the CLI."
    rm -rf "$HOME/.ollama/models"
    rm -f "$BASE_MODEL_FILE"
    return 0
  }

  start_ollama_if_possible || {
    warn "Could not start the Ollama API. Removing the local model store directly."
    rm -rf "$HOME/.ollama/models"
    rm -f "$BASE_MODEL_FILE"
    return 0
  }

  local models
  models="$(ollama list 2>/dev/null | awk 'NR > 1 {print $1}' || true)"

  if [[ -z "$models" ]]; then
    success "No installed models to remove."
    rm -f "$BASE_MODEL_FILE"
    return 0
  fi

  local model
  while IFS= read -r model; do
    [[ -n "$model" ]] || continue
    info "Removing model: $model"
    ollama stop "$model" >/dev/null 2>&1 || true
    ollama rm "$model" >/dev/null 2>&1 || warn "Could not remove model through Ollama: $model"
  done <<< "$models"

  rm -f "$BASE_MODEL_FILE"
  success "All Ollama models were removed."
}

purge_macos() {
  local remove_model_data="${1:-0}"
  info "Stopping Ollama..."
  osascript -e 'tell application "Ollama" to quit' >/dev/null 2>&1 || true
  pkill -x Ollama >/dev/null 2>&1 || true
  pkill -x ollama >/dev/null 2>&1 || true

  if command -v brew >/dev/null 2>&1; then
    if brew list --cask ollama-app >/dev/null 2>&1; then
      info "Removing Homebrew Ollama app..."
      brew uninstall --cask ollama-app || warn "Homebrew could not uninstall ollama-app. Continuing with manual cleanup."
    elif brew list --formula ollama >/dev/null 2>&1; then
      info "Removing Homebrew Ollama formula..."
      brew uninstall ollama || warn "Homebrew could not uninstall ollama. Continuing with manual cleanup."
    fi
  fi

  if [[ -e /Applications/Ollama.app ]]; then
    info "Removing /Applications/Ollama.app..."
    sudo rm -rf /Applications/Ollama.app
  fi

  if [[ -L /usr/local/bin/ollama ]] || [[ -f /usr/local/bin/ollama ]]; then
    info "Removing /usr/local/bin/ollama..."
    sudo rm -f /usr/local/bin/ollama
  fi

  rm -rf \
    "$HOME/Library/Application Support/Ollama" \
    "$HOME/Library/Saved Application State/com.electron.ollama.savedState" \
    "$HOME/Library/Caches/com.electron.ollama" \
    "$HOME/Library/Caches/ollama" \
    "$HOME/Library/WebKit/com.electron.ollama"

  if [[ "$remove_model_data" == "1" ]]; then
    rm -rf "$HOME/.ollama"
  fi
}

purge_linux() {
  local remove_model_data="${1:-0}"
  info "Stopping Ollama service..."
  if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl stop ollama 2>/dev/null || true
    sudo systemctl disable ollama 2>/dev/null || true
    sudo rm -f /etc/systemd/system/ollama.service
    sudo rm -rf /etc/systemd/system/ollama.service.d
    sudo systemctl daemon-reload 2>/dev/null || true
  fi

  pkill -x ollama >/dev/null 2>&1 || true

  local ollama_bin=""
  ollama_bin="$(command -v ollama 2>/dev/null || true)"

  if [[ -n "$ollama_bin" ]]; then
    case "$ollama_bin" in
      /usr/local/bin/ollama|/usr/bin/ollama|/bin/ollama)
        sudo rm -f "$ollama_bin"
        ;;
      *)
        warn "Ollama binary is in a non-standard location and was not deleted automatically: $ollama_bin"
        ;;
    esac
  fi

  sudo rm -rf /usr/local/lib/ollama /usr/lib/ollama /lib/ollama 2>/dev/null || true

  if [[ "$remove_model_data" == "1" ]]; then
    sudo rm -rf /usr/share/ollama 2>/dev/null || true
    rm -rf "$HOME/.ollama"
  fi

  sudo userdel ollama 2>/dev/null || true
  sudo groupdel ollama 2>/dev/null || true
}

purge_ollama_only_impl() {
  local os
  os="$(uname -s 2>/dev/null || true)"
  case "$os" in
    Darwin) purge_macos 0 ;;
    Linux)  purge_linux 0 ;;
    *) die "Ollama purge currently supports macOS and Linux only." ;;
  esac

  success "Ollama was removed. Downloaded model data was preserved."
}

purge_ollama_and_models_impl() {
  remove_all_models_if_possible

  local os
  os="$(uname -s 2>/dev/null || true)"
  case "$os" in
    Darwin) purge_macos 1 ;;
    Linux)  purge_linux 1 ;;
    *) die "Ollama purge currently supports macOS and Linux only." ;;
  esac

  rm -f "$BASE_MODEL_FILE"
  success "Ollama and all downloaded models were purged."
}

purge_models_impl() {
  remove_all_models_if_possible
  success "Model purge complete. Ollama was kept installed."
}

purge_codex_impl() {
  if ! command -v codex >/dev/null 2>&1; then
    success "Codex CLI is not installed."
    return 0
  fi

  local codex_path
  codex_path="$(command -v codex)"

  if command -v npm >/dev/null 2>&1 && npm list -g --depth=0 @openai/codex >/dev/null 2>&1; then
    info "Removing Codex CLI from npm..."
    run_npm_global uninstall -g @openai/codex
    hash -r 2>/dev/null || true
    success "Codex CLI was removed."
    return 0
  fi

  if command -v brew >/dev/null 2>&1; then
    if brew list --cask codex >/dev/null 2>&1; then
      info "Removing Homebrew Codex cask..."
      brew uninstall --cask codex
      success "Codex CLI was removed."
      return 0
    elif brew list --formula codex >/dev/null 2>&1; then
      info "Removing Homebrew Codex formula..."
      brew uninstall codex
      success "Codex CLI was removed."
      return 0
    fi
  fi

  case "$codex_path" in
    "$HOME/.local/bin/codex"|"$HOME/bin/codex")
      info "Removing standalone Codex binary: $codex_path"
      rm -f "$codex_path"
      success "Codex CLI was removed."
      ;;
    /usr/local/bin/codex|/opt/homebrew/bin/codex)
      warn "Codex was not detected as an npm/Homebrew package. Removing only the detected command: $codex_path"
      if [[ -w "$codex_path" || -w "$(dirname "$codex_path")" ]]; then
        rm -f "$codex_path"
      else
        sudo rm -f "$codex_path"
      fi
      success "Codex command was removed."
      ;;
    *)
      die "Codex exists at an unrecognized location and was not removed automatically: $codex_path"
      ;;
  esac
}

purge_npm_impl() {
  if ! command -v npm >/dev/null 2>&1; then
    success "npm is not installed."
    return 0
  fi

  local npm_path
  npm_path="$(command -v npm)"
  info "Removing npm CLI: $npm_path"

  # npm officially supports uninstalling itself globally. This intentionally
  # leaves Node.js and unrelated global packages in place.
  if npm_global_prefix_is_writable; then
    "$npm_path" uninstall npm -g
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$npm_path" uninstall npm -g
  else
    "$npm_path" uninstall npm -g
  fi

  hash -r 2>/dev/null || true
  if command -v npm >/dev/null 2>&1; then
    warn "An npm command is still available at $(command -v npm). There may be another npm installation earlier/later in PATH."
  else
    success "npm CLI was removed. Node.js was left installed."
  fi
}

purge_default() {
  confirm_purge "this will remove Ollama and ALL downloaded Ollama models. npm and Codex will be kept."
  purge_ollama_and_models_impl
}

purge_ollama_only() {
  confirm_purge "this will remove Ollama only. Downloaded model data will be preserved."
  purge_ollama_only_impl
}

purge_models() {
  confirm_purge "this will remove ALL downloaded Ollama models. Ollama itself will be kept."
  purge_models_impl
}

purge_codex() {
  confirm_purge "this will remove Codex CLI only."
  purge_codex_impl
}

purge_npm() {
  confirm_purge "this will remove the npm CLI only. Node.js itself will be kept."
  purge_npm_impl
}

purge_all() {
  confirm_purge "this will remove Ollama, ALL models, Codex CLI, and npm."

  # Codex must be removed before npm because npm may be needed to uninstall
  # @openai/codex cleanly.
  purge_codex_impl
  purge_npm_impl
  purge_ollama_and_models_impl

  rm -rf "$CONFIG_DIR"
  success "Full AI toolchain purge complete."
}

purge_component() {
  if [[ $# -eq 0 ]]; then
    purge_default
    return 0
  fi

  if [[ $# -gt 1 ]]; then
    die "--purge accepts one component only. If you meant all components, the shell probably expanded *. Use: ai --purge '*'"
  fi

  case "$1" in
    '*')
      purge_all
      ;;
    ollama)
      purge_ollama_only
      ;;
    models)
      purge_models
      ;;
    npm)
      purge_npm
      ;;
    codex)
      purge_codex
      ;;
    *)
      die "Unknown purge component: $1. Expected: ollama, models, npm, codex, or '*'."
      ;;
  esac
}

# -----------------------------------------------------------------------------
# Dialog TUI helpers
# -----------------------------------------------------------------------------

tui_require_dialog() {
  load_homebrew_if_present || true
  command -v dialog >/dev/null 2>&1 || \
    die "The dialog TUI is not installed. Run: ai --setup"

  [[ -t 0 && -t 1 ]] || die "The dialog TUI requires an interactive terminal."
}

tui_dialog() {
  dialog --backtitle "AI Model Manager v$SCRIPT_VERSION" --colors --no-collapse "$@"
}

tui_capture_dialog() {
  local output status
  set +e
  output="$(DIALOG_OK=0 DIALOG_CANCEL=1 DIALOG_HELP=2 DIALOG_EXTRA=3 DIALOG_ESC=255 \
    dialog --stdout --backtitle "AI Model Manager v$SCRIPT_VERSION" --colors --no-collapse "$@")"
  status=$?
  set -e

  if (( status == 0 )); then
    printf '%s\n' "$output"
  fi
  return "$status"
}

tui_dialog_capture_status() {
  local output status
  set +e
  output="$(DIALOG_OK=0 DIALOG_CANCEL=1 DIALOG_HELP=2 DIALOG_EXTRA=3 DIALOG_ESC=255 \
    dialog --stdout --backtitle "AI Model Manager v$SCRIPT_VERSION" --colors --no-collapse "$@")"
  status=$?
  set -e
  printf '%s|%s\n' "$status" "$output"
  return 0
}

tui_model_dialog_capture() {
  local rc="$1"
  shift
  local output status

  set +e
  output="$(DIALOG_OK=0 DIALOG_CANCEL=1 DIALOG_HELP=2 DIALOG_EXTRA=3 DIALOG_ESC=255 \
    DIALOGRC="$rc" dialog --stdout --backtitle "AI Model Manager v$SCRIPT_VERSION" \
      --colors --no-collapse "$@")"
  status=$?
  set -e

  printf '%s|%s\n' "$status" "$output"
  return 0
}

tui_clear_terminal() {
  if command -v clear >/dev/null 2>&1; then
    clear
  else
    printf '\033[2J\033[H'
  fi
}

tui_restore_terminal_mode() {
  command -v stty >/dev/null 2>&1 || return 0
  # dialog normally restores the terminal itself, but some dialog/key paths can
  # leave the controlling TTY in cbreak/raw-ish mode (for example -icrnl).
  # A sane line discipline is required before handing the terminal to a shell
  # command or waiting for Enter, otherwise Enter can be echoed as ^M.
  ( stty sane < /dev/tty ) >/dev/null 2>&1 || true
}

tui_pause_terminal() {
  tui_restore_terminal_mode
  printf '\nPress Enter to return to the AI menu...'
  if ( : < /dev/tty ) 2>/dev/null; then
    IFS= read -r _ < /dev/tty || true
  else
    IFS= read -r _ || true
  fi
}

tui_strip_ansi_file() {
  local input="$1" output="$2"
  LC_ALL=C sed $'s/\033\\[[0-9;]*m//g' "$input" > "$output"
}

tui_show_text_file() {
  local title="$1" file="$2"
  tui_dialog --title "$title" --exit-label "Back" --textbox "$file" 0 0 || true
}

tui_show_message() {
  local title="$1" message="$2"
  tui_dialog --title "$title" --msgbox "$message" 0 0 || true
}

tui_confirm() {
  local title="$1" message="$2"
  tui_dialog --title "$title" --yes-label "Continue" --no-label "Cancel" --yesno "$message" 0 0
}

tui_run_captured() {
  local title="$1"
  shift
  local tmp plain status
  tmp="$(mktemp -t ai-tui-output.XXXXXX)"
  plain="$(mktemp -t ai-tui-plain.XXXXXX)"

  set +e
  ( "$@" ) > "$tmp" 2>&1
  status=$?
  set -e

  tui_strip_ansi_file "$tmp" "$plain"
  if [[ ! -s "$plain" ]]; then
    if (( status == 0 )); then
      printf '%s\n' 'Operation completed successfully.' > "$plain"
    else
      printf 'Operation failed with exit code %s.\n' "$status" > "$plain"
    fi
  fi

  tui_show_text_file "$title" "$plain"
  rm -f "$tmp" "$plain"
  return 0
}

tui_run_terminal() {
  local title="$1"
  shift
  local status

  # Restore canonical input before leaving dialog and handing the TTY to the
  # command. Restore it once more afterwards in case the child changed it.
  tui_restore_terminal_mode
  tui_clear_terminal
  printf '%b\n\n' "${BOLD}${BRIGHT_CYAN}$title${RESET}"

  set +e
  ( "$@" )
  status=$?
  set -e

  tui_restore_terminal_mode
  if (( status != 0 )); then
    printf '\n%b\n' "${RED}Command exited with status $status.${RESET}"
  fi

  tui_pause_terminal
  return 0
}

tui_show_help() {
  local tmp plain
  tmp="$(mktemp -t ai-tui-help.XXXXXX)"
  plain="$(mktemp -t ai-tui-help-plain.XXXXXX)"
  usage > "$tmp" 2>&1
  tui_strip_ansi_file "$tmp" "$plain"
  tui_show_text_file "Help" "$plain"
  rm -f "$tmp" "$plain"
}

tui_show_versions() {
  local tmp
  tmp="$(mktemp -t ai-tui-version.XXXXXX)"
  show_versions > "$tmp" 2>&1
  tui_show_text_file "Version" "$tmp"
  rm -f "$tmp"
}

tui_model_dialog_rc() {
  local rc
  rc="$(mktemp -t ai-tui-dialogrc.XXXXXX)"

  # Preserve the user's dialog theme/settings when possible, then add the
  # model-browser shortcuts.  Each browser chooses its own button labels;
  # F1 always maps to Details, F2 to Sort, and Esc remains Back.
  if [[ -n "${DIALOGRC:-}" ]] && [[ -r "$DIALOGRC" ]]; then
    cp "$DIALOGRC" "$rc"
  elif [[ -r "$HOME/.dialogrc" ]]; then
    cp "$HOME/.dialogrc" "$rc"
  else
    rm -f "$rc"
    dialog --create-rc "$rc" >/dev/null 2>&1 || : > "$rc"
  fi

  cat >> "$rc" <<'DIALOG_KEYS'

# ai model-browser shortcuts
bindkey menubox F1 EXTRA
bindkey menu F1 EXTRA
bindkey menubox F2 CANCEL
bindkey menu F2 CANCEL
DIALOG_KEYS

  printf '%s\n' "$rc"
}


tui_local_model_dialog_rc() {
  local rc
  rc="$(mktemp -t ai-tui-local-dialogrc.XXXXXX)"

  if [[ -n "${DIALOGRC:-}" ]] && [[ -r "$DIALOGRC" ]]; then
    cp "$DIALOGRC" "$rc"
  elif [[ -r "$HOME/.dialogrc" ]]; then
    cp "$HOME/.dialogrc" "$rc"
  else
    rm -f "$rc"
    dialog --create-rc "$rc" >/dev/null 2>&1 || : > "$rc"
  fi

  cat >> "$rc" <<'DIALOG_KEYS'

# ai local-model browser shortcuts
bindkey menubox F1 EXTRA
bindkey menu F1 EXTRA
bindkey menubox F2 CANCEL
bindkey menu F2 CANCEL
DIALOG_KEYS

  printf '%s\n' "$rc"
}

terminal_lines() {
  local lines=""

  if [[ -r /dev/tty ]]; then
    lines="$(stty size < /dev/tty 2>/dev/null | awk '{print $1}' || true)"
  fi
  if [[ ! "$lines" =~ ^[0-9]+$ ]] || (( lines < 10 )); then
    lines="$(tput lines 2>/dev/null || true)"
  fi
  if [[ ! "$lines" =~ ^[0-9]+$ ]] || (( lines < 10 )); then
    lines="${LINES:-}"
  fi
  if [[ ! "$lines" =~ ^[0-9]+$ ]] || (( lines < 10 )); then
    lines=24
  fi

  printf '%s\n' "$lines"
}

tui_prepare_model_menu_data() {
  local input="$1" output="$2" header_file="$3" content_width="$4" base_model="${5:-}"

  (( content_width >= 58 )) || content_width=58

  LC_ALL=C awk -F '\t' -v OFS='\t' -v maxwidth="$content_width" -v header_file="$header_file" -v output="$output" -v base_model="$base_model" '
    function clipped(s,w) {
      if (length(s) <= w) return s
      if (w <= 3) return substr(s,1,w)
      return substr(s,1,w-3) "..."
    }
    function spaces(n,   s,i) {
      s=""
      for (i=0;i<n;i++) s=s " "
      return s
    }
    function normalized(s) {
      if (s == "") return ""
      if (s ~ /:/) return s
      return s ":latest"
    }
    BEGIN {
      h[1]="Model"; h[2]="Status"; h[3]="Size"; h[4]="Rating"; h[5]="Codex"; h[6]="Category"
      for (i=1;i<=6;i++) w[i]=length(h[i])
    }
    NF >= 7 {
      rows[++n]=$0
      model_width=length($1)
      if (base_model != "" && normalized($1) == normalized(base_model)) model_width+=2
      if (model_width>w[1]) w[1]=model_width
      for (i=2;i<=6;i++) if (length($i)>w[i]) w[i]=length($i)
    }
    END {
      separators=10
      fixed=w[2]+w[3]+w[4]+w[5]+w[6]+separators
      model_space=maxwidth-fixed
      if (model_space < 14) model_space=14
      if (w[1] > model_space) w[1]=model_space

      header_core=sprintf("%-*s  %-*s  %*s  %*s  %-*s  %-*s", \
        w[1],h[1],w[2],h[2],w[3],h[3],w[4],h[4],w[5],h[5],w[6],h[6])
      pad=int((maxwidth-length(header_core))/2)
      if (pad < 0) pad=0
      print spaces(pad) header_core > header_file

      for (r=1;r<=n;r++) {
        split(rows[r],a,"\\t")
        model_text=a[1]
        if (base_model != "" && normalized(a[1]) == normalized(base_model)) model_text=model_text " *"
        display=sprintf("%-*s  %-*s  %*s  %*s  %-*s  %-*s", \
          w[1],clipped(model_text,w[1]),w[2],a[2],w[3],a[3],w[4],a[4],w[5],a[5],w[6],a[6])
        printf "%06d\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n", \
          r,a[1],a[2],a[3],a[4],a[5],a[6],a[7],display > output
      }
    }
  ' "$input"
}

tui_model_row_by_id() {
  local data_file="$1" id="$2"
  LC_ALL=C awk -F '\t' -v id="$id" 'BEGIN{OFS="\t"} $1==id {print $2,$3,$4,$5,$6,$7,$8; exit}' "$data_file"
}

tui_show_model_details() {
  local row="$1"
  local model status size fit code category description tmp base base_note=""
  IFS=$'\t' read -r model status size fit code category description <<< "$row"

  base="$(get_base_model)"
  if [[ -n "$base" ]] && [[ "$(normalize_model_name "$model")" == "$(normalize_model_name "$base")" ]]; then
    base_note=" * (default)"
  fi

  tmp="$(mktemp -t ai-tui-model-details.XXXXXX)"
  cat > "$tmp" <<EOF
Model:       $model$base_note
Status:      $status
Size:        $size
Rating:      $fit
Codex:       $code
Category:    $category

Description:
$description
EOF
  tui_show_text_file "Model Details" "$tmp"
  rm -f "$tmp"
}

tui_sort_dialog_rc() {
  local rc
  rc="$(mktemp -t ai-tui-sort-dialogrc.XXXXXX)"

  if [[ -n "${DIALOGRC:-}" ]] && [[ -r "$DIALOGRC" ]]; then
    cp "$DIALOGRC" "$rc"
  elif [[ -r "$HOME/.dialogrc" ]]; then
    cp "$HOME/.dialogrc" "$rc"
  else
    rm -f "$rc"
    dialog --create-rc "$rc" >/dev/null 2>&1 || : > "$rc"
  fi

  cat >> "$rc" <<'DIALOG_KEYS'

# ai sorting shortcuts
bindkey menubox F2 EXTRA
bindkey menu F2 EXTRA
bindkey menubox \? EXTRA
bindkey menu \? EXTRA
DIALOG_KEYS

  printf '%s\n' "$rc"
}

tui_sort_field_description() {
  case "$1" in
    model)    printf '%s\n' "Model name" ;;
    status)   printf '%s\n' "Lifecycle state" ;;
    size)     printf '%s\n' "Model size" ;;
    rating)   printf '%s\n' "Hardware Rating percentage" ;;
    codex)    printf '%s\n' "Codex compatibility, then coding quality" ;;
    category) printf '%s\n' "Model category" ;;
    *)        printf '%s\n' "" ;;
  esac
}

tui_sort_spec_label() {
  local spec="$1" token key direction label=""
  local -a tokens

  IFS='|' read -r -a tokens <<< "$spec"
  for token in "${tokens[@]}"; do
    key="${token%%:*}"
    direction="${token#*:}"
    direction="$(printf '%s' "$direction" | tr '[:lower:]' '[:upper:]')"
    if [[ -n "$label" ]]; then
      label="${label} > "
    fi
    label="${label}${key} ${direction}"
  done
  printf '%s\n' "$label"
}

tui_sort_spec_toggle_direction() {
  local spec="$1" selected="$2" token key direction result=""
  local -a tokens

  IFS='|' read -r -a tokens <<< "$spec"
  for token in "${tokens[@]}"; do
    key="${token%%:*}"
    direction="${token#*:}"
    if [[ "$key" == "$selected" ]]; then
      if [[ "$direction" == "asc" ]]; then direction="desc"; else direction="asc"; fi
    fi
    if [[ -n "$result" ]]; then
      result="${result}|${key}:${direction}"
    else
      result="${key}:${direction}"
    fi
  done
  printf '%s\n' "$result"
}

tui_sort_spec_position() {
  local spec="$1" selected="$2" token key index=0
  local -a tokens
  IFS='|' read -r -a tokens <<< "$spec"
  for token in "${tokens[@]}"; do
    index=$((index + 1))
    key="${token%%:*}"
    if [[ "$key" == "$selected" ]]; then
      printf '%s\n' "$index"
      return 0
    fi
  done
  printf '%s\n' "1"
}

tui_sort_spec_move() {
  local spec="$1" selected="$2" target="$3"
  local token key selected_token="" result=""
  local index=0 inserted=0 count=0
  local -a tokens remaining

  IFS='|' read -r -a tokens <<< "$spec"
  for token in "${tokens[@]}"; do
    key="${token%%:*}"
    if [[ "$key" == "$selected" ]]; then
      selected_token="$token"
    else
      remaining+=( "$token" )
    fi
  done

  [[ -n "$selected_token" ]] || { printf '%s\n' "$spec"; return 0; }

  count=$(( ${#remaining[@]} + 1 ))
  [[ "$target" =~ ^[0-9]+$ ]] || target=1
  (( target < 1 )) && target=1
  (( target > count )) && target="$count"

  for token in "${remaining[@]}"; do
    index=$((index + 1))
    if (( inserted == 0 && index == target )); then
      if [[ -n "$result" ]]; then result="${result}|${selected_token}"; else result="$selected_token"; fi
      inserted=1
    fi
    if [[ -n "$result" ]]; then result="${result}|${token}"; else result="$token"; fi
  done

  if (( inserted == 0 )); then
    if [[ -n "$result" ]]; then result="${result}|${selected_token}"; else result="$selected_token"; fi
  fi

  printf '%s\n' "$result"
}

tui_model_sort_menu() {
  local spec="$1" selected="status" moving_field=""
  local rc result status output token key direction description display header target_position
  local prompt moved_field
  local -a tokens items

  spec="$(normalize_tui_sort_spec "$spec")"
  rc="$(tui_sort_dialog_rc)"

  while true; do
    items=()
    IFS='|' read -r -a tokens <<< "$spec"

    for token in "${tokens[@]}"; do
      key="${token%%:*}"
      direction="${token#*:}"
      description="$(tui_sort_field_description "$key")"
      if [[ -n "$moving_field" && "$key" == "$moving_field" ]]; then
        display="$(printf '> %-9s  %-30s  [%s]' "$key" "$description" "$direction")"
      else
        display="$(printf '  %-9s  %-30s  [%s]' "$key" "$description" "$direction")"
      fi
      items+=( "$key" "$display" )
    done

    header="$(printf '  %-9s  %-30s  %s' "Column" "Description" "Direction")"

    if [[ -n "$moving_field" ]]; then
      prompt="Moving: $moving_field\nUse Up/Down to choose its new position, then press Enter to place it.\nPress Esc to cancel moving.\n\n$header"
    else
      prompt="Top row has the highest sorting priority.\nPress Enter to select a column to move.\n\n$header"
    fi

    result="$(tui_model_dialog_capture "$rc" \
      --title "Sorting" \
      --default-item "$selected" \
      --no-tags --no-hot-list \
      --ok-label "Select" --cancel-label "Back" \
      --extra-button --extra-label "Direction" \
      --hline "Up/Down Navigate   Enter Select/Place   ?/F2 Direction   Esc Back/Cancel" \
      --menu "$prompt" 0 0 10 \
      "${items[@]}")"

    status="${result%%|*}"
    output="${result#*|}"
    [[ -n "$output" ]] && selected="$output"

    case "$status" in
      0)
        if [[ -z "$moving_field" ]]; then
          moving_field="$selected"
        else
          target_position="$(tui_sort_spec_position "$spec" "$selected")"
          moved_field="$moving_field"
          spec="$(tui_sort_spec_move "$spec" "$moving_field" "$target_position")"
          moving_field=""
          selected="$moved_field"
        fi
        ;;
      3)
        spec="$(tui_sort_spec_toggle_direction "$spec" "$selected")"
        ;;
      1|255|-1)
        if [[ -n "$moving_field" ]]; then
          moving_field=""
          continue
        fi
        rm -f "$rc"
        printf '%s\n' "$spec"
        return 0
        ;;
      *)
        ;;
    esac
  done
}

tui_execute_purge_selection() {
  local selection="$1" item
  local want_ollama=0 want_models=0 want_npm=0 want_codex=0

  while IFS= read -r item; do
    case "$item" in
      ollama) want_ollama=1 ;;
      models) want_models=1 ;;
      npm)    want_npm=1 ;;
      codex)  want_codex=1 ;;
    esac
  done <<< "$selection"

  export AI_PURGE_FORCE=1

  # Codex must be removed before npm because npm may be required to uninstall it.
  if (( want_codex == 1 )); then
    purge_codex_impl
  fi
  if (( want_npm == 1 )); then
    purge_npm_impl
  fi

  if (( want_ollama == 1 && want_models == 1 )); then
    purge_ollama_and_models_impl
  elif (( want_models == 1 )); then
    purge_models_impl
  elif (( want_ollama == 1 )); then
    purge_ollama_only_impl
  fi
}

# -----------------------------------------------------------------------------
# TUI v2 - view-oriented interface
# -----------------------------------------------------------------------------

tui_default_installed_model() {
  local base name size first=""
  base="$(get_base_model)"

  while IFS='|' read -r name size; do
    [[ -n "$name" ]] || continue
    [[ -n "$first" ]] || first="$name"
    if [[ -n "$base" ]] && [[ "$(normalize_model_name "$name")" == "$(normalize_model_name "$base")" ]]; then
      printf '%s\n' "$name"
      return 0
    fi
  done < <(installed_models_data)

  printf '%s\n' "$first"
}

tui_select_installed_model() {
  local title="${1:-Select model}"
  local default_model="${2:-}"
  local base name size description choice
  local -a items args

  if ! command -v ollama >/dev/null 2>&1; then
    tui_show_message "$title" "Ollama is not installed. Run Setup first."
    return 1
  fi

  start_ollama_if_possible >/dev/null 2>&1 || true
  base="$(get_base_model)"
  items=()

  while IFS='|' read -r name size; do
    [[ -n "$name" ]] || continue
    description="$size"
    if [[ -n "$base" ]] && [[ "$(normalize_model_name "$name")" == "$(normalize_model_name "$base")" ]]; then
      description="$description  [base]"
    fi
    items+=( "$name" "$description" )
  done < <(installed_models_data)

  if (( ${#items[@]} == 0 )); then
    tui_show_message "$title" "No local models are installed."
    return 1
  fi

  if [[ -z "$default_model" ]]; then
    default_model="$(tui_default_installed_model)"
  fi

  args=( --title "$title" --cancel-label "Back" --menu "Select an installed model:" 0 0 14 )
  if [[ -n "$default_model" ]]; then
    args=( --default-item "$default_model" "${args[@]}" )
  fi

  if choice="$(tui_capture_dialog "${args[@]}" "${items[@]}")"; then
    printf '%s\n' "$choice"
    return 0
  fi
  return 1
}

tui_context_length_prompt() {
  local current="${1:-16K}" value

  while true; do
    if ! value="$(tui_capture_dialog --title "Context Length" --cancel-label "Back" --inputbox \
        "Set the context length.\n\nExamples: 16384, 16K, 1M" 10 64 "$current")"; then
      return 1
    fi

    [[ -n "$value" ]] || value="16K"
    if [[ "$value" =~ ^[0-9]+$ || "$value" =~ ^[0-9]+[KkMm]$ ]]; then
      if [[ "$value" =~ [1-9] ]]; then
        printf '%s\n' "$value"
        return 0
      fi
    fi

    tui_show_message "Context Length" "Invalid context length: $value\n\nUse a positive number such as 16384, 16K, or 1M."
  done
}

# Preserve the old helper name for any backend/UI path that still calls it.
tui_context_prompt() {
  tui_context_length_prompt "${1:-16K}"
}

TUI_AGENT_WORKSPACE=""

tui_agent_workspace_prompt() {
  local current="${1:-$PWD}" result status selection target entry name
  local -a items

  TUI_AGENT_WORKSPACE=""

  if ! current="$(cd "$current" 2>/dev/null && pwd -P)"; then
    current="$(cd "$HOME" 2>/dev/null && pwd -P)"
  fi

  while true; do
    items=(
      "."  "This"
      ".." "Back"
    )

    # macOS ships Bash 3.2.  Avoid nullglob + an empty intermediate array under
    # `set -u`; unmatched globs simply fail the -d test below.
    for entry in "$current"/* "$current"/.[!.]* "$current"/..?*; do
      [[ -d "$entry" ]] || continue
      name="${entry##*/}"
      [[ "$name" != "." && "$name" != ".." ]] || continue
      items+=( "$name" "Directory" )
    done

    result="$(tui_dialog_capture_status \
      --title "Workspace" \
      --default-item "." \
      --ok-label "Select" --cancel-label "Back" \
      --extra-button --extra-label "No catalog" \
      --scrollbar \
      --menu "Location:\n$current\n\nSelect a directory to enter it. Select . (This) to use the current location." \
      0 0 16 "${items[@]}")"

    status="${result%%|*}"
    selection="${result#*|}"

    case "$status" in
      0)
        case "$selection" in
          ".")
            TUI_AGENT_WORKSPACE="$current"
            return 0
            ;;
          "..")
            current="$(cd "$current/.." 2>/dev/null && pwd -P)" || current="/"
            ;;
          "")
            ;;
          *)
            target="$current/$selection"
            if [[ -d "$target" ]] && target="$(cd "$target" 2>/dev/null && pwd -P)"; then
              current="$target"
            else
              tui_show_message "Workspace" "Could not open directory:\n$target"
            fi
            ;;
        esac
        ;;
      3)
        TUI_AGENT_WORKSPACE=""
        return 0
        ;;
      1|255|-1)
        return 1
        ;;
      *)
        tui_show_message "Workspace" "Unexpected dialog status: $status"
        ;;
    esac
  done
}

tui_exec_mode_prompt() {
  local current="${1:-ask}" value
  local ask_state="off" auto_state="off" noask_state="off"

  case "$current" in
    ask) ask_state="on" ;;
    auto) auto_state="on" ;;
    no-ask) noask_state="on" ;;
    *) ask_state="on" ;;
  esac

  if value="$(tui_capture_dialog --title "Execution Approvals" --cancel-label "Back" --radiolist \
      "Choose how Codex handles execution approval requests:" 13 72 3 \
      "ask"    "Ask when approval is required" "$ask_state" \
      "auto"   "Use Codex automatic review" "$auto_state" \
      "no-ask" "Never ask; sandbox escalation fails" "$noask_state")"; then
    value="$(validate_exec_mode "$value")"
    printf '%s\n' "$value"
    return 0
  fi
  return 1
}

tui_tools_checklist() {
  local selection name state description
  local -a items
  items=()

  while IFS= read -r name; do
    [[ -n "$name" ]] || continue
    if tool_is_enabled "$name"; then state='on'; else state='off'; fi
    description="$(tool_description "$name") [$(tool_scope "$name")]"
    items+=( "$name" "$description" "$state" )
  done <<'AI_TOOL_NAMES'
shell
view-image
web-search
AI_TOOL_NAMES

  if selection="$(tui_capture_dialog \
      --title "Agent Tools" \
      --ok-label "Save" --cancel-label "Back" \
      --separate-output \
      --checklist "Enable the tools available to Codex. web-search uses the network." \
      0 0 10 "${items[@]}")"; then
    while IFS= read -r name; do
      [[ -n "$name" ]] || continue
      if printf '%s\n' "$selection" | grep -Fqx -- "$name"; then
        tool_set_state "$name" 'enabled'
      else
        tool_set_state "$name" 'disabled'
      fi
    done <<'AI_TOOL_NAMES'
shell
view-image
web-search
AI_TOOL_NAMES
    return 0
  fi
  return 1
}

tui_display_workspace() {
  local path="$1"
  if [[ -z "$path" ]]; then
    printf '%s\n' "No catalog"
  elif [[ "$path" == "$HOME" ]]; then
    printf '%s\n' "~"
  elif [[ "$path" == "$HOME/"* ]]; then
    printf '~/%s\n' "${path#$HOME/}"
  else
    printf '%s\n' "$path"
  fi
}

tui_select_image_model() {
  local title="${1:-Image Model}" default_model="${2:-}" name size choice count=0
  local -a items args

  if ! command -v ollama >/dev/null 2>&1; then
    tui_show_message "$title" "Ollama is not installed."
    return 1
  fi
  start_ollama_if_possible >/dev/null 2>&1 || true
  items=()

  while IFS='|' read -r name size; do
    [[ -n "$name" ]] || continue
    if model_supports_image_generation "$name"; then
      items+=( "$name" "$size" )
      count=$((count + 1))
    fi
  done < <(installed_models_data)

  if (( count == 0 )); then
    tui_show_message "$title" "No installed image-generation models were found.\n\nInstall one from Models > Experimental Models."
    return 1
  fi

  args=( --title "$title" --cancel-label "Back" --menu "Select an installed image-generation model:" 0 0 12 )
  if [[ -n "$default_model" ]]; then
    args=( --default-item "$default_model" "${args[@]}" )
  fi
  if choice="$(tui_capture_dialog "${args[@]}" "${items[@]}")"; then
    printf '%s\n' "$choice"
    return 0
  fi
  return 1
}

tui_image_dimension_prompt() {
  local label="$1" current="$2" value
  while true; do
    if ! value="$(tui_capture_dialog --title "$label" --cancel-label "Back" --inputbox \
        "Set $label in pixels (64-8192)." 9 52 "$current")"; then
      return 1
    fi
    if [[ "$value" =~ ^[0-9]+$ ]]; then
      local number
      number=$((10#$value))
      if (( number >= 64 && number <= 8192 )); then
        printf '%s\n' "$number"
        return 0
      fi
    fi
    tui_show_message "$label" "Enter an integer between 64 and 8192."
  done
}

TUI_SELECTED_DIRECTORY=""

tui_directory_prompt() {
  local current="${1:-$PWD}" title="${2:-Select Directory}" result status selection target entry name
  local -a items
  TUI_SELECTED_DIRECTORY=""

  if ! current="$(cd "$current" 2>/dev/null && pwd -P)"; then
    current="$(cd "$HOME" 2>/dev/null && pwd -P)"
  fi

  while true; do
    items=( "." "Use this directory" ".." "Back" )
    for entry in "$current"/* "$current"/.[!.]* "$current"/..?*; do
      [[ -d "$entry" ]] || continue
      name="${entry##*/}"
      [[ "$name" != "." && "$name" != ".." ]] || continue
      items+=( "$name" "Directory" )
    done

    result="$(tui_dialog_capture_status \
      --title "$title" --default-item "." \
      --ok-label "Select" --cancel-label "Back" --scrollbar \
      --menu "Location:\n$current\n\nSelect a directory to enter it. Select . to use the current location." \
      0 0 16 "${items[@]}")"
    status="${result%%|*}"; selection="${result#*|}"
    case "$status" in
      0)
        case "$selection" in
          ".") TUI_SELECTED_DIRECTORY="$current"; return 0 ;;
          "..") current="$(cd "$current/.." 2>/dev/null && pwd -P)" || current="/" ;;
          "") ;;
          *)
            target="$current/$selection"
            if [[ -d "$target" ]] && target="$(cd "$target" 2>/dev/null && pwd -P)"; then
              current="$target"
            else
              tui_show_message "$title" "Could not open directory:\n$target"
            fi
            ;;
        esac
        ;;
      1|255|-1) return 1 ;;
    esac
  done
}

tui_image_prompt() {
  local tmp output
  tmp="$(mktemp -t ai-image-prompt.XXXXXX)"
  : > "$tmp"
  if output="$(tui_capture_dialog --title "Image Prompt" --cancel-label "Back" --ok-label "Generate" \
      --editbox "$tmp" 20 86)"; then
    rm -f "$tmp"
    [[ -n "$output" ]] || return 1
    printf '%s\n' "$output"
    return 0
  fi
  rm -f "$tmp"
  return 1
}

tui_image_view() {
  local model="${1:-}" width="800" height="600" target_dir="$PWD" file_name prompt
  local result status field value display_model display_dir
  local -a items

  if [[ -z "$model" ]]; then
    model="$(default_image_model 2>/dev/null || true)"
  fi
  file_name="$(default_image_file_name)"

  while true; do
    display_model="${model:-Not selected}"
    display_dir="$(tui_display_workspace "$target_dir")"
    items=(
      "model"   "$(printf '%-22s [%s]' "Model" "$display_model")"
      "width"   "$(printf '%-22s [%s]' "Width" "$width")"
      "height"  "$(printf '%-22s [%s]' "Height" "$height")"
      "dir"     "$(printf '%-22s [%s]' "Target Directory" "$display_dir")"
      "file"    "$(printf '%-22s [%s]' "File Name" "$file_name")"
    )

    result="$(tui_dialog_capture_status \
      --title "Image Generation" --no-tags --no-hot-list \
      --ok-label "Edit" --cancel-label "Back" \
      --extra-button --extra-label "Run" \
      --hline "Up/Down Navigate   Enter Edit   Run Prompt/Generate   Esc Back" \
      --menu "" 16 92 7 "${items[@]}")"
    status="${result%%|*}"; field="${result#*|}"

    case "$status" in
      0)
        case "$field" in
          model) if value="$(tui_select_image_model "Image Model" "$model")"; then model="$value"; fi ;;
          width) if value="$(tui_image_dimension_prompt "Width" "$width")"; then width="$value"; fi ;;
          height) if value="$(tui_image_dimension_prompt "Height" "$height")"; then height="$value"; fi ;;
          dir)
            if tui_directory_prompt "$target_dir" "Target Directory"; then target_dir="$TUI_SELECTED_DIRECTORY"; fi
            ;;
          file)
            if value="$(tui_capture_dialog --title "File Name" --cancel-label "Back" --inputbox \
                "PNG file name. .png is added automatically when omitted." 9 68 "$file_name")"; then
              [[ -n "$value" ]] && file_name="$value"
            fi
            ;;
        esac
        ;;
      3)
        if [[ -z "$model" ]]; then
          tui_show_message "Image Generation" "Select or install an image-generation model first."
          continue
        fi
        if prompt="$(tui_image_prompt)"; then
          tui_run_terminal "Image Generation: $model" generate_image "$model" "$width" "$height" "$target_dir" "$file_name" "$prompt"
          file_name="$(default_image_file_name)"
        fi
        ;;
      1|255|-1) return 0 ;;
    esac
  done
}

tui_agent_view() {
  local model="${1:-}" context="${2:-16K}" workspace="${3:-}" approval="${4:-ask}"
  local result status field value display_model display_workspace display_tools
  local workspace_start="$PWD"
  local -a items

  if [[ -z "$model" ]]; then
    model="$(tui_default_installed_model)"
  fi
  [[ -n "$context" ]] || context="16K"
  [[ -n "$approval" ]] || approval="ask"

  while true; do
    display_model="${model:-Not selected}"
    display_workspace="$(tui_display_workspace "$workspace")"
    display_tools="$(tools_enabled_summary)"

    items=(
      "model"     "$(printf '%-22s [%s]' "Model" "$display_model")"
      "context"   "$(printf '%-22s [%s]' "Context Length" "$context")"
      "workspace" "$(printf '%-22s [%s]' "Workspace" "$display_workspace")"
      "approval"  "$(printf '%-22s [%s]' "Execution Approvals" "$approval")"
      "tools"     "$(printf '%-22s [%s]' "Tools" "$display_tools")"
    )

    result="$(tui_dialog_capture_status \
      --title "Codex Options" \
      --no-tags --no-hot-list \
      --ok-label "Edit" --cancel-label "Back" \
      --extra-button --extra-label "Run" \
      --hline "Up/Down Navigate   Enter Edit   Run Start Codex   Esc Back" \
      --menu "" 16 84 7 "${items[@]}")"

    status="${result%%|*}"
    field="${result#*|}"

    case "$status" in
      0)
        case "$field" in
          model)
            if value="$(tui_select_installed_model "Agent Model" "$model")"; then
              model="$value"
            fi
            ;;
          context)
            if value="$(tui_context_length_prompt "$context")"; then
              context="$value"
            fi
            ;;
          workspace)
            if [[ -n "$workspace" ]]; then workspace_start="$workspace"; else workspace_start="$PWD"; fi
            if tui_agent_workspace_prompt "$workspace_start"; then
              workspace="$TUI_AGENT_WORKSPACE"
            fi
            ;;
          approval)
            if value="$(tui_exec_mode_prompt "$approval")"; then
              approval="$value"
            fi
            ;;
          tools)
            tui_tools_checklist || true
            ;;
        esac
        ;;
      3)
        if [[ -z "$model" ]]; then
          tui_show_message "Codex Options" "Select an installed model before running Codex."
          continue
        fi
        tui_run_terminal "Codex agent: $model" agent_model "$model" "$workspace" "$context" "$approval"
        ;;
      1|255|-1)
        return 0
        ;;
    esac
  done
}

# Compatibility name used by older local-model action code.  The new UI calls
# tui_agent_view directly.
tui_agent_flow() {
  tui_agent_view "$1"
}

tui_chat_view() {
  local model="${1:-}" context="${2:-16K}"
  local result status field value display_model
  local -a items

  if [[ -z "$model" ]]; then
    model="$(tui_default_installed_model)"
  fi
  [[ -n "$context" ]] || context="16K"

  while true; do
    display_model="${model:-Not selected}"
    items=(
      "model"   "$(printf '%-22s [%s]' "Model" "$display_model")"
      "context" "$(printf '%-22s [%s]' "Context Length" "$context")"
    )

    result="$(tui_dialog_capture_status \
      --title "Chat Options" \
      --no-tags --no-hot-list \
      --ok-label "Edit" --cancel-label "Back" \
      --extra-button --extra-label "Run" \
      --hline "Up/Down Navigate   Enter Edit   Run Start Chat   Esc Back" \
      --menu "" 12 78 4 "${items[@]}")"

    status="${result%%|*}"
    field="${result#*|}"

    case "$status" in
      0)
        case "$field" in
          model)
            if value="$(tui_select_installed_model "Chat Model" "$model")"; then
              model="$value"
            fi
            ;;
          context)
            if value="$(tui_context_length_prompt "$context")"; then
              context="$value"
            fi
            ;;
        esac
        ;;
      3)
        if [[ -z "$model" ]]; then
          tui_show_message "Chat Options" "Select an installed model before starting Chat."
          continue
        fi
        tui_run_terminal "Chat: $model" chat_model "$model" "$context"
        ;;
      1|255|-1)
        return 0
        ;;
    esac
  done
}

tui_collect_local_model_rows() {
  local output="$1" order="${2:-status:desc|rating:desc|size:asc|model:asc|codex:desc|category:asc}"
  local hw os arch chip device ram_gb running
  local name size_text size_value size_unit size_gb fit code_score code category description status display_size
  local unsorted

  : > "$output"
  command -v ollama >/dev/null 2>&1 || return 0
  start_ollama_if_possible >/dev/null 2>&1 || true

  hw="$(detect_hardware)"
  IFS='|' read -r os arch chip device ram_gb <<< "$hw"
  running="$(ollama ps 2>/dev/null | awk 'NR > 1 {print $1}' || true)"
  unsorted="$(mktemp -t ai-tui-local-unsorted.XXXXXX)"
  : > "$unsorted"

  while IFS='|' read -r name size_text; do
    [[ -n "$name" ]] || continue
    size_value="${size_text%% *}"
    size_unit="${size_text##* }"
    size_gb="$(size_to_gb "$size_value" "$size_unit")"
    fit="$(hardware_rating "$size_gb" "$ram_gb")"
    code_score="$(code_score_for_model "$name")"
    code="$(codex_rating_for_model "$name" installed)"
    category="$(model_category_for "$name")"
    description="$(model_description_for "$name")"
    if name_list_contains "$name" "$running"; then status="running"; else status="stopped"; fi
    display_size="$(format_size_gb "$size_gb")"
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$name" "$status" "$display_size" "$fit" "$code" "$category" "$description" >> "$unsorted"
  done < <(installed_models_data)

  sort_model_rows "$unsorted" "$output" "$order" "per-field"
  rm -f "$unsorted"
}

tui_collect_install_model_rows() {
  local output="$1" order="${2:-rating:desc|size:asc|model:asc|codex:desc|category:asc}"
  local hw os arch chip device ram_gb installed
  local family bytes name size_gb display_size fit code_score code category description
  local catalog unsorted

  hw="$(detect_hardware)"
  IFS='|' read -r os arch chip device ram_gb <<< "$hw"
  installed=""
  if command -v ollama >/dev/null 2>&1; then
    installed="$(ollama list 2>/dev/null | awk 'NR > 1 {print $1}' || true)"
  fi

  catalog="$(mktemp -t ai-tui-install-catalog.XXXXXX)"
  unsorted="$(mktemp -t ai-tui-install-unsorted.XXXXXX)"
  : > "$catalog"
  : > "$unsorted"

  remote_library_catalog > "$catalog" 2>/dev/null || true

  while IFS='|' read -r family bytes; do
    [[ -n "$family" ]] || continue
    name="${family}:latest"
    if name_list_contains "$name" "$installed"; then
      continue
    fi
    size_gb="$(bytes_to_gb "$bytes")"
    display_size="$(format_size_gb "$size_gb")"
    fit="$(hardware_rating "$size_gb" "$ram_gb")"
    code_score="$(code_score_for_model "$family")"
    code="$(codex_rating_for_model "$family" remote)"
    category="$(model_category_for "$family")"
    description="$(model_description_for "$family")"
    printf '%s\tavailable\t%s\t%s\t%s\t%s\t%s\n' \
      "$name" "$display_size" "$fit" "$code" "$category" "$description" >> "$unsorted"
  done < "$catalog"

  sort_model_rows "$unsorted" "$output" "$order" "per-field"
  rm -f "$catalog" "$unsorted"
}

tui_prepare_install_model_menu_data() {
  local input="$1" output="$2" header_file="$3" content_width="$4"
  (( content_width >= 50 )) || content_width=50

  LC_ALL=C awk -F '\t' -v OFS='\t' -v maxwidth="$content_width" -v header_file="$header_file" -v output="$output" '
    function clipped(s,w) {
      if (length(s) <= w) return s
      if (w <= 3) return substr(s,1,w)
      return substr(s,1,w-3) "..."
    }
    function spaces(n,   s,i) { s=""; for (i=0;i<n;i++) s=s " "; return s }
    BEGIN {
      h[1]="Model"; h[2]="Size"; h[3]="Rating"; h[4]="Codex"; h[5]="Category"
      for (i=1;i<=5;i++) w[i]=length(h[i])
    }
    NF >= 7 {
      rows[++n]=$0
      v[1]=$1; v[2]=$3; v[3]=$4; v[4]=$5; v[5]=$6
      for (i=1;i<=5;i++) if (length(v[i])>w[i]) w[i]=length(v[i])
    }
    END {
      separators=8
      fixed=w[2]+w[3]+w[4]+w[5]+separators
      model_space=maxwidth-fixed
      if (model_space < 14) model_space=14
      if (w[1] > model_space) w[1]=model_space
      header_core=sprintf("%-*s  %*s  %*s  %-*s  %-*s", w[1],h[1],w[2],h[2],w[3],h[3],w[4],h[4],w[5],h[5])
      pad=int((maxwidth-length(header_core))/2); if (pad<0) pad=0
      print spaces(pad) header_core > header_file
      for (r=1;r<=n;r++) {
        split(rows[r],a,"\\t")
        display=sprintf("%-*s  %*s  %*s  %-*s  %-*s", w[1],clipped(a[1],w[1]),w[2],a[3],w[3],a[4],w[4],a[5],w[5],a[6])
        printf "%06d\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n", r,a[1],a[2],a[3],a[4],a[5],a[6],a[7],display > output
      }
    }
  ' "$input"
}

tui_prepare_experimental_model_menu_data() {
  local input="$1" output="$2" header_file="$3" content_width="$4"
  (( content_width >= 48 )) || content_width=48

  LC_ALL=C awk -F '\t' -v OFS='\t' -v maxwidth="$content_width" -v header_file="$header_file" -v output="$output" '
    function clipped(s,w) { if(length(s)<=w)return s; if(w<=3)return substr(s,1,w); return substr(s,1,w-3) "..." }
    function spaces(n, s,i){s="";for(i=0;i<n;i++)s=s " ";return s}
    BEGIN { h[1]="Model";h[2]="Size";h[3]="Rating";h[4]="Category"; for(i=1;i<=4;i++)w[i]=length(h[i]) }
    NF>=7 {
      rows[++n]=$0; v[1]=$1;v[2]=$3;v[3]=$4;v[4]=$6
      for(i=1;i<=4;i++)if(length(v[i])>w[i])w[i]=length(v[i])
    }
    END {
      separators=6; fixed=w[2]+w[3]+w[4]+separators; model_space=maxwidth-fixed
      if(model_space<16)model_space=16; if(w[1]>model_space)w[1]=model_space
      header=sprintf("%-*s  %*s  %*s  %-*s",w[1],h[1],w[2],h[2],w[3],h[3],w[4],h[4])
      pad=int((maxwidth-length(header))/2);if(pad<0)pad=0; print spaces(pad) header > header_file
      for(r=1;r<=n;r++){
        split(rows[r],a,"\\t")
        display=sprintf("%-*s  %*s  %*s  %-*s",w[1],clipped(a[1],w[1]),w[2],a[3],w[3],a[4],w[4],a[6])
        printf "%06d\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n",r,a[1],a[2],a[3],a[4],a[5],a[6],a[7],display > output
      }
    }
  ' "$input"
}

tui_show_experimental_model_details() {
  local row="$1" model status size rating code category description tmp
  IFS=$'\t' read -r model status size rating code category description <<< "$row"
  tmp="$(mktemp -t ai-tui-experimental-details.XXXXXX)"
  cat > "$tmp" <<EOF
Model:       $model
Size:        $size
Rating:      $rating
Category:    $category

Description:
$description
EOF
  tui_show_text_file "Experimental Model Details" "$tmp"
  rm -f "$tmp"
}

tui_install_from_source_view() {
  local source
  while true; do
    if ! source="$(tui_capture_dialog --title "Install from Source" --cancel-label "Back" --ok-label "Install" --inputbox \
        "Enter a Hugging Face repository URL or a direct .gguf URL:" 11 86 "")"; then
      return 0
    fi
    [[ -n "$source" ]] || { tui_show_message "Install from Source" "Source URL cannot be empty."; continue; }
    tui_run_terminal "Install from Source" install_model_from_source "$source"
    return 0
  done
}

tui_experimental_models_view() {
  local order="rating:desc|size:asc|model:asc|category:asc" selected_model=""
  local rows data header rc result status output id row sort_result sorted_rows
  local hw os arch chip device ram_gb screen_cols screen_rows dialog_width dialog_height menu_height content_width default_id header_text
  local refresh_needed=1 layout_needed=1 last_content_width=0
  local -a items

  rc="$(tui_model_dialog_rc)"
  rows="$(mktemp -t ai-tui-experimental-rows.XXXXXX)"
  data="$(mktemp -t ai-tui-experimental-data.XXXXXX)"
  header="$(mktemp -t ai-tui-experimental-header.XXXXXX)"
  hw="$(detect_hardware)"; IFS='|' read -r os arch chip device ram_gb <<< "$hw"

  while true; do
    screen_cols="$(terminal_columns)"; screen_rows="$(terminal_lines)"
    dialog_width=$((screen_cols - 4)); dialog_height=$((screen_rows - 4))
    (( dialog_width >= 72 )) || dialog_width=72
    (( dialog_height >= 16 )) || dialog_height=16
    menu_height=$((dialog_height - 8)); (( menu_height >= 6 )) || menu_height=6
    content_width=$((dialog_width - 10))

    if (( refresh_needed == 1 )); then
      tui_dialog --title "Experimental Models" --infobox "Loading Experimental Ollama models..." 5 64 || true
      : > "$rows"
      collect_experimental_model_rows "$rows" "$order" "per-field" "$ram_gb" 1
      if [[ ! -s "$rows" ]]; then
        rm -f "$rows" "$data" "$header" "$rc"
        tui_show_message "Experimental Models" "No installable experimental models could be loaded."
        return 0
      fi
      refresh_needed=0; layout_needed=1
    fi

    if (( layout_needed == 1 || last_content_width != content_width )); then
      : > "$data"; : > "$header"
      tui_prepare_experimental_model_menu_data "$rows" "$data" "$header" "$content_width"
      last_content_width="$content_width"; layout_needed=0
    fi

    header_text="$(cat "$header")"; items=(); default_id=""
    while IFS=$'\t' read -r id model status size rating code category description display; do
      [[ -n "$id" ]] || continue
      items+=( "$id" "$display" )
      if [[ -n "$selected_model" && "$model" == "$selected_model" ]]; then default_id="$id"; fi
    done < "$data"
    [[ -n "$default_id" ]] || default_id="000001"

    result="$(tui_model_dialog_capture "$rc" \
      --title "Experimental Models" --default-item "$default_id" \
      --no-tags --no-hot-list --scrollbar --cr-wrap \
      --ok-label "Install" --cancel-label "Sort" \
      --extra-button --extra-label "Details" \
      --help-button --help-label "Back" --help-tags \
      --hline "Up/Down Navigate   Enter Install   F1 Details   F2 Sort   Esc Back" \
      --menu "$header_text" "$dialog_height" "$dialog_width" "$menu_height" "${items[@]}")"
    status="${result%%|*}"; output="${result#*|}"
    case "$status" in
      0)
        id="$output"; row="$(tui_model_row_by_id "$data" "$id")"
        if [[ -n "$row" ]]; then
          selected_model="${row%%$'\t'*}"
          if tui_confirm "Install experimental model" "Install $selected_model?"; then
            tui_run_terminal "Install model: $selected_model" install_model "$selected_model"
            refresh_needed=1
          fi
        fi
        ;;
      3)
        id="$output"; row="$(tui_model_row_by_id "$data" "$id")"
        [[ -n "$row" ]] && tui_show_experimental_model_details "$row"
        ;;
      1)
        if sort_result="$(tui_model_sort_menu "$order")"; then
          order="$sort_result"; sorted_rows="$(mktemp -t ai-tui-experimental-sorted.XXXXXX)"
          if sort_model_rows "$rows" "$sorted_rows" "$order" "per-field"; then mv "$sorted_rows" "$rows"; else rm -f "$sorted_rows"; fi
          layout_needed=1; dialog --clear >/dev/null 2>&1 || true
        fi
        ;;
      2|255|-1) rm -f "$rows" "$data" "$header" "$rc"; return 0 ;;
    esac
  done
}

tui_local_model_options() {
  local row="$1"
  local model status size fit code category description choice
  local -a items

  IFS=$'\t' read -r model status size fit code category description <<< "$row"

  while true; do
    if model_is_running "$model"; then status="running"; else status="stopped"; fi
    items=(
      "Agent"          "Open Codex Options with this model selected"
      "Chat"           "Open Chat Options with this model selected"
      "Run"            "Load this model into memory"
      "Stop"           "Stop this model"
      "Set as default" "Use this model as the default/base model"
      "Uninstall"      "Stop and remove this model"
    )

    if ! choice="$(tui_capture_dialog --title "Local Model Options" --cancel-label "Back" --menu \
        "Model: $model\nStatus: $status   Size: $size   Rating: $fit   Codex: $code   Category: $category" \
        0 0 12 "${items[@]}")"; then
      return 0
    fi

    case "$choice" in
      Agent)
        tui_agent_view "$model"
        ;;
      Chat)
        tui_chat_view "$model"
        ;;
      Run)
        tui_run_captured "Run model: $model" run_model "$model" ""
        ;;
      Stop)
        if model_is_running "$model"; then
          tui_run_captured "Stop model: $model" stop_model "$model"
        else
          tui_show_message "Stop model" "$model is already stopped."
        fi
        ;;
      "Set as default")
        tui_run_captured "Set default model: $model" set_base_model "$model"
        return 11
        ;;
      Uninstall)
        if tui_confirm "Uninstall model" "Remove $model from this computer?"; then
          tui_run_terminal "Uninstall model: $model" uninstall_model "$model"
          return 10
        fi
        ;;
    esac
  done
}

tui_local_models_view() {
  local order="status:desc|rating:desc|size:asc|model:asc|codex:desc|category:asc" selected_model=""
  local rows data header rc result status output id row sort_result action_status sorted_rows base_model
  local screen_cols screen_rows dialog_width dialog_height menu_height content_width default_id header_text
  local refresh_needed=1 layout_needed=1 last_content_width=0
  local -a items

  rc="$(tui_local_model_dialog_rc)"
  rows="$(mktemp -t ai-tui-local-rows.XXXXXX)"
  data="$(mktemp -t ai-tui-local-data.XXXXXX)"
  header="$(mktemp -t ai-tui-local-header.XXXXXX)"

  while true; do
    screen_cols="$(terminal_columns)"
    screen_rows="$(terminal_lines)"
    dialog_width=$((screen_cols - 4)); dialog_height=$((screen_rows - 4))
    (( dialog_width >= 72 )) || dialog_width=72
    (( dialog_height >= 16 )) || dialog_height=16
    menu_height=$((dialog_height - 8)); (( menu_height >= 6 )) || menu_height=6
    content_width=$((dialog_width - 10))

    if (( refresh_needed == 1 )); then
      : > "$rows"
      tui_collect_local_model_rows "$rows" "$order"
      if [[ ! -s "$rows" ]]; then
        rm -f "$rows" "$data" "$header" "$rc"
        tui_show_message "Local Models" "No local models are installed."
        return 0
      fi
      base_model="$(get_base_model)"
      refresh_needed=0
      layout_needed=1
    fi

    if (( layout_needed == 1 || last_content_width != content_width )); then
      : > "$data"; : > "$header"
      tui_prepare_model_menu_data "$rows" "$data" "$header" "$content_width" "$base_model"
      last_content_width="$content_width"
      layout_needed=0
    fi

    header_text="$(cat "$header")"
    items=(); default_id=""
    while IFS=$'\t' read -r id model status size fit code category description display; do
      [[ -n "$id" ]] || continue
      items+=( "$id" "$display" )
      if [[ -n "$selected_model" && "$model" == "$selected_model" ]]; then default_id="$id"; fi
    done < "$data"
    [[ -n "$default_id" ]] || default_id="000001"

    # dialog exposes four native action buttons. Keep the four per-model/navigation
    # actions as buttons and expose Stop All as a dedicated final list action.
    items+=( "__STOP_ALL__" "< Stop All >" )
    result="$(tui_model_dialog_capture "$rc" \
      --title "Local Models" \
      --default-item "$default_id" \
      --no-tags --no-hot-list --scrollbar --cr-wrap \
      --ok-label "Options" --cancel-label "Sort" \
      --extra-button --extra-label "Details" \
      --help-button --help-label "Back" --help-tags \
      --hline "Up/Down Navigate   Enter Options/Stop All   F1 Details   F2 Sort   Esc Back" \
      --menu "$header_text" "$dialog_height" "$dialog_width" "$menu_height" \
      "${items[@]}")"

    status="${result%%|*}"; output="${result#*|}"
    case "$status" in
      0)
        id="$output"
        if [[ "$id" == "__STOP_ALL__" ]]; then
          if tui_confirm "Stop all models" "Stop every model currently loaded by Ollama?"; then
            tui_run_captured "Stop all models" stop_all_models
            refresh_needed=1
          fi
          continue
        fi
        row="$(tui_model_row_by_id "$data" "$id")"
        if [[ -n "$row" ]]; then
          selected_model="${row%%$'\t'*}"
          if tui_local_model_options "$row"; then action_status=0; else action_status=$?; fi
          if (( action_status == 10 || action_status == 11 )); then refresh_needed=1; fi
          # Run/Stop/default may have changed list state even when options exits normally.
          refresh_needed=1
        fi
        ;;
      3)
        id="$output"
        [[ "$id" == "__STOP_ALL__" ]] && continue
        row="$(tui_model_row_by_id "$data" "$id")"
        if [[ -n "$row" ]]; then
          selected_model="${row%%$'\t'*}"
          tui_show_model_details "$row"
        fi
        ;;
      1)
        if sort_result="$(tui_model_sort_menu "$order")"; then
          order="$sort_result"
          sorted_rows="$(mktemp -t ai-tui-local-sorted.XXXXXX)"
          if sort_model_rows "$rows" "$sorted_rows" "$order" "per-field"; then mv "$sorted_rows" "$rows"; else rm -f "$sorted_rows"; fi
          layout_needed=1
          dialog --clear >/dev/null 2>&1 || true
        fi
        ;;
      2|255|-1)
        rm -f "$rows" "$data" "$header" "$rc"
        return 0
        ;;
    esac
  done
}

tui_install_models_view() {
  local order="rating:desc|size:asc|model:asc|codex:desc|category:asc" selected_model=""
  local rows data header rc result status output id row sort_result sorted_rows
  local screen_cols screen_rows dialog_width dialog_height menu_height content_width default_id header_text
  local refresh_needed=1 layout_needed=1 last_content_width=0
  local -a items

  rc="$(tui_model_dialog_rc)"
  rows="$(mktemp -t ai-tui-install-rows.XXXXXX)"
  data="$(mktemp -t ai-tui-install-data.XXXXXX)"
  header="$(mktemp -t ai-tui-install-header.XXXXXX)"

  while true; do
    screen_cols="$(terminal_columns)"; screen_rows="$(terminal_lines)"
    dialog_width=$((screen_cols - 4)); dialog_height=$((screen_rows - 4))
    (( dialog_width >= 72 )) || dialog_width=72
    (( dialog_height >= 16 )) || dialog_height=16
    menu_height=$((dialog_height - 8)); (( menu_height >= 6 )) || menu_height=6
    content_width=$((dialog_width - 10))

    if (( refresh_needed == 1 )); then
      tui_dialog --title "Install Models" --infobox "Loading Ollama Library catalog..." 5 64 || true
      : > "$rows"
      tui_collect_install_model_rows "$rows" "$order"
      if [[ ! -s "$rows" ]]; then
        rm -f "$rows" "$data" "$header" "$rc"
        tui_show_message "Install Models" "No installable models could be loaded."
        return 0
      fi
      refresh_needed=0; layout_needed=1
    fi

    if (( layout_needed == 1 || last_content_width != content_width )); then
      : > "$data"; : > "$header"
      tui_prepare_install_model_menu_data "$rows" "$data" "$header" "$content_width"
      last_content_width="$content_width"; layout_needed=0
    fi

    header_text="$(cat "$header")"
    items=(); default_id=""
    while IFS=$'\t' read -r id model status size fit code category description display; do
      [[ -n "$id" ]] || continue
      items+=( "$id" "$display" )
      if [[ -n "$selected_model" && "$model" == "$selected_model" ]]; then default_id="$id"; fi
    done < "$data"
    [[ -n "$default_id" ]] || default_id="000001"

    result="$(tui_model_dialog_capture "$rc" \
      --title "Install Models" \
      --default-item "$default_id" \
      --no-tags --no-hot-list --scrollbar --cr-wrap \
      --ok-label "Install" --cancel-label "Sort" \
      --extra-button --extra-label "Details" \
      --help-button --help-label "Back" --help-tags \
      --hline "Up/Down Navigate   Enter Install   F1 Details   F2 Sort   Esc Back" \
      --menu "$header_text" "$dialog_height" "$dialog_width" "$menu_height" \
      "${items[@]}")"

    status="${result%%|*}"; output="${result#*|}"
    case "$status" in
      0)
        id="$output"; row="$(tui_model_row_by_id "$data" "$id")"
        if [[ -n "$row" ]]; then
          selected_model="${row%%$'\t'*}"
          if tui_confirm "Install model" "Install $selected_model?"; then
            tui_run_terminal "Install model: $selected_model" install_model "$selected_model"
            refresh_needed=1
          fi
        fi
        ;;
      3)
        id="$output"; row="$(tui_model_row_by_id "$data" "$id")"
        if [[ -n "$row" ]]; then
          selected_model="${row%%$'\t'*}"
          tui_show_model_details "$row"
        fi
        ;;
      1)
        if sort_result="$(tui_model_sort_menu "$order")"; then
          order="$sort_result"
          sorted_rows="$(mktemp -t ai-tui-install-sorted.XXXXXX)"
          if sort_model_rows "$rows" "$sorted_rows" "$order" "per-field"; then mv "$sorted_rows" "$rows"; else rm -f "$sorted_rows"; fi
          layout_needed=1
          dialog --clear >/dev/null 2>&1 || true
        fi
        ;;
      2|255|-1)
        rm -f "$rows" "$data" "$header" "$rc"
        return 0
        ;;
    esac
  done
}

tui_models_menu() {
  local choice
  while true; do
    if ! choice="$(tui_capture_dialog --title "Models Menu" --cancel-label "Back" --menu \
        "Choose a model catalog:" 0 0 12 \
        "Local Models"        "Installed models and runtime actions" \
        "Install Models"      "Browse models available from the Ollama Library" \
        "Experimental Models" "Browse Experimental Ollama models" \
        "Install from Source" "Install from Hugging Face or a direct GGUF URL")"; then
      return 0
    fi
    case "$choice" in
      "Local Models") tui_local_models_view ;;
      "Install Models") tui_install_models_view ;;
      "Experimental Models") tui_experimental_models_view ;;
      "Install from Source") tui_install_from_source_view ;;
    esac
  done
}

tui_registry_latest_version() {
  local package="$1" url json version
  command -v curl >/dev/null 2>&1 || return 1
  case "$package" in
    npm) url="https://registry.npmjs.org/npm/latest" ;;
    codex) url="https://registry.npmjs.org/%40openai%2Fcodex/latest" ;;
    *) return 1 ;;
  esac
  json="$(curl -fsSL --connect-timeout 2 --max-time 5 "$url" 2>/dev/null || true)"
  [[ -n "$json" ]] || return 1
  version="$(printf '%s' "$json" | sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)"
  [[ -n "$version" ]] || return 1
  printf '%s\n' "$version"
}

tui_latest_ollama_version() {
  local url tag
  command -v curl >/dev/null 2>&1 || return 1
  url="$(curl -fsSL --connect-timeout 2 --max-time 5 -o /dev/null -w '%{url_effective}' \
    "https://github.com/ollama/ollama/releases/latest" 2>/dev/null || true)"
  [[ -n "$url" ]] || return 1
  tag="${url%/}"; tag="${tag##*/}"; tag="${tag#v}"
  [[ "$tag" =~ ^[0-9]+\.[0-9]+\.[0-9]+ ]] || return 1
  printf '%s\n' "$tag"
}

tui_collect_setup_components() {
  local output="$1" local_version latest state
  : > "$output"

  local_version=""
  if command -v ollama >/dev/null 2>&1; then local_version="$(ollama --version 2>/dev/null | extract_version || true)"; fi
  latest="$(tui_latest_ollama_version || true)"
  if [[ -z "$local_version" ]]; then state="not installed"; elif [[ -n "$latest" && "$local_version" != "$latest" ]]; then state="update"; else state="installed"; fi
  printf 'ollama\t%s\t%s\t%s\n' "$local_version" "$latest" "$state" >> "$output"

  local_version=""
  if command -v npm >/dev/null 2>&1; then local_version="$(npm --version 2>/dev/null || true)"; fi
  latest="$(tui_registry_latest_version npm || true)"
  if [[ -z "$local_version" ]]; then state="not installed"; elif [[ -n "$latest" && "$local_version" != "$latest" ]]; then state="update"; else state="installed"; fi
  printf 'npm\t%s\t%s\t%s\n' "$local_version" "$latest" "$state" >> "$output"

  local_version=""
  if command -v codex >/dev/null 2>&1; then local_version="$(codex --version 2>/dev/null | extract_version || true)"; fi
  latest="$(tui_registry_latest_version codex || true)"
  if [[ -z "$local_version" ]]; then state="not installed"; elif [[ -n "$latest" && "$local_version" != "$latest" ]]; then state="update"; else state="installed"; fi
  printf 'codex\t%s\t%s\t%s\n' "$local_version" "$latest" "$state" >> "$output"
}

tui_component_setup_display() {
  local component="$1" local_version="$2" latest="$3" state="$4" checked="$5"
  local mark="[ ]" version_text status_text
  [[ "$checked" == "1" ]] && mark="[x]"

  case "$state" in
    installed)
      if [[ -n "$local_version" ]]; then version_text="\\Z2v${local_version}\\Zn"; else version_text="\\Z2installed\\Zn"; fi
      status_text="[installed]"
      ;;
    update)
      version_text="\\Z2v${local_version}\\Zn -> \\Z3v${latest}\\Zn"
      status_text="\\Z3[update]\\Zn"
      ;;
    "not installed")
      if [[ -n "$latest" ]]; then version_text="\\Z3v${latest}\\Zn"; else version_text="version unavailable"; fi
      status_text="[not installed]"
      ;;
    *)
      version_text="${local_version:-unknown}"
      status_text="[$state]"
      ;;
  esac

  printf '%s %-10s %-30s %s' "$mark" "$component" "$version_text" "$status_text"
}

tui_execute_setup_selection() {
  local selection="$1" item
  local want_ollama=0 want_npm=0 want_codex=0
  for item in $selection; do
    case "$item" in
      ollama) want_ollama=1 ;;
      npm) want_npm=1 ;;
      codex) want_codex=1 ;;
    esac
  done

  if (( want_ollama == 1 )); then install_or_update_ollama; fi
  if (( want_npm == 1 )); then install_or_update_npm; fi
  if (( want_codex == 1 )); then
    # Codex is an npm package.  Selecting Codex on a machine without npm should
    # still be a useful action instead of failing half-way through.
    if ! command -v npm >/dev/null 2>&1; then install_or_update_npm; fi
    install_or_update_codex
  fi
}

tui_setup_view() {
  local data result status component local_version latest state selected_component="ollama"
  local sel_ollama=0 sel_npm=0 sel_codex=0 checked display selection
  local -a items

  data="$(mktemp -t ai-tui-setup.XXXXXX)"
  tui_dialog --title "Setup" --infobox "Checking installed and available component versions..." 5 70 || true
  tui_collect_setup_components "$data"

  while true; do
    items=()
    while IFS=$'\t' read -r component local_version latest state; do
      [[ -n "$component" ]] || continue
      checked=0
      case "$component" in
        ollama) checked="$sel_ollama" ;;
        npm) checked="$sel_npm" ;;
        codex) checked="$sel_codex" ;;
      esac
      display="$(tui_component_setup_display "$component" "$local_version" "$latest" "$state" "$checked")"
      items+=( "$component" "$display" )
    done < "$data"

    result="$(tui_dialog_capture_status \
      --title "Setup" --default-item "$selected_component" \
      --no-tags --no-hot-list \
      --ok-label "Select" --cancel-label "Back" \
      --extra-button --extra-label "Install" \
      --hline "Up/Down Navigate   Enter Select   Install Apply Selected   Esc Back" \
      --menu "Installed versions are green; available updates are yellow." 14 88 7 \
      "${items[@]}")"
    status="${result%%|*}"; component="${result#*|}"
    [[ -n "$component" ]] && selected_component="$component"

    case "$status" in
      0)
        case "$component" in
          ollama) if (( sel_ollama == 1 )); then sel_ollama=0; else sel_ollama=1; fi ;;
          npm) if (( sel_npm == 1 )); then sel_npm=0; else sel_npm=1; fi ;;
          codex) if (( sel_codex == 1 )); then sel_codex=0; else sel_codex=1; fi ;;
        esac
        ;;
      3)
        selection=""
        (( sel_ollama == 1 )) && selection="$selection ollama"
        (( sel_npm == 1 )) && selection="$selection npm"
        (( sel_codex == 1 )) && selection="$selection codex"
        if [[ -z "${selection// /}" ]]; then
          tui_show_message "Setup" "Select at least one component first."
          continue
        fi
        tui_run_terminal "Setup selected components" tui_execute_setup_selection "$selection"
        sel_ollama=0; sel_npm=0; sel_codex=0
        tui_dialog --title "Setup" --infobox "Refreshing component versions..." 5 60 || true
        tui_collect_setup_components "$data"
        ;;
      1|255|-1)
        rm -f "$data"
        return 0
        ;;
    esac
  done
}

tui_models_present() {
  if command -v ollama >/dev/null 2>&1; then
    if ollama list 2>/dev/null | awk 'NR > 1 {found=1; exit} END{exit !found}'; then
      return 0
    fi
  fi
  if [[ -d "$HOME/.ollama/models/manifests" ]]; then
    find "$HOME/.ollama/models/manifests" -type f -print -quit 2>/dev/null | grep -q . && return 0
  fi
  return 1
}

tui_collect_purge_components() {
  local output="$1" version
  : > "$output"
  if command -v ollama >/dev/null 2>&1; then
    version="$(ollama --version 2>/dev/null | extract_version || true)"
    printf 'ollama\t%s\n' "$version" >> "$output"
  fi
  if tui_models_present; then printf 'models\t\n' >> "$output"; fi
  if command -v npm >/dev/null 2>&1; then
    version="$(npm --version 2>/dev/null || true)"
    printf 'npm\t%s\n' "$version" >> "$output"
  fi
  if command -v codex >/dev/null 2>&1; then
    version="$(codex --version 2>/dev/null | extract_version || true)"
    printf 'codex\t%s\n' "$version" >> "$output"
  fi
}

tui_purge_component_display() {
  local component="$1" version="$2" checked="$3" mark="[ ]" version_text=""
  [[ "$checked" == "1" ]] && mark="[x]"
  if [[ -n "$version" ]]; then version_text="\\Z2v${version}\\Zn"; fi
  printf '%s %-10s %s' "$mark" "$component" "$version_text"
}

tui_purge_view() {
  local data result status component version selected_component=""
  local sel_ollama=0 sel_models=0 sel_npm=0 sel_codex=0 checked display selection summary
  local -a items

  data="$(mktemp -t ai-tui-purge.XXXXXX)"
  tui_collect_purge_components "$data"

  while true; do
    if [[ ! -s "$data" ]]; then
      rm -f "$data"
      tui_show_message "Purge" "No installed components or model data were found."
      return 0
    fi

    items=()
    while IFS=$'\t' read -r component version; do
      [[ -n "$component" ]] || continue
      [[ -n "$selected_component" ]] || selected_component="$component"
      checked=0
      case "$component" in
        ollama) checked="$sel_ollama" ;;
        models) checked="$sel_models" ;;
        npm) checked="$sel_npm" ;;
        codex) checked="$sel_codex" ;;
      esac
      display="$(tui_purge_component_display "$component" "$version" "$checked")"
      items+=( "$component" "$display" )
    done < "$data"

    result="$(tui_dialog_capture_status \
      --title "Purge" --default-item "$selected_component" \
      --no-tags --no-hot-list \
      --ok-label "Select" --cancel-label "Back" \
      --extra-button --extra-label "Purge" \
      --hline "Up/Down Navigate   Enter Select   Purge Remove Selected   Esc Back" \
      --menu "Only installed components are shown." 14 78 7 "${items[@]}")"
    status="${result%%|*}"; component="${result#*|}"
    [[ -n "$component" ]] && selected_component="$component"

    case "$status" in
      0)
        case "$component" in
          ollama) if (( sel_ollama == 1 )); then sel_ollama=0; else sel_ollama=1; fi ;;
          models) if (( sel_models == 1 )); then sel_models=0; else sel_models=1; fi ;;
          npm) if (( sel_npm == 1 )); then sel_npm=0; else sel_npm=1; fi ;;
          codex) if (( sel_codex == 1 )); then sel_codex=0; else sel_codex=1; fi ;;
        esac
        ;;
      3)
        selection=""; summary=""
        if (( sel_ollama == 1 )); then selection="$selection ollama"; summary="$summary\n  - ollama"; fi
        if (( sel_models == 1 )); then selection="$selection models"; summary="$summary\n  - models"; fi
        if (( sel_npm == 1 )); then selection="$selection npm"; summary="$summary\n  - npm"; fi
        if (( sel_codex == 1 )); then selection="$selection codex"; summary="$summary\n  - codex"; fi
        if [[ -z "${selection// /}" ]]; then
          tui_show_message "Purge" "Select at least one component first."
          continue
        fi
        if tui_confirm "Confirm purge" "Remove the selected components?\n$summary\n\nThis action cannot be undone."; then
          # tui_execute_purge_selection accepts newline-separated values in the
          # old UI.  Convert our compact selection to one item per line.
          tui_run_terminal "Purge selected components" tui_execute_purge_selection "$(printf '%s\n' $selection)"
          sel_ollama=0; sel_models=0; sel_npm=0; sel_codex=0; selected_component=""
          tui_collect_purge_components "$data"
        fi
        ;;
      1|255|-1)
        rm -f "$data"
        return 0
        ;;
    esac
  done
}

tui_system_menu() {
  local choice
  while true; do
    if ! choice="$(tui_capture_dialog --title "System Menu" --cancel-label "Back" --menu \
        "Toolchain setup and removal:" 0 0 10 \
        "Setup" "Install or update selected components" \
        "Purge" "Remove selected installed components")"; then
      return 0
    fi
    case "$choice" in
      Setup) tui_setup_view ;;
      Purge) tui_purge_view ;;
    esac
  done
}

tui_main() {
  local choice
  tui_require_dialog

  while true; do
    if ! choice="$(tui_capture_dialog --title "Main Menu" --cancel-label "Exit" --no-tags --menu \
        "Menu:" 0 0 12 \
        "agent"   "Agent" \
        "chat"    "Chat" \
        "image"   "Image Generation" \
        "models"  "Models" \
        "help"    "Help" \
        "system"  "System" \
        "version" "Version" \
        "exit"    "Exit")"; then
      break
    fi

    case "$choice" in
      agent) tui_agent_view ;;
      chat) tui_chat_view ;;
      image) tui_image_view ;;
      models) tui_models_menu ;;
      help) tui_show_help ;;
      system) tui_system_menu ;;
      version) tui_show_versions ;;
      exit) break ;;
    esac
  done

  dialog --clear >/dev/null 2>&1 || true
  tui_clear_terminal
}


# -----------------------------------------------------------------------------
# v1.9.1 - Draw Things backend integration
# -----------------------------------------------------------------------------

DRAW_THINGS_MODELS_DIR_DEFAULT="$HOME/Library/Containers/com.liuliu.draw-things/Data/Documents/Models"
DRAW_THINGS_REGISTRY="$CONFIG_DIR/draw-things-models.tsv"
DRAW_THINGS_CATALOG_CACHE="$CACHE_DIR/draw-things-catalog-v1.tsv"
DRAW_THINGS_CATALOG_TTL="${AI_DRAW_THINGS_CACHE_TTL:-86400}"
DRAW_THINGS_MODELS_URL="${AI_DRAW_THINGS_MODELS_URL:-https://models.drawthings.ai/models.json}"
DRAW_THINGS_SIZES_URL="${AI_DRAW_THINGS_SIZES_URL:-https://models.drawthings.ai/file_sizes_metadata.json}"


draw_things_models_dir() {
  printf '%s\n' "${DRAWTHINGS_MODELS_DIR:-$DRAW_THINGS_MODELS_DIR_DEFAULT}"
}


draw_things_cli_path() {
  local path prefix
  path="$(command -v draw-things-cli 2>/dev/null || true)"
  if [[ -n "$path" && -x "$path" ]]; then
    printf '%s\n' "$path"
    return 0
  fi
  load_homebrew_if_present || true
  path="$(command -v draw-things-cli 2>/dev/null || true)"
  if [[ -n "$path" && -x "$path" ]]; then
    printf '%s\n' "$path"
    return 0
  fi
  if command -v brew >/dev/null 2>&1; then
    prefix="$(brew --prefix draw-things-cli 2>/dev/null || true)"
    if [[ -n "$prefix" && -x "$prefix/bin/draw-things-cli" ]]; then
      printf '%s\n' "$prefix/bin/draw-things-cli"
      return 0
    fi
  fi
  return 1
}


draw_things_cli_installed() {
  draw_things_cli_path >/dev/null 2>&1 && return 0
  load_homebrew_if_present || true
  command -v brew >/dev/null 2>&1 && brew list --formula draw-things-cli >/dev/null 2>&1
}


draw_things_cli_version() {
  local cli version
  load_homebrew_if_present || true
  if command -v brew >/dev/null 2>&1 && brew list --formula draw-things-cli >/dev/null 2>&1; then
    version="$(brew list --versions draw-things-cli 2>/dev/null | awk 'NR==1{print $2}')"
    if [[ -n "$version" ]]; then printf '%s\n' "$version"; return 0; fi
  fi
  cli="$(draw_things_cli_path 2>/dev/null || true)"
  [[ -n "$cli" ]] || return 1
  version="$("$cli" --version 2>/dev/null | extract_version || true)"
  [[ -n "$version" ]] || return 1
  printf '%s\n' "$version"
}


draw_things_latest_version() {
  local json version
  load_homebrew_if_present || true
  command -v brew >/dev/null 2>&1 || return 1
  json="$(brew info --json=v2 draw-things-cli 2>/dev/null || true)"
  version="$(printf '%s' "$json" | sed -n 's/.*"stable"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)"
  [[ -n "$version" ]] || return 1
  printf '%s\n' "$version"
}


ensure_draw_things_cli() {
  local cli
  cli="$(draw_things_cli_path 2>/dev/null || true)"
  [[ -n "$cli" ]] || die "Draw Things CLI is not installed. Install it in System > Setup or run: ai --setup"
  printf '%s\n' "$cli"
}


install_or_update_draw_things_cli() {
  [[ "$(uname -s 2>/dev/null || true)" == "Darwin" ]] || \
    die "Draw Things CLI is currently supported by this script on macOS only."
  install_homebrew_if_needed
  info "Checking Draw Things CLI..."
  if brew list --formula draw-things-cli >/dev/null 2>&1; then
    if brew outdated --formula draw-things-cli 2>/dev/null | grep -qx 'draw-things-cli'; then
      info "Updating Draw Things CLI..."
      brew upgrade draw-things-cli
      success "Draw Things CLI updated to v$(draw_things_cli_version 2>/dev/null || printf unknown)."
    else
      success "Draw Things CLI is already installed (v$(draw_things_cli_version 2>/dev/null || printf unknown))."
    fi
  else
    info "Installing Draw Things CLI through Homebrew..."
    brew install draw-things-cli
    load_homebrew_if_present || true
    draw_things_cli_installed || die "Homebrew installed draw-things-cli, but it could not be located."
    success "Draw Things CLI installed (v$(draw_things_cli_version 2>/dev/null || printf unknown))."
  fi
}


draw_things_registry_add() {
  local model="$1" name="${2:-$1}" tmp
  mkdir -p "$CONFIG_DIR"
  tmp="$(mktemp -t ai-dt-registry.XXXXXX)"
  if [[ -f "$DRAW_THINGS_REGISTRY" ]]; then
    awk -F '\t' -v m="$model" '$1 != m' "$DRAW_THINGS_REGISTRY" > "$tmp" || true
  else
    : > "$tmp"
  fi
  printf '%s\t%s\n' "$model" "$name" >> "$tmp"
  mv "$tmp" "$DRAW_THINGS_REGISTRY"
}


draw_things_registry_remove() {
  local model="$1" tmp
  [[ -f "$DRAW_THINGS_REGISTRY" ]] || return 0
  tmp="$(mktemp -t ai-dt-registry.XXXXXX)"
  awk -F '\t' -v m="$model" '$1 != m' "$DRAW_THINGS_REGISTRY" > "$tmp" || true
  mv "$tmp" "$DRAW_THINGS_REGISTRY"
}


draw_things_cli_list_rows() {
  local downloaded_only="${1:-0}" cli dir
  cli="$(draw_things_cli_path 2>/dev/null || true)"
  [[ -n "$cli" ]] || return 0
  dir="$(draw_things_models_dir)"
  mkdir -p "$dir" 2>/dev/null || true
  if (( downloaded_only == 1 )); then
    "$cli" models list --models-dir "$dir" --downloaded-only 2>/dev/null
  else
    "$cli" models list --models-dir "$dir" 2>/dev/null
  fi | LC_ALL=C awk '
    BEGIN{FS="[[:space:]][[:space:]]+"; started=0}
    /^MODEL[[:space:]]+NAME[[:space:]]+SOURCE/ {started=1; next}
    started && /^-+[[:space:]]+-+/ {next}
    started && NF>=4 {
      model=$1; name=$2; source=$3; downloaded=$4; hf=(NF>=5?$5:"-")
      gsub(/^[[:space:]]+|[[:space:]]+$/,"",model)
      gsub(/^[[:space:]]+|[[:space:]]+$/,"",name)
      if(model!="" && model !~ /\.\.\.$/) print model "|" name "|" source "|" downloaded "|" hf
    }'
}


draw_things_downloaded_models() {
  local seen model name source downloaded hf
  seen="$(mktemp -t ai-dt-seen.XXXXXX)"
  : > "$seen"
  if [[ -f "$DRAW_THINGS_REGISTRY" ]]; then
    while IFS=$'\t' read -r model name; do
      [[ -n "$model" ]] || continue
      printf '%s|%s\n' "$model" "${name:-$model}"
      printf '%s\n' "$model" >> "$seen"
    done < "$DRAW_THINGS_REGISTRY"
  fi
  while IFS='|' read -r model name source downloaded hf; do
    [[ -n "$model" ]] || continue
    grep -Fqx "$model" "$seen" 2>/dev/null && continue
    printf '%s|%s\n' "$model" "${name:-$model}"
    printf '%s\n' "$model" >> "$seen"
  done < <(draw_things_cli_list_rows 1)
  rm -f "$seen"
}


draw_things_model_installed() {
  local target="$1" model name dir
  dir="$(draw_things_models_dir)"
  [[ -f "$dir/$target" || -f "$dir/$target-tensordata" ]] && return 0
  while IFS='|' read -r model name; do
    [[ "$model" == "$target" ]] && return 0
  done < <(draw_things_downloaded_models)
  return 1
}


draw_things_model_bytes() {
  local model="$1" dir total=0 file n
  dir="$(draw_things_models_dir)"
  for file in "$dir/$model" "$dir/$model-tensordata"; do
    [[ -f "$file" ]] || continue
    n="$(wc -c < "$file" 2>/dev/null | tr -d '[:space:]' || true)"
    [[ "$n" =~ ^[0-9]+$ ]] || n=0
    total=$((total + n))
  done
  printf '%s\n' "$total"
}


draw_things_category_for() {
  local value
  value="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$value" in
    *video*|*wan_*|*wan-*|*ltx_*|*ltx-*|*hunyuan*|*skyreels*|*longcat*|*cosmos*) printf 'Video\n' ;;
    *) printf 'Image\n' ;;
  esac
}


draw_things_catalog_cache_fresh() {
  local now mtime age
  [[ -s "$DRAW_THINGS_CATALOG_CACHE" ]] || return 1
  [[ "$DRAW_THINGS_CATALOG_TTL" =~ ^[0-9]+$ ]] || return 1
  now="$(date +%s)"
  mtime="$(file_mtime "$DRAW_THINGS_CATALOG_CACHE")"
  [[ "$mtime" =~ ^[0-9]+$ ]] || return 1
  age=$((now - mtime))
  (( age >= 0 && age < DRAW_THINGS_CATALOG_TTL ))
}


draw_things_remote_catalog_refresh() {
  local models sizes community official cli_rows sizes_tsv tmp bytes
  require_cmd curl
  mkdir -p "$CACHE_DIR"
  models="$(mktemp -t ai-dt-models-json.XXXXXX)"
  sizes="$(mktemp -t ai-dt-sizes-json.XXXXXX)"
  community="$(mktemp -t ai-dt-community.XXXXXX)"
  official="$(mktemp -t ai-dt-official.XXXXXX)"
  cli_rows="$(mktemp -t ai-dt-cli-list.XXXXXX)"
  sizes_tsv="$(mktemp -t ai-dt-sizes-tsv.XXXXXX)"
  tmp="$(mktemp -t ai-dt-catalog.XXXXXX)"
  : > "$community"; : > "$official"; : > "$cli_rows"; : > "$sizes_tsv"; : > "$tmp"

  if ! curl -fsSL --connect-timeout 5 --max-time 30 "$DRAW_THINGS_MODELS_URL" -o "$models"; then
    rm -f "$models" "$sizes" "$community" "$official" "$cli_rows" "$sizes_tsv" "$tmp"
    return 1
  fi
  curl -fsSL --connect-timeout 5 --max-time 30 "$DRAW_THINGS_SIZES_URL" -o "$sizes" 2>/dev/null || printf '[]' > "$sizes"

  if command -v node >/dev/null 2>&1; then
    node - "$models" "$sizes" > "$community" <<'NODE' || : > "$community"
const fs = require('fs');
const models = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
let sizes = [];
try { sizes = JSON.parse(fs.readFileSync(process.argv[3], 'utf8')); } catch (_) {}
const sm = new Map((Array.isArray(sizes)?sizes:[]).map(x => [x.file, Number(x.size)||0]));
const clean = x => String(x ?? '').replace(/[\t\r\n|]+/g, ' ').replace(/\s+/g, ' ').trim();
for (const m of models) {
  if (!m || !m.file || !m.name) continue;
  const note = clean(m.note || '');
  console.log([clean(m.file), String(sm.get(m.file)||0), clean(m.name), 'community', note].join('|'));
}
NODE
    node - "$sizes" > "$sizes_tsv" <<'NODE' || : > "$sizes_tsv"
const fs=require('fs'); let a=[]; try{a=JSON.parse(fs.readFileSync(process.argv[2],'utf8'))}catch(_){}
for(const x of (Array.isArray(a)?a:[])) if(x&&x.file) console.log(String(x.file).replace(/[\t\r\n|]+/g,' ')+'|'+(Number(x.size)||0));
NODE
  fi

  draw_things_cli_list_rows 0 > "$cli_rows" || true
  while IFS='|' read -r model name source downloaded hf; do
    [[ -n "$model" && "$source" == "official" ]] || continue
    bytes="$(awk -F'|' -v m="$model" '$1==m{print $2; exit}' "$sizes_tsv")"
    [[ "$bytes" =~ ^[0-9]+$ ]] || bytes=0
    printf '%s|%s|%s|official|%s\n' "$model" "$bytes" "$name" "$hf" >> "$official"
  done < "$cli_rows"

  cat "$official" "$community" | LC_ALL=C awk -F'|' '!seen[$1]++' | sort -t'|' -k1,1 > "$tmp"
  if [[ -s "$tmp" ]]; then
    mv "$tmp" "$DRAW_THINGS_CATALOG_CACHE"
  else
    rm -f "$tmp"
  fi
  rm -f "$models" "$sizes" "$community" "$official" "$cli_rows" "$sizes_tsv"
  [[ -s "$DRAW_THINGS_CATALOG_CACHE" ]]
}


draw_things_remote_catalog() {
  if draw_things_catalog_cache_fresh; then
    cat "$DRAW_THINGS_CATALOG_CACHE"
    return 0
  fi
  if draw_things_remote_catalog_refresh; then
    cat "$DRAW_THINGS_CATALOG_CACHE"
    return 0
  fi
  if [[ -s "$DRAW_THINGS_CATALOG_CACHE" ]]; then
    warn "Could not refresh the Draw Things catalog; using stale cache."
    cat "$DRAW_THINGS_CATALOG_CACHE"
    return 0
  fi
  # Last-resort CLI catalog without size metadata.
  local model name source downloaded hf
  while IFS='|' read -r model name source downloaded hf; do
    [[ -n "$model" ]] || continue
    printf '%s|0|%s|%s|%s\n' "$model" "$name" "$source" "$hf"
  done < <(draw_things_cli_list_rows 0)
}


collect_draw_things_model_rows() {
  local output="$1" order_spec="${2:-model}" direction="${3:-auto}" skip_installed="${4:-0}"
  local hw os arch chip device ram_gb model bytes name source note size_gb size rating category description installed unsorted
  hw="$(detect_hardware)"; IFS='|' read -r os arch chip device ram_gb <<< "$hw"
  installed="$(draw_things_downloaded_models | cut -d'|' -f1 || true)"
  unsorted="$(mktemp -t ai-dt-rows-unsorted.XXXXXX)"; : > "$unsorted"
  while IFS='|' read -r model bytes name source note; do
    [[ -n "$model" ]] || continue
    if (( skip_installed == 1 )) && printf '%s\n' "$installed" | grep -Fqx "$model"; then continue; fi
    size_gb="$(bytes_to_gb "$bytes")"
    size="$(format_size_gb "$size_gb")"
    rating="$(hardware_rating "$size_gb" "$ram_gb")"
    category="$(draw_things_category_for "$model $name")"
    description="$name"
    [[ -n "$source" ]] && description="$description [$source]"
    [[ -n "$note" && "$note" != "-" ]] && description="$description - $note"
    printf '%s\tavailable\t%s\t%s\tN/A\t%s\t%s\n' "$model" "$size" "$rating" "$category" "$description" >> "$unsorted"
  done < <(draw_things_remote_catalog)
  sort_model_rows "$unsorted" "$output" "$order_spec" "$direction"
  rm -f "$unsorted"
}


install_draw_things_model() {
  local model="$1" name="${2:-$1}" cli dir
  cli="$(ensure_draw_things_cli)"
  dir="$(draw_things_models_dir)"
  mkdir -p "$dir"
  info "Downloading Draw Things model: $name"
  "$cli" models ensure --models-dir "$dir" --model "$model"
  draw_things_registry_add "$model" "$name"
  success "Draw Things model installed: $name"
}


draw_things_catalog_name_for_model() {
  local target="$1" model bytes name source note
  while IFS='|' read -r model bytes name source note; do
    [[ "$model" == "$target" ]] || continue
    printf '%s\n' "${name:-$target}"
    return 0
  done < <(draw_things_remote_catalog 2>/dev/null || true)
  return 1
}


install_named_model() {
  local model="$1" backend="${2:-auto}" name=""
  case "$backend" in
    auto|"")
      case "$model" in
        *.ckpt|*.CKPT) backend="draw-things" ;;
        *) backend="ollama" ;;
      esac
      ;;
    ollama|draw-things)
      ;;
    *)
      die "Unknown backend: $backend. Expected: ollama or draw-things."
      ;;
  esac

  if [[ "$backend" == "draw-things" ]]; then
    name="$(draw_things_catalog_name_for_model "$model" 2>/dev/null || true)"
    install_draw_things_model "$model" "${name:-$model}"
  else
    install_model "$model"
  fi
}


uninstall_named_model() {
  local model="$1"
  if draw_things_model_installed "$model" || [[ "$model" == *.ckpt || "$model" == *.CKPT ]]; then
    uninstall_draw_things_model "$model"
  else
    uninstall_model "$model"
  fi
}


uninstall_draw_things_model() {
  local model="$1" dir
  dir="$(draw_things_models_dir)"
  rm -f "$dir/$model" "$dir/$model-tensordata"
  draw_things_registry_remove "$model"
  success "Draw Things model removed: $model"
}


source_is_http_url() {
  case "$1" in http://*|https://*) return 0 ;; *) return 1 ;; esac
}

source_basename_hint() {
  local source="$1" path
  if source_is_http_url "$source"; then
    path="${source%%\?*}"
    path="${path%%\#*}"
    printf '%s
' "${path##*/}"
  else
    printf '%s
' "${source##*/}"
  fi
}

draw_things_source_supported() {
  local base
  base="$(source_basename_hint "$1" | tr '[:upper:]' '[:lower:]')"
  case "$base" in
    *.ckpt|*.safetensors) return 0 ;;
    *) return 1 ;;
  esac
}

normalize_install_source_type() {
  local source_type="${1:-auto}"
  case "$source_type" in
    auto|model|lora) printf '%s
' "$source_type" ;;
    *) die "Unknown source type: $source_type. Expected: auto, model, or lora." ;;
  esac
}

guess_draw_things_source_type() {
  local source="$1" base lowered
  base="$(source_basename_hint "$source")"
  lowered="$(printf '%s' "$base" | tr '[:upper:]' '[:lower:]')"
  case "$lowered" in
    *lora*.ckpt|*lora*.safetensors|*lycoris*.safetensors|*adapter*.safetensors) printf 'lora
' ;;
    *) printf 'model
' ;;
  esac
}

install_draw_things_lora_source() {
  local cli="$1" dir="$2" artifact="$3"
  if "$cli" lora import --help >/dev/null 2>&1; then
    "$cli" lora import --models-dir "$dir" "$artifact" && return 0
  fi
  if "$cli" loras import --help >/dev/null 2>&1; then
    "$cli" loras import --models-dir "$dir" "$artifact" && return 0
  fi
  if "$cli" models import-lora --help >/dev/null 2>&1; then
    "$cli" models import-lora --models-dir "$dir" "$artifact" && return 0
  fi
  "$cli" models import --models-dir "$dir" "$artifact" && return 0
  return 1
}

install_model_from_source() {
  local source="$1" backend="${2:-auto}" requested_type="${3:-auto}" source_type hf_ref tmpdir url_path gguf modelfile local_name cli dir artifact base lowered
  [[ -n "$source" ]] || die "--source requires a URL or local file path."
  case "$backend" in auto|"") backend="auto" ;; ollama|draw-things) ;; *) die "Unknown backend: $backend" ;; esac
  source_type="$(normalize_install_source_type "$requested_type")"

  base="$(source_basename_hint "$source")"
  lowered="$(printf '%s' "$base" | tr '[:upper:]' '[:lower:]')"
  if [[ "$backend" == auto ]]; then
    if [[ "$source_type" == lora ]]; then
      backend="draw-things"
    elif draw_things_source_supported "$source"; then
      backend="draw-things"
    elif [[ -f "$source" && "$lowered" == *.gguf ]]; then
      backend="ollama"
    fi
  fi

  if [[ "$backend" == "draw-things" ]]; then
    cli="$(ensure_draw_things_cli)"
    dir="$(draw_things_models_dir)"
    mkdir -p "$dir"
    if [[ "$source_type" == auto ]]; then
      source_type="$(guess_draw_things_source_type "$source")"
    fi
    draw_things_source_supported "$source" || die "Draw Things source import supports .ckpt and .safetensors files only."
    if source_is_http_url "$source"; then
      require_cmd curl
      tmpdir="$(mktemp -d -t ai-dt-source.XXXXXX)"
      artifact="$tmpdir/$base"
      if [[ -z "$base" ]]; then
        if [[ "$source_type" == lora ]]; then artifact="$tmpdir/source-lora.safetensors"; else artifact="$tmpdir/source-model.safetensors"; fi
      fi
      info "Downloading Draw Things source: $source"
      if ! curl -fL --progress-bar "$source" -o "$artifact"; then rm -rf "$tmpdir"; die "Could not download: $source"; fi
    else
      [[ -f "$source" ]] || die "Source file does not exist: $source"
      artifact="$source"
      info "Importing Draw Things source file: $source"
    fi
    if [[ "$source_type" == lora ]]; then
      info "Importing LoRA through Draw Things CLI..."
      install_draw_things_lora_source "$cli" "$dir" "$artifact" || { [[ -n "$tmpdir" ]] && rm -rf "$tmpdir"; die "Draw Things could not import the LoRA source. Try a newer draw-things-cli version if your current build does not expose a dedicated LoRA import command."; }
      [[ -n "$tmpdir" ]] && rm -rf "$tmpdir"
      success "Draw Things LoRA import completed."
      return 0
    fi
    info "Importing model through Draw Things CLI..."
    "$cli" models import --models-dir "$dir" "$artifact" || { [[ -n "$tmpdir" ]] && rm -rf "$tmpdir"; die "Draw Things could not import the source model."; }
    [[ -n "$tmpdir" ]] && rm -rf "$tmpdir"
    success "Draw Things source import completed."
    return 0
  fi

  [[ "$source_type" != lora ]] || die "LoRA sources are currently supported only with --backend draw-things."
  ensure_ollama_cli
  ensure_ollama_api
  if source_is_http_url "$source"; then
    if hf_ref="$(normalize_huggingface_source "$source" 2>/dev/null)"; then
      info "Downloading Hugging Face model through Ollama: $hf_ref"
      ollama pull "$hf_ref"
      success "Model installed from source: $hf_ref"
      return 0
    fi
    url_path="${source%%\?*}"
    url_path="${url_path%%\#*}"
    case "$url_path" in
      *huggingface.co/*/blob/*/*.gguf|*huggingface.co/*/blob/*/*.GGUF) source="$(printf '%s' "$source" | sed 's#/blob/#/resolve/#')" ;;
      *.gguf|*.GGUF) ;;
      *.ckpt|*.CKPT|*.safetensors|*.SAFETENSORS)
        if [[ "$backend" == auto ]]; then install_model_from_source "$source" draw-things "$source_type"; return $?; fi
        die "Direct Ollama source URLs currently support GGUF files only. Use --backend draw-things for .ckpt or .safetensors sources." ;;
      *) die "Direct Ollama source URLs currently support GGUF files; pass a Hugging Face repository URL otherwise." ;;
    esac
    require_cmd curl
    tmpdir="$(mktemp -d -t ai-source-model.XXXXXX)"
    gguf="$tmpdir/model.gguf"
    modelfile="$tmpdir/Modelfile"
    local_name="$(source_model_name_from_url "$source")"
    info "Downloading GGUF source: $source"
    if ! curl -fL --progress-bar "$source" -o "$gguf"; then rm -rf "$tmpdir"; die "Could not download model source: $source"; fi
  else
    [[ -f "$source" ]] || die "Source file does not exist: $source"
    case "$lowered" in
      *.gguf) ;;
      *.ckpt|*.safetensors)
        if [[ "$backend" == auto ]]; then install_model_from_source "$source" draw-things "$source_type"; return $?; fi
        die "Local Ollama source files must be .gguf. Use --backend draw-things for .ckpt or .safetensors sources." ;;
      *) die "Unsupported local source file: $source. Ollama imports .gguf; Draw Things imports .ckpt or .safetensors." ;;
    esac
    tmpdir="$(mktemp -d -t ai-source-model.XXXXXX)"
    gguf="$tmpdir/${base:-model.gguf}"
    modelfile="$tmpdir/Modelfile"
    local_name="${base%.*}"
    info "Importing local GGUF source: $source"
    cp -f "$source" "$gguf" || { rm -rf "$tmpdir"; die "Could not copy local GGUF source."; }
  fi
  printf 'FROM %s
' "$gguf" > "$modelfile"
  ollama create "$local_name" -f "$modelfile" || { rm -rf "$tmpdir"; die "Ollama could not import the GGUF model."; }
  rm -rf "$tmpdir"
  success "Model installed from source as: $local_name"
}


# Preserve backend in an optional eighth row field while retaining all existing sort keys.
sort_model_rows() {
  local input="$1" output="$2" order_spec="$3" direction_override="$4"
  local enriched tab token key token_direction direction spec has_model=0
  local -a keys sort_args
  enriched="$(mktemp "${TMPDIR:-/tmp}/ai-sort.XXXXXX")"; tab="$(printf '\t')"
  LC_ALL=C awk -F '\t' 'BEGIN{OFS="\t"} NF>=7 {
    backend=(NF>=8?$8:"")
    status_rank=0
    if($2=="available") status_rank=1; else if($2=="stopped"||$2=="Stopped"||$2=="installed"||$2=="Installed") status_rank=2; else if($2=="running"||$2=="Running") status_rank=3; else if($2=="base") status_rank=4; else if($2=="base/run") status_rank=5
    size_num=$3; gsub(/[^0-9.]/,"",size_num); if(size_num=="") size_num=0
    rating_num=$4; gsub(/[^0-9.]/,"",rating_num); if(rating_num=="") rating_num=-1
    codex_rank=0; if($5=="Unknown")codex_rank=1; else if($5=="Limited")codex_rank=2; else if($5=="General")codex_rank=3; else if($5=="Good")codex_rank=4; else if($5=="Very good")codex_rank=5; else if($5=="Excellent")codex_rank=6
    print $1,$2,$3,$4,$5,$6,$7,backend,status_rank,size_num,rating_num,codex_rank
  }' "$input" > "$enriched"
  IFS='|' read -r -a keys <<< "$order_spec"; sort_args=( -s -t "$tab" )
  for token in "${keys[@]}"; do
    key="${token%%:*}"; token_direction=""; [[ "$token" == *:* ]] && token_direction="${token#*:}"
    if [[ "$direction_override" == "per-field" ]]; then direction="$token_direction"; [[ "$direction" == asc || "$direction" == desc ]] || { [[ "$key" == rating ]] && direction=desc || direction=asc; }
    else direction="$direction_override"; [[ "$direction" != auto ]] || { [[ "$key" == rating ]] && direction=desc || direction=asc; }; fi
    case "$key" in model) spec="1,1"; has_model=1 ;; status) spec="9,9n" ;; size) spec="10,10n" ;; rating) spec="11,11n" ;; codex) spec="12,12n" ;; category) spec="6,6" ;; description) spec="7,7" ;; *) rm -f "$enriched"; die "Internal error: unsupported sort field: $key" ;; esac
    [[ "$direction" != desc ]] || spec="${spec}r"; sort_args+=( "-k${spec}" )
  done
  (( has_model == 1 )) || sort_args+=( "-k1,1" )
  LC_ALL=C sort "${sort_args[@]}" "$enriched" | cut -f1-8 > "$output" || { rm -f "$enriched"; return 1; }
  rm -f "$enriched"
}


collect_combined_local_model_rows() {
  local output="$1" order="${2:-status:desc|rating:desc|size:asc|model:asc|codex:desc|category:asc}"
  local hw os arch chip device ram_gb running name size_text size_value size_unit size_gb rating codex category description status display_size unsorted model dt_name bytes
  : > "$output"; hw="$(detect_hardware)"; IFS='|' read -r os arch chip device ram_gb <<< "$hw"
  unsorted="$(mktemp -t ai-local-combined.XXXXXX)"; : > "$unsorted"
  if command -v ollama >/dev/null 2>&1; then
    start_ollama_if_possible >/dev/null 2>&1 || true
    running="$(ollama ps 2>/dev/null | awk 'NR>1{print $1}' || true)"
    while IFS='|' read -r name size_text; do
      [[ -n "$name" ]] || continue
      size_value="${size_text%% *}"; size_unit="${size_text##* }"; size_gb="$(size_to_gb "$size_value" "$size_unit")"
      rating="$(hardware_rating "$size_gb" "$ram_gb")"; codex="$(codex_rating_for_model "$name" installed)"; category="$(model_category_for "$name")"; description="$(model_description_for "$name")"
      if name_list_contains "$name" "$running"; then status="Running"; else status="Stopped"; fi
      display_size="$(format_size_gb "$size_gb")"
      printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\tOllama\n' "$name" "$status" "$display_size" "$rating" "$codex" "$category" "$description" >> "$unsorted"
    done < <(installed_models_data)
  fi
  while IFS='|' read -r model dt_name; do
    [[ -n "$model" ]] || continue
    bytes="$(draw_things_model_bytes "$model")"; size_gb="$(bytes_to_gb "$bytes")"; display_size="$(format_size_gb "$size_gb")"; rating="$(hardware_rating "$size_gb" "$ram_gb")"; category="$(draw_things_category_for "$model $dt_name")"
    printf '%s\tInstalled\t%s\t%s\tN/A\t%s\t%s\tDraw Things\n' "$model" "$display_size" "$rating" "$category" "$dt_name" >> "$unsorted"
  done < <(draw_things_downloaded_models)
  sort_model_rows "$unsorted" "$output" "$order" "per-field"
  rm -f "$unsorted"
}


tui_collect_local_model_rows() { collect_combined_local_model_rows "$@"; }


print_local_combined_table() {
  local file="$1" base="${2:-}" cols normalized_base=""
  cols="$(terminal_columns)"; [[ -z "$base" ]] || normalized_base="$(normalize_model_name "$base")"
  LC_ALL=C awk -F'\t' -v term="$cols" -v base="$normalized_base" '
    BEGIN{h1="Model";h2="Backend";h3="Status";h4="Size";h5="Rating";h6="Codex";h7="Category";w1=length(h1);w2=length(h2);w3=length(h3);w4=length(h4);w5=length(h5);w6=length(h6);w7=length(h7)}
    NF>=8{rows[++n]=$0; if(length($1)>w1)w1=length($1); if(length($8)>w2)w2=length($8); if(length($2)>w3)w3=length($2); if(length($3)>w4)w4=length($3); if(length($4)>w5)w5=length($4); if(length($5)>w6)w6=length($5); if(length($6)>w7)w7=length($6)}
    function line(w, s,i){s="";for(i=0;i<w;i++)s=s"-";return s}
    END{
      printf "%-*s  %-*s  %-*s  %*s  %*s  %-*s  %-*s\n",w1,h1,w2,h2,w3,h3,w4,h4,w5,h5,w6,h6,w7,h7
      printf "%-*s  %-*s  %-*s  %*s  %*s  %-*s  %-*s\n",w1,line(w1),w2,line(w2),w3,line(w3),w4,line(w4),w5,line(w5),w6,line(w6),w7,line(w7)
      for(r=1;r<=n;r++){split(rows[r],a,"\t");printf "%-*s  %-*s  %-*s  %*s  %*s  %-*s  %-*s\n",w1,a[1],w2,a[8],w3,a[2],w4,a[3],w5,a[4],w6,a[5],w7,a[6]}
    }' "$file"
}


print_hardware_summary_v191() {
  local hw os arch chip device ram_gb base
  hw="$(detect_hardware)"; IFS='|' read -r os arch chip device ram_gb <<< "$hw"; base="$(get_base_model)"
  printf '%s%b%s\n' "$LIST_HEADER" 'Hardware:' "$RESET"
  printf '  %-13s %s\n' 'Device:' "$device"; printf '  %-13s %s\n' 'CPU / SoC:' "$chip"; printf '  %-13s %s\n' 'Architecture:' "$arch"
  if [[ "$ram_gb" != 0 ]]; then printf '  %-13s %s GB%s\n' 'Memory:' "$ram_gb" "$([[ "$os" == Darwin && "$arch" == arm64 ]] && printf ' unified' || printf ' RAM')"; fi
  printf '  %-13s %s\n' 'Base model:' "${base:-not set}"
}


list_models_by_target() {
  local target="${1:-local}" order="${2:-model}" direction="${3:-auto}" rows hw os arch chip device ram_gb
  order="$(normalize_list_order "$order")"
  case "$target" in
    local|'')
      rows="$(mktemp -t ai-list-local.XXXXXX)"; collect_combined_local_model_rows "$rows" "$order"
      print_hardware_summary_v191; printf '\n%s%s%s\n' "$LIST_HEADER" 'Local models / Draw Things assets:' "$RESET"
      if [[ -s "$rows" ]]; then print_local_combined_table "$rows" "$(get_base_model)"; else printf '%s(no local models installed)%s\n' "$DIM" "$RESET"; fi
      rm -f "$rows"
      ;;
    ollama)
      rows="$(mktemp -t ai-list-ollama.XXXXXX)"; tui_collect_install_model_rows "$rows" "$order"
      print_hardware_summary_v191; printf '\n%s%s%s\n' "$LIST_HEADER" 'Available Ollama models:' "$RESET"
      [[ -s "$rows" ]] && print_dynamic_model_table "$rows" available || printf '%s(no Ollama catalog available)%s\n' "$DIM" "$RESET"; rm -f "$rows"
      ;;
    ollama-experimental)
      hw="$(detect_hardware)"; IFS='|' read -r os arch chip device ram_gb <<< "$hw"; rows="$(mktemp -t ai-list-ollama-exp.XXXXXX)"; collect_experimental_model_rows "$rows" "$order" "$direction" "$ram_gb" 0
      print_hardware_summary_v191; printf '\n%s%s%s\n' "$LIST_HEADER" 'Experimental Ollama models:' "$RESET"
      [[ -s "$rows" ]] && print_dynamic_model_table "$rows" experimental || printf '%s(no experimental models available)%s\n' "$DIM" "$RESET"; rm -f "$rows"
      ;;
    draw-things)
      rows="$(mktemp -t ai-list-dt.XXXXXX)"; collect_draw_things_model_rows "$rows" "$order" "$direction" 0
      print_hardware_summary_v191; printf '\n%s%s%s\n' "$LIST_HEADER" 'Draw Things models:' "$RESET"
      [[ -s "$rows" ]] && print_dynamic_model_table "$rows" experimental || printf '%s(no Draw Things catalog available)%s\n' "$DIM" "$RESET"; rm -f "$rows"
      ;;
    *) die "Unknown list target: $target. Expected: local, ollama, ollama-experimental, or draw-things." ;;
  esac
}


# Draw Things image generation backend.
generate_image_ollama() {
  local model="$1" width="$2" height="$3" output_dir="$4" file_name="$5" prompt="$6"
  local escaped_model escaped_prompt payload response b64 http_code error output_path
  ensure_ollama_cli; ensure_ollama_api; require_cmd curl; require_cmd base64
  [[ -n "$model" ]] || model="$(default_image_model 2>/dev/null || true)"
  [[ -n "$model" ]] || die "No installed Ollama image-generation model was found."
  model_is_installed "$model" || die "Image model is not installed: $model"
  model_supports_image_generation "$model" || die "Model $model does not advertise Ollama image-generation capability."
  width="$(validate_image_dimension width "$width")"; height="$(validate_image_dimension height "$height")"; [[ -n "$prompt" ]] || die "--prompt/-p is required."
  [[ -n "$output_dir" ]] || output_dir="$PWD"; [[ "$output_dir" != '~' ]] || output_dir="$HOME"; [[ "$output_dir" != '~/'* ]] || output_dir="$HOME/${output_dir#~/}"
  mkdir -p "$output_dir"; output_dir="$(cd "$output_dir" && pwd -P)"; file_name="$(normalize_image_file_name "$file_name")"; output_path="$output_dir/$file_name"
  payload="$(mktemp -t ai-image-payload.XXXXXX)"; response="$(mktemp -t ai-image-response.XXXXXX)"; b64="$(mktemp -t ai-image-base64.XXXXXX)"
  escaped_model="$(printf '%s' "$model" | json_escape_stdin)"; escaped_prompt="$(printf '%s' "$prompt" | json_escape_stdin)"
  printf '{"model":"%s","prompt":"%s","width":%s,"height":%s,"stream":false}\n' "$escaped_model" "$escaped_prompt" "$width" "$height" > "$payload"
  info "Generating image with $model (${width}x${height}) via Ollama..."
  http_code="$(curl -sS -o "$response" -w '%{http_code}' -H 'Content-Type: application/json' --data-binary "@$payload" "$OLLAMA_URL/api/generate" 2>/dev/null || printf 000)"
  case "$http_code" in 2??) ;; *) error="$(tr '\n\r' '  ' < "$response" | sed -n 's/.*"error"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"; rm -f "$payload" "$response" "$b64"; die "Image generation failed (HTTP $http_code)${error:+: $error}" ;; esac
  extract_image_base64 "$response" "$b64" || { rm -f "$payload" "$response" "$b64"; die "Ollama did not return an image."; }
  base64_decode_to_file "$b64" "$output_path" || { rm -f "$payload" "$response" "$b64"; die "Could not decode Ollama image."; }
  rm -f "$payload" "$response" "$b64"; success "Image saved: $output_path"
}


generate_image_draw_things() {
  local model="$1" width="$2" height="$3" output_dir="$4" file_name="$5" prompt="$6" cli dir output_path dtw dth
  cli="$(ensure_draw_things_cli)"; dir="$(draw_things_models_dir)"
  width="$(validate_image_dimension width "$width")"; height="$(validate_image_dimension height "$height")"
  dtw=$((width / 64 * 64)); dth=$((height / 64 * 64)); (( dtw >= 64 )) || dtw=64; (( dth >= 64 )) || dth=64
  if (( dtw != width || dth != height )); then warn "Draw Things requires dimensions divisible by 64; using ${dtw}x${dth}."; fi
  [[ -n "$output_dir" ]] || output_dir="$PWD"; mkdir -p "$output_dir"; output_dir="$(cd "$output_dir" && pwd -P)"; file_name="$(normalize_image_file_name "$file_name")"; output_path="$output_dir/$file_name"
  info "Generating image with $model (${dtw}x${dth}) via Draw Things..."
  "$cli" generate --models-dir "$dir" --model "$model" --prompt "$prompt" --width "$dtw" --height "$dth" --output "$output_path"
  [[ -s "$output_path" ]] || die "Draw Things finished without creating: $output_path"
  success "Image saved: $output_path"
}


default_image_model() {
  local base model name
  base="$(get_base_model)"
  if [[ -n "$base" ]] && model_is_installed "$base" && model_supports_image_generation "$base"; then printf '%s\n' "$base"; return 0; fi
  while IFS='|' read -r model name; do [[ "$(draw_things_category_for "$model $name")" == Image ]] || continue; printf '%s\n' "$model"; return 0; done < <(draw_things_downloaded_models)
  while IFS='|' read -r model name; do [[ -n "$model" ]] || continue; model_supports_image_generation "$model" && { printf '%s\n' "$model"; return 0; }; done < <(installed_models_data)
  return 1
}


generate_image() {
  local model="$1" width="$2" height="$3" output_dir="$4" file_name="$5" prompt="$6"
  [[ -n "$model" ]] || model="$(default_image_model 2>/dev/null || true)"
  [[ -n "$model" ]] || die "No installed image-generation model was found."
  if draw_things_model_installed "$model"; then generate_image_draw_things "$model" "$width" "$height" "$output_dir" "$file_name" "$prompt"; else generate_image_ollama "$model" "$width" "$height" "$output_dir" "$file_name" "$prompt"; fi
}


tui_select_image_model() {
  local title="${1:-Image Model}" default_model="${2:-}" name size model choice count=0
  local -a items args
  items=()
  if command -v ollama >/dev/null 2>&1; then
    start_ollama_if_possible >/dev/null 2>&1 || true
    while IFS='|' read -r name size; do [[ -n "$name" ]] || continue; if model_supports_image_generation "$name"; then items+=( "$name" "[Ollama] $size" ); count=$((count+1)); fi; done < <(installed_models_data)
  fi
  while IFS='|' read -r model name; do [[ "$(draw_things_category_for "$model $name")" == Image ]] || continue; items+=( "$model" "[Draw Things] $name" ); count=$((count+1)); done < <(draw_things_downloaded_models)
  if (( count == 0 )); then tui_show_message "$title" "No installed image-generation models were found.\n\nInstall one from Models > Ollama Experimental Models or Models > Install Draw Things Models."; return 1; fi
  args=( --title "$title" --cancel-label "Back" --menu "Select an installed image-generation model:" 0 0 14 ); [[ -z "$default_model" ]] || args=( --default-item "$default_model" "${args[@]}" )
  if choice="$(tui_capture_dialog "${args[@]}" "${items[@]}")"; then printf '%s\n' "$choice"; return 0; fi; return 1
}


# Setup/Purge UI: pipe-delimited records keep empty fields intact and wider labels stay aligned.
tui_component_setup_display() {
  local component="$1" local_version="$2" latest="$3" state="$4" checked="$5"
  local label mark="[ ]" version_plain version_color="" version_reset="" status_text
  [[ "$checked" == 1 ]] && mark="[x]"
  case "$component" in
    ollama) label="Ollama" ;;
    npm) label="npm" ;;
    codex) label="Codex" ;;
    dialog) label="dialog" ;;
    draw-things-cli) label="Draw Things CLI" ;;
    *) label="$component" ;;
  esac
  case "$state" in
    installed)
      version_plain="${local_version:-installed}"
      version_color="\\Z2"; version_reset="\\Zn"
      status_text="\\Z2[installed]\\Zn"
      ;;
    update)
      version_plain="${local_version:-?} -> ${latest:-?}"
      version_color="\\Z3"; version_reset="\\Zn"
      status_text="\\Z3[update]\\Zn"
      ;;
    'not installed')
      version_plain="${latest:+available: $latest}"
      [[ -n "$version_plain" ]] || version_plain="-"
      status_text="[not installed]"
      ;;
    *)
      version_plain="${local_version:--}"
      status_text="[$state]"
      ;;
  esac
  # Pad the plain text first. dialog color escapes must not participate in the
  # width calculation, otherwise colored and uncolored rows visibly drift.
  printf '%s %-18s %s%-34s%s %s' \
    "$mark" "$label" "$version_color" "$version_plain" "$version_reset" "$status_text"
}

tui_collect_setup_components() {
  local output="$1" local_version latest state
  : > "$output"
  local_version=""; command -v ollama >/dev/null 2>&1 && local_version="$(ollama --version 2>/dev/null | extract_version || true)"; latest="$(tui_latest_ollama_version || true)"; if [[ -z "$local_version" ]]; then state="not installed"; elif [[ -n "$latest" && "$local_version" != "$latest" ]]; then state=update; else state=installed; fi; printf 'ollama|%s|%s|%s\n' "$local_version" "$latest" "$state" >> "$output"
  local_version=""; command -v npm >/dev/null 2>&1 && local_version="$(npm --version 2>/dev/null || true)"; latest="$(tui_registry_latest_version npm || true)"; if [[ -z "$local_version" ]]; then state="not installed"; elif [[ -n "$latest" && "$local_version" != "$latest" ]]; then state=update; else state=installed; fi; printf 'npm|%s|%s|%s\n' "$local_version" "$latest" "$state" >> "$output"
  local_version=""; command -v codex >/dev/null 2>&1 && local_version="$(codex --version 2>/dev/null | extract_version || true)"; latest="$(tui_registry_latest_version codex || true)"; if [[ -z "$local_version" ]]; then state="not installed"; elif [[ -n "$latest" && "$local_version" != "$latest" ]]; then state=update; else state=installed; fi; printf 'codex|%s|%s|%s\n' "$local_version" "$latest" "$state" >> "$output"
  local_version=""; command -v dialog >/dev/null 2>&1 && local_version="$(dialog_version_string 2>/dev/null || true)"; [[ -n "$local_version" ]] && state=installed || state="not installed"; printf 'dialog|%s||%s\n' "$local_version" "$state" >> "$output"
  local_version="$(draw_things_cli_version 2>/dev/null || true)"; latest="$(draw_things_latest_version 2>/dev/null || true)"; if ! draw_things_cli_installed; then state="not installed"; local_version=""; elif [[ -n "$latest" && -n "$local_version" && "$latest" != "$local_version" ]]; then state=update; else state=installed; fi; printf 'draw-things-cli|%s|%s|%s\n' "$local_version" "$latest" "$state" >> "$output"
}


tui_execute_setup_selection() {
  local selection="$1" item want_ollama=0 want_npm=0 want_codex=0 want_dialog=0 want_dt=0
  for item in $selection; do case "$item" in ollama)want_ollama=1;; npm)want_npm=1;; codex)want_codex=1;; dialog)want_dialog=1;; draw-things-cli)want_dt=1;; esac; done
  (( want_ollama==0 )) || install_or_update_ollama; (( want_npm==0 )) || install_or_update_npm
  if (( want_codex==1 )); then command -v npm >/dev/null 2>&1 || install_or_update_npm; install_or_update_codex; fi
  (( want_dialog==0 )) || install_or_update_dialog; (( want_dt==0 )) || install_or_update_draw_things_cli
}


tui_setup_view() {
  local data result status component local_version latest state selected_component="ollama" checked display selection
  local sel_ollama=0 sel_npm=0 sel_codex=0 sel_dialog=0 sel_dt=0
  local -a items
  data="$(mktemp -t ai-tui-setup.XXXXXX)"; tui_dialog --title "Setup" --infobox "Checking installed and available component versions..." 5 70 || true; tui_collect_setup_components "$data"
  while true; do
    items=()
    while IFS='|' read -r component local_version latest state; do
      [[ -n "$component" ]] || continue; checked=0
      case "$component" in ollama)checked=$sel_ollama;; npm)checked=$sel_npm;; codex)checked=$sel_codex;; dialog)checked=$sel_dialog;; draw-things-cli)checked=$sel_dt;; esac
      display="$(tui_component_setup_display "$component" "$local_version" "$latest" "$state" "$checked")"; items+=( "$component" "$display" )
    done < "$data"
    result="$(tui_dialog_capture_status --title "Setup" --default-item "$selected_component" --no-tags --no-hot-list --ok-label "Select" --cancel-label "Back" --extra-button --extra-label "Install" --hline "Up/Down Navigate   Enter Select   Install Apply Selected   Esc Back" --menu "Installed versions are green; available updates are yellow." 16 100 9 "${items[@]}")"
    status="${result%%|*}"; component="${result#*|}"; [[ -z "$component" ]] || selected_component="$component"
    case "$status" in
      0) case "$component" in ollama)((sel_ollama=1-sel_ollama));; npm)((sel_npm=1-sel_npm));; codex)((sel_codex=1-sel_codex));; dialog)((sel_dialog=1-sel_dialog));; draw-things-cli)((sel_dt=1-sel_dt));; esac ;;
      3) selection=""; ((sel_ollama==0))||selection="$selection ollama"; ((sel_npm==0))||selection="$selection npm"; ((sel_codex==0))||selection="$selection codex"; ((sel_dialog==0))||selection="$selection dialog"; ((sel_dt==0))||selection="$selection draw-things-cli"; [[ -n "${selection// /}" ]] || { tui_show_message "Setup" "Select at least one component first."; continue; }; tui_run_terminal "Setup selected components" tui_execute_setup_selection "$selection"; sel_ollama=0;sel_npm=0;sel_codex=0;sel_dialog=0;sel_dt=0; tui_collect_setup_components "$data" ;;
      1|255|-1) rm -f "$data"; return 0 ;;
    esac
  done
}


tui_models_present() { command -v ollama >/dev/null 2>&1 && ollama list 2>/dev/null | awk 'NR>1{found=1} END{exit !found}' && return 0; [[ -d "$HOME/.ollama/models/manifests" ]] && find "$HOME/.ollama/models/manifests" -type f -print -quit 2>/dev/null | grep -q .; }

draw_things_models_present() { draw_things_downloaded_models | grep -q .; }


tui_collect_purge_components() {
  local output="$1" version; : > "$output"
  if command -v ollama >/dev/null 2>&1; then version="$(ollama --version 2>/dev/null | extract_version || true)"; printf 'ollama|%s\n' "$version" >> "$output"; fi
  if tui_models_present; then printf 'ollama-models|\n' >> "$output"; fi
  if command -v npm >/dev/null 2>&1; then printf 'npm|%s\n' "$(npm --version 2>/dev/null || true)" >> "$output"; fi
  if command -v codex >/dev/null 2>&1; then printf 'codex|%s\n' "$(codex --version 2>/dev/null | extract_version || true)" >> "$output"; fi
  if draw_things_cli_installed; then printf 'draw-things-cli|%s\n' "$(draw_things_cli_version 2>/dev/null || printf unknown)" >> "$output"; fi
  if draw_things_models_present; then printf 'draw-things-models|\n' >> "$output"; fi
}


tui_purge_component_display() {
  local component="$1" version="$2" checked="$3" label mark="[ ]" version_text=""
  [[ "$checked" == 1 ]] && mark="[x]"; case "$component" in ollama)label=Ollama;; ollama-models)label="Ollama Models";; npm)label=npm;; codex)label=Codex;; draw-things-cli)label="Draw Things CLI";; draw-things-models)label="Draw Things Models";; *)label="$component";; esac
  [[ -z "$version" ]] || version_text="\\Z2v${version}\\Zn"; printf '%s %-22s %s' "$mark" "$label" "$version_text"
}


purge_draw_things_cli_impl() { load_homebrew_if_present || true; if command -v brew >/dev/null 2>&1 && brew list --formula draw-things-cli >/dev/null 2>&1; then brew uninstall draw-things-cli; success "Draw Things CLI removed."; else warn "Draw Things CLI is not installed through Homebrew."; fi; }
purge_draw_things_models_impl() { local dir; dir="$(draw_things_models_dir)"; if [[ -d "$dir" ]]; then find "$dir" -mindepth 1 -maxdepth 1 -exec rm -rf {} +; fi; rm -f "$DRAW_THINGS_REGISTRY"; success "Draw Things models removed."; }
purge_draw_things_cli() { confirm_purge "this will remove Draw Things CLI only."; purge_draw_things_cli_impl; }
purge_draw_things_models() { confirm_purge "this will remove all Draw Things model data."; purge_draw_things_models_impl; }


tui_execute_purge_selection() {
  local selection="$1" item want_ollama=0 want_om=0 want_npm=0 want_codex=0 want_dt=0 want_dtm=0
  while IFS= read -r item; do case "$item" in ollama)want_ollama=1;; ollama-models|models)want_om=1;; npm)want_npm=1;; codex)want_codex=1;; draw-things-cli)want_dt=1;; draw-things-models)want_dtm=1;; esac; done <<< "$selection"
  export AI_PURGE_FORCE=1; ((want_codex==0))||purge_codex_impl; ((want_npm==0))||purge_npm_impl; ((want_dt==0))||purge_draw_things_cli_impl; ((want_dtm==0))||purge_draw_things_models_impl
  if ((want_ollama==1 && want_om==1)); then purge_ollama_and_models_impl; elif ((want_om==1)); then purge_models_impl; elif ((want_ollama==1)); then purge_ollama_only_impl; fi
}


tui_purge_view() {
  local data result status component version selected_component="" checked display selection summary
  local so=0 som=0 sn=0 sc=0 sd=0 sdm=0
  local -a items
  data="$(mktemp -t ai-tui-purge.XXXXXX)"; tui_collect_purge_components "$data"
  while true; do
    [[ -s "$data" ]] || { rm -f "$data"; tui_show_message "Purge" "No installed components or model data were found."; return 0; }
    items=(); while IFS='|' read -r component version; do [[ -n "$component" ]] || continue; [[ -n "$selected_component" ]] || selected_component="$component"; checked=0; case "$component" in ollama)checked=$so;; ollama-models)checked=$som;; npm)checked=$sn;; codex)checked=$sc;; draw-things-cli)checked=$sd;; draw-things-models)checked=$sdm;; esac; display="$(tui_purge_component_display "$component" "$version" "$checked")"; items+=( "$component" "$display" ); done < "$data"
    result="$(tui_dialog_capture_status --title "Purge" --default-item "$selected_component" --no-tags --no-hot-list --ok-label "Select" --cancel-label "Back" --extra-button --extra-label "Purge" --hline "Up/Down Navigate   Enter Select   Purge Remove Selected   Esc Back" --menu "Only installed components are shown." 16 88 9 "${items[@]}")"; status="${result%%|*}"; component="${result#*|}"; [[ -z "$component" ]] || selected_component="$component"
    case "$status" in
      0) case "$component" in ollama)((so=1-so));; ollama-models)((som=1-som));; npm)((sn=1-sn));; codex)((sc=1-sc));; draw-things-cli)((sd=1-sd));; draw-things-models)((sdm=1-sdm));; esac ;;
      3) selection=""; summary=""; for pair in "ollama:$so" "ollama-models:$som" "npm:$sn" "codex:$sc" "draw-things-cli:$sd" "draw-things-models:$sdm"; do component="${pair%%:*}"; checked="${pair#*:}"; if [[ "$checked" == 1 ]]; then selection="$selection $component"; summary="$summary\n  - $component"; fi; done; [[ -n "${selection// /}" ]] || { tui_show_message "Purge" "Select at least one component first."; continue; }; if tui_confirm "Confirm purge" "Remove the selected components?\n$summary\n\nThis action cannot be undone."; then tui_run_terminal "Purge selected components" tui_execute_purge_selection "$(printf '%s\n' $selection)"; so=0;som=0;sn=0;sc=0;sd=0;sdm=0;selected_component="";tui_collect_purge_components "$data"; fi ;;
      1|255|-1) rm -f "$data"; return 0 ;;
    esac
  done
}


purge_all() { confirm_purge "this will remove Ollama, Ollama models, Codex CLI, npm, Draw Things CLI, and Draw Things models."; purge_codex_impl; purge_npm_impl; purge_draw_things_cli_impl; purge_draw_things_models_impl; purge_ollama_and_models_impl; rm -rf "$CONFIG_DIR"; success "Full AI toolchain purge complete."; }
purge_component() { if [[ $# -eq 0 ]]; then purge_default; return; fi; [[ $# -eq 1 ]] || die "--purge accepts one component only."; case "$1" in '*')purge_all;; ollama)purge_ollama_only;; models|ollama-models)purge_models;; npm)purge_npm;; codex)purge_codex;; draw-things-cli)purge_draw_things_cli;; draw-things-models)purge_draw_things_models;; *)die "Unknown purge component: $1";; esac; }


setup_all() {
  require_cmd curl; printf '%b\n\n' "${BOLD}AI toolchain setup${RESET}"
  info "[1/5] Checking Ollama..."; install_or_update_ollama
  printf '\n'; info "[2/5] Checking Node.js + npm..."; install_or_update_npm
  printf '\n'; info "[3/5] Checking Codex CLI..."; install_or_update_codex
  printf '\n'; info "[4/5] Checking dialog TUI..."; install_or_update_dialog
  printf '\n'; info "[5/5] Checking Draw Things CLI..."; install_or_update_draw_things_cli
  printf '\n'; success "AI toolchain setup is complete."
}


path_disk_bytes() {
  local path="$1" kb
  [[ -e "$path" || -L "$path" ]] || { printf '0\n'; return 0; }
  kb="$(du -skL "$path" 2>/dev/null | awk 'NR==1{print $1}' || true)"
  [[ "$kb" =~ ^[0-9]+$ ]] || kb=0
  printf '%s\n' "$((kb * 1024))"
}

human_size_bytes() {
  local bytes="$1"
  [[ "$bytes" =~ ^[0-9]+$ ]] || bytes=0
  LC_NUMERIC=C awk -v b="$bytes" 'BEGIN {
    if (b >= 1000000000000) printf "%.1f TB", b/1000000000000
    else if (b >= 1000000000) printf "%.1f GB", b/1000000000
    else if (b >= 1000000) printf "%.1f MB", b/1000000
    else if (b >= 1000) printf "%.1f KB", b/1000
    else printf "%d B", b
  }'
}

brew_component_path() {
  local formula="$1" fallback_cmd="${2:-$1}" prefix=""
  if command -v brew >/dev/null 2>&1 && brew list --formula "$formula" >/dev/null 2>&1; then
    prefix="$(brew --prefix "$formula" 2>/dev/null || true)"
    [[ -n "$prefix" && -e "$prefix" ]] && { printf '%s\n' "$prefix"; return 0; }
  fi
  command -v "$fallback_cmd" 2>/dev/null || true
}

npm_package_path() {
  local package="$1" root
  command -v npm >/dev/null 2>&1 || return 0
  root="$(npm root -g 2>/dev/null || true)"
  [[ -n "$root" && -e "$root/$package" ]] && printf '%s\n' "$root/$package"
}

ollama_models_dir() {
  if [[ -n "${OLLAMA_MODELS:-}" ]]; then printf '%s\n' "$OLLAMA_MODELS"; else printf '%s\n' "$HOME/.ollama/models"; fi
}

component_disk_size() {
  local component="$1" path=""
  case "$component" in
    ai) path="${BASH_SOURCE[0]}" ;;
    ollama) path="$(brew_component_path ollama ollama)" ;;
    npm)
      path="$(npm_package_path npm)"
      [[ -n "$path" ]] || path="$(command -v npm 2>/dev/null || true)"
      ;;
    codex)
      path="$(npm_package_path @openai/codex)"
      [[ -n "$path" ]] || path="$(command -v codex 2>/dev/null || true)"
      ;;
    dialog) path="$(brew_component_path dialog dialog)" ;;
    draw-things-cli)
      path="$(brew_component_path draw-things-cli draw-things-cli)"
      [[ -n "$path" ]] || path="$(draw_things_cli_path 2>/dev/null || true)"
      ;;
  esac
  [[ -n "$path" ]] || { printf '%s\n' '-'; return 0; }
  human_size_bytes "$(path_disk_bytes "$path")"
  printf '\n'
}

model_storage_bytes() {
  local backend="$1" path
  case "$backend" in
    ollama) path="$(ollama_models_dir)" ;;
    draw-things) path="$(draw_things_models_dir)" ;;
    *) printf '0\n'; return 0 ;;
  esac
  path_disk_bytes "$path"
}

local_models_storage_summary() {
  local ollama_bytes dt_bytes total_bytes
  ollama_bytes="$(model_storage_bytes ollama)"
  dt_bytes="$(model_storage_bytes draw-things)"
  total_bytes=$((ollama_bytes + dt_bytes))
  printf 'Ollama models: %s | Draw Things: %s | Total: %s\n' \
    "$(human_size_bytes "$ollama_bytes")" "$(human_size_bytes "$dt_bytes")" "$(human_size_bytes "$total_bytes")"
}

show_versions() {
  local ollama_version npm_version codex_version dialog_version dt_version
  local ollama_size npm_size codex_size dialog_size dt_size ai_size
  local ollama_models_bytes dt_models_bytes models_total_bytes
  ollama_version="$(component_version_or_missing ollama ollama --version)"
  command -v npm >/dev/null 2>&1 && npm_version="v$(npm --version 2>/dev/null || true)" || npm_version="not installed"
  codex_version="$(component_version_or_missing codex codex --version)"
  command -v dialog >/dev/null 2>&1 && dialog_version="$(dialog_version_string)" || dialog_version="not installed"
  draw_things_cli_installed && dt_version="v$(draw_things_cli_version 2>/dev/null || printf unknown)" || dt_version="not installed"

  ai_size="$(component_disk_size ai)"
  [[ "$ollama_version" == "not installed" ]] && ollama_size="-" || ollama_size="$(component_disk_size ollama)"
  [[ "$npm_version" == "not installed" ]] && npm_size="-" || npm_size="$(component_disk_size npm)"
  [[ "$codex_version" == "not installed" ]] && codex_size="-" || codex_size="$(component_disk_size codex)"
  [[ "$dialog_version" == "not installed" ]] && dialog_size="-" || dialog_size="$(component_disk_size dialog)"
  [[ "$dt_version" == "not installed" ]] && dt_size="-" || dt_size="$(component_disk_size draw-things-cli)"

  printf '%-22s %-34s %12s\n' 'Component' 'Version' 'Disk size'
  printf '%-22s %-34s %12s\n' '----------------------' '----------------------------------' '------------'
  printf '%-22s %-34s %12s\n' 'AI Model Manager' "v$SCRIPT_VERSION" "$ai_size"
  printf '%-22s %-34s %12s\n' 'Ollama' "$ollama_version" "$ollama_size"
  printf '%-22s %-34s %12s\n' 'npm' "$npm_version" "$npm_size"
  printf '%-22s %-34s %12s\n' 'Codex' "$codex_version" "$codex_size"
  printf '%-22s %-34s %12s\n' 'dialog' "$dialog_version" "$dialog_size"
  printf '%-22s %-34s %12s\n' 'Draw Things CLI' "$dt_version" "$dt_size"

  ollama_models_bytes="$(model_storage_bytes ollama)"
  dt_models_bytes="$(model_storage_bytes draw-things)"
  models_total_bytes=$((ollama_models_bytes + dt_models_bytes))
  printf '\nModel storage:\n'
  printf '%-38s %12s\n' 'Ollama models' "$(human_size_bytes "$ollama_models_bytes")"
  printf '%-38s %12s\n' 'Draw Things models / assets' "$(human_size_bytes "$dt_models_bytes")"
  printf '%-38s %12s\n' 'Total model storage' "$(human_size_bytes "$models_total_bytes")"
  printf '\n%s\n' 'Disk sizes are approximate allocated/installed sizes; shared package dependencies are not attributed across tools.'
}

prepare_local_combined_menu_data() {
  local input="$1" output="$2" header_file="$3" content_width="$4" base_model="${5:-}"
  ((content_width>=70)) || content_width=70
  LC_ALL=C awk -F'\t' -v output="$output" -v header_file="$header_file" -v maxwidth="$content_width" -v base="$base_model" '
    function clip(s,w){if(length(s)<=w)return s;if(w<=3)return substr(s,1,w);return substr(s,1,w-3)"..."}
    BEGIN{h[1]="Model";h[2]="Backend";h[3]="Status";h[4]="Size";h[5]="Rating";h[6]="Codex";h[7]="Category";for(i=1;i<=7;i++)w[i]=length(h[i])}
    NF>=8{rows[++n]=$0; vals[1]=$1;vals[2]=$8;vals[3]=$2;vals[4]=$3;vals[5]=$4;vals[6]=$5;vals[7]=$6;for(i=1;i<=7;i++)if(length(vals[i])>w[i])w[i]=length(vals[i])}
    END{sep=12; fixed=w[2]+w[3]+w[4]+w[5]+w[6]+w[7]+sep; avail=maxwidth-fixed; if(avail<18)avail=18;if(w[1]>avail)w[1]=avail; header=sprintf("%-*s  %-*s  %-*s  %*s  %*s  %-*s  %-*s",w[1],h[1],w[2],h[2],w[3],h[3],w[4],h[4],w[5],h[5],w[6],h[6],w[7],h[7]);print header > header_file; for(r=1;r<=n;r++){split(rows[r],a,"\t");display=sprintf("%-*s  %-*s  %-*s  %*s  %*s  %-*s  %-*s",w[1],clip(a[1],w[1]),w[2],a[8],w[3],a[2],w[4],a[3],w[5],a[4],w[6],a[5],w[7],a[6]);printf "%06d\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n",r,a[1],a[2],a[3],a[4],a[5],a[6],a[7],a[8],display > output}}
  ' "$input"
}


tui_local_combined_row_by_id() { LC_ALL=C awk -F'\t' -v id="$2" 'BEGIN{OFS="\t"}$1==id{print $2,$3,$4,$5,$6,$7,$8,$9;exit}' "$1"; }


tui_show_model_details() {
  local row="$1" model status size rating codex category description backend tmp
  IFS=$'\t' read -r model status size rating codex category description backend <<< "$row"
  tmp="$(mktemp -t ai-model-details.XXXXXX)"; cat > "$tmp" <<EOF
Model:       $model
Backend:     ${backend:-Ollama}
Status:      $status
Size:        $size
Rating:      $rating
Codex:       $codex
Category:    $category

Description:
$description
EOF
  tui_show_text_file "Model Details" "$tmp"; rm -f "$tmp"
}


tui_local_model_options() {
  local row="$1" model status size rating codex category description backend choice
  local -a items
  IFS=$'\t' read -r model status size rating codex category description backend <<< "$row"; [[ -n "$backend" ]] || backend=Ollama
  if [[ "$backend" == "Draw Things" ]]; then
    while true; do
      items=( "Image" "Open Image Generation with this model" "Uninstall" "Remove this Draw Things model" )
      if ! choice="$(tui_capture_dialog --title "Local Model Options" --cancel-label "Back" --menu "Model: $model\nBackend: Draw Things   Size: $size   Rating: $rating   Category: $category" 0 0 10 "${items[@]}")"; then return 0; fi
      case "$choice" in Image)tui_image_view "$model";; Uninstall)if tui_confirm "Uninstall model" "Remove $model? Shared dependencies are kept."; then tui_run_terminal "Uninstall Draw Things model" uninstall_draw_things_model "$model"; return 10; fi;; esac
    done
  fi
  while true; do
    if model_is_running "$model"; then status=running; else status=stopped; fi
    items=( "Agent" "Open Codex Options with this model selected" "Chat" "Open Chat Options with this model selected" "Run" "Load this model into memory" "Stop" "Stop this model" "Set as default" "Use this model as the default/base model" "Uninstall" "Stop and remove this model" )
    if ! choice="$(tui_capture_dialog --title "Local Model Options" --cancel-label "Back" --menu "Model: $model\nBackend: Ollama   Status: $status   Size: $size   Rating: $rating   Codex: $codex" 0 0 12 "${items[@]}")"; then return 0; fi
    case "$choice" in Agent)tui_agent_view "$model";; Chat)tui_chat_view "$model";; Run)tui_run_captured "Run model: $model" run_model "$model" "";; Stop)model_is_running "$model" && tui_run_captured "Stop model: $model" stop_model "$model" || tui_show_message "Stop model" "$model is already stopped.";; "Set as default")tui_run_captured "Set default model" set_base_model "$model"; return 11;; Uninstall)if tui_confirm "Uninstall model" "Remove $model?"; then tui_run_terminal "Uninstall model" uninstall_model "$model"; return 10; fi;; esac
  done
}


tui_local_models_view() {
  local order="status:desc|rating:desc|size:asc|model:asc|codex:desc|category:asc" selected_model="" rows data header rc result status output id row sort_result action_status sorted_rows base_model
  local screen_cols screen_rows dialog_width dialog_height menu_height content_width default_id header_text
  local refresh_needed=1 layout_needed=1 last_content_width=0
  local -a items
  rc="$(tui_local_model_dialog_rc)"; rows="$(mktemp -t ai-local-rows.XXXXXX)"; data="$(mktemp -t ai-local-data.XXXXXX)"; header="$(mktemp -t ai-local-header.XXXXXX)"
  while true; do
    screen_cols="$(terminal_columns)";screen_rows="$(terminal_lines)";dialog_width=$((screen_cols-4));dialog_height=$((screen_rows-4));((dialog_width>=82))||dialog_width=82;((dialog_height>=16))||dialog_height=16;menu_height=$((dialog_height-8));((menu_height>=6))||menu_height=6;content_width=$((dialog_width-10))
    if ((refresh_needed==1)); then : > "$rows";collect_combined_local_model_rows "$rows" "$order";if [[ ! -s "$rows" ]];then rm -f "$rows" "$data" "$header" "$rc";tui_show_message "Local Models" "No local models are installed.";return 0;fi;base_model="$(get_base_model)";refresh_needed=0;layout_needed=1;fi
    if ((layout_needed==1 || last_content_width!=content_width));then :>"$data";:>"$header";prepare_local_combined_menu_data "$rows" "$data" "$header" "$content_width" "$base_model";last_content_width=$content_width;layout_needed=0;fi
    header_text="$(cat "$header")";items=();default_id="";while IFS=$'\t' read -r id model st sz rt cx cat desc backend display;do [[ -n "$id" ]]||continue;items+=( "$id" "$display" );[[ -n "$selected_model" && "$model" == "$selected_model" ]]&&default_id="$id";done < "$data";[[ -n "$default_id" ]]||default_id=000001
    items+=( "__STOP_ALL__" "< Stop All Ollama Models >" )
    result="$(tui_model_dialog_capture "$rc" --title "Local Models" --default-item "$default_id" --no-tags --no-hot-list --scrollbar --cr-wrap --ok-label "Options" --cancel-label "Sort" --extra-button --extra-label "Details" --help-button --help-label "Back" --help-tags --hline "Up/Down Navigate   Enter Options   F1 Details   F2 Sort   Esc Back" --menu "$header_text" "$dialog_height" "$dialog_width" "$menu_height" "${items[@]}")";status="${result%%|*}";output="${result#*|}"
    case "$status" in
      0)id="$output";if [[ "$id" == __STOP_ALL__ ]];then tui_confirm "Stop all models" "Stop every Ollama model?"&&tui_run_captured "Stop all models" stop_all_models;refresh_needed=1;continue;fi;row="$(tui_local_combined_row_by_id "$data" "$id")";if [[ -n "$row" ]];then selected_model="${row%%$'\t'*}";if tui_local_model_options "$row";then action_status=0;else action_status=$?;fi;refresh_needed=1;fi;;
      3)id="$output";[[ "$id" == __STOP_ALL__ ]]&&continue;row="$(tui_local_combined_row_by_id "$data" "$id")";[[ -z "$row" ]]||tui_show_model_details "$row";;
      1)if sort_result="$(tui_model_sort_menu "$order")";then order="$sort_result";sorted_rows="$(mktemp -t ai-local-sorted.XXXXXX)";sort_model_rows "$rows" "$sorted_rows" "$order" per-field&&mv "$sorted_rows" "$rows"||rm -f "$sorted_rows";layout_needed=1;fi;;
      2|255|-1)rm -f "$rows" "$data" "$header" "$rc";return 0;;
    esac
  done
}


tui_draw_things_models_view() {
  local order="rating:desc|size:asc|model:asc|category:asc" selected_model="" rows data header rc result status output id row sort_result sorted_rows
  local hw os arch chip device ram_gb screen_cols screen_rows dialog_width dialog_height menu_height content_width default_id header_text refresh_needed=1 layout_needed=1 last_content_width=0 model description model_name
  local -a items
  ensure_draw_things_cli >/dev/null
  rc="$(tui_model_dialog_rc)";rows="$(mktemp -t ai-dt-tui-rows.XXXXXX)";data="$(mktemp -t ai-dt-tui-data.XXXXXX)";header="$(mktemp -t ai-dt-tui-header.XXXXXX)"
  while true;do
    screen_cols="$(terminal_columns)";screen_rows="$(terminal_lines)";dialog_width=$((screen_cols-4));dialog_height=$((screen_rows-4));((dialog_width>=72))||dialog_width=72;((dialog_height>=16))||dialog_height=16;menu_height=$((dialog_height-8));((menu_height>=6))||menu_height=6;content_width=$((dialog_width-10))
    if ((refresh_needed==1));then tui_dialog --title "Install Draw Things Models" --infobox "Loading Draw Things online catalog..." 5 66||true;:>"$rows";collect_draw_things_model_rows "$rows" "$order" per-field 1;if [[ ! -s "$rows" ]];then rm -f "$rows" "$data" "$header" "$rc";tui_show_message "Install Draw Things Models" "No installable Draw Things models could be loaded.";return 0;fi;refresh_needed=0;layout_needed=1;fi
    if ((layout_needed==1||last_content_width!=content_width));then :>"$data";:>"$header";tui_prepare_experimental_model_menu_data "$rows" "$data" "$header" "$content_width";last_content_width=$content_width;layout_needed=0;fi
    header_text="$(cat "$header")";items=();default_id="";while IFS=$'\t' read -r id model st sz rt cx cat desc display;do [[ -n "$id" ]]||continue;items+=( "$id" "$display" );[[ -n "$selected_model"&&"$model"=="$selected_model" ]]&&default_id="$id";done < "$data";[[ -n "$default_id" ]]||default_id=000001
    result="$(tui_model_dialog_capture "$rc" --title "Install Draw Things Models" --default-item "$default_id" --no-tags --no-hot-list --scrollbar --cr-wrap --ok-label "Install" --cancel-label "Sort" --extra-button --extra-label "Details" --help-button --help-label "Back" --help-tags --hline "Up/Down Navigate   Enter Install   F1 Details   F2 Sort   Esc Back" --menu "$header_text" "$dialog_height" "$dialog_width" "$menu_height" "${items[@]}")";status="${result%%|*}";output="${result#*|}"
    case "$status" in
      0)id="$output";row="$(tui_model_row_by_id "$data" "$id")";if [[ -n "$row" ]];then selected_model="${row%%$'\t'*}";description="$(printf '%s' "$row"|awk -F'\t' '{print $7}')";model_name="${description%% \[*}";if tui_confirm "Install Draw Things model" "Install $model_name?\n\nModel file: $selected_model";then tui_run_terminal "Install Draw Things model" install_draw_things_model "$selected_model" "$model_name";refresh_needed=1;fi;fi;;
      3)id="$output";row="$(tui_model_row_by_id "$data" "$id")";[[ -z "$row" ]]||tui_show_experimental_model_details "$row";;
      1)if sort_result="$(tui_model_sort_menu "$order")";then order="$sort_result";sorted_rows="$(mktemp -t ai-dt-sorted.XXXXXX)";sort_model_rows "$rows" "$sorted_rows" "$order" per-field&&mv "$sorted_rows" "$rows"||rm -f "$sorted_rows";layout_needed=1;fi;;
      2|255|-1)rm -f "$rows" "$data" "$header" "$rc";return 0;;
    esac
  done
}


tui_install_from_source_view() {
  local prompt="Select a backend and then provide a source URL or local file:" backend_choice backend source source_location artifact_choice artifact_type
  if ! backend_choice="$(tui_capture_dialog --title "Install from Source" --cancel-label "Back" --menu "Choose backend:" 0 0 10 "Ollama" "Hugging Face repository or direct GGUF" "Draw Things" "Download or import a checkpoint/safetensors/LoRA source")"; then return 0; fi
  backend="$(printf '%s' "$backend_choice" | tr "[:upper:]" "[:lower:]" | tr " " "-")"
  if [[ "$backend" == "draw-things" ]]; then
    if ! artifact_choice="$(tui_capture_dialog --title "Install from Source" --cancel-label "Back" --menu "Choose Draw Things artifact type:" 0 0 12 "Auto" "Try to detect whether the source is a model or a LoRA" "Model" "Import a full checkpoint / base model" "LoRA" "Import a LoRA adapter")"; then return 0; fi
    artifact_type="$(printf '%s' "$artifact_choice" | tr '[:upper:]' '[:lower:]')"
  else
    artifact_type="model"
  fi
  if ! source_location="$(tui_capture_dialog --title "Install from Source" --cancel-label "Back" --menu "Choose source type:" 0 0 10 "URL" "Download from an HTTP(S) source" "File" "Import from a local file")"; then return 0; fi
  if [[ "$backend" == "draw-things" ]]; then
    case "$artifact_type" in
      lora) prompt="Enter a source URL for Draw Things LoRA (.ckpt or .safetensors):" ;;
      model) prompt="Enter a source URL for a Draw Things model (.ckpt or .safetensors):" ;;
      *) prompt="Enter a source URL for Draw Things (.ckpt or .safetensors):" ;;
    esac
  else
    prompt="Enter a source URL for Ollama (Hugging Face repo or .gguf URL):"
  fi
  if [[ "$source_location" == "File" ]]; then
    if ! source="$(tui_file_prompt "$HOME/" "Select Source File")"; then return 0; fi
  else
    if ! source="$(tui_capture_dialog --title "Install from Source" --cancel-label "Back" --ok-label "Install" --inputbox "$prompt" 11 88 "")"; then return 0; fi
  fi
  [[ -n "$source" ]] || { tui_show_message "Install from Source" "Source cannot be empty."; return 0; }
  tui_run_terminal "Install from Source" install_model_from_source "$source" "$backend" "$artifact_type"
}


tui_models_menu() {
  local choice
  while true;do
    if ! choice="$(tui_capture_dialog --title "Models Menu" --cancel-label "Back" --menu "Choose a model catalog:" 0 0 14 "Local Models" "Installed Ollama and Draw Things models" "Install Ollama Models" "Browse Ollama Library" "Ollama Experimental Models" "Browse experimental Ollama models" "Install Draw Things Models" "Browse Draw Things online catalog" "Install from Source" "Install a model from a source URL or file")";then return 0;fi
    case "$choice" in "Local Models")tui_local_models_view;; "Install Ollama Models")tui_install_models_view;; "Ollama Experimental Models")tui_experimental_models_view;; "Install Draw Things Models")tui_draw_things_models_view;; "Install from Source")tui_install_from_source_view;; esac
  done
}


main() {
  if [[ $# -eq 0 ]]; then tui_main; exit 0; fi
  local action="$1"; shift
  case "$action" in
    --help) require_no_extra_args "$@"; usage ;;
    --setup) require_no_extra_args "$@"; setup_all ;;
    --tools) require_no_extra_args "$@"; show_tools ;;
    --tool)
      [[ $# -ge 2 ]] || die "Usage: ai --tool [TOOL] --enable|-e|--disable|-d"; local tool_target="$1" tool_action="$2" tool_state=""; shift 2; require_no_extra_args "$@"; case "$tool_action" in --enable|-e)tool_state=enabled;; --disable|-d)tool_state=disabled;; *)die "Unknown tool action: $tool_action";; esac; tool_target="$(normalize_tool_name "$tool_target")"||die "Unknown tool: $tool_target";tool_set_state "$tool_target" "$tool_state";success "Tool $tool_target: $tool_state" ;;
    --list)
      local list_target=local list_order=model list_direction=auto list_direction_seen=""
      if [[ $# -gt 0 && "$1" != --* ]]; then list_target="$1";shift;fi
      while [[ $# -gt 0 ]];do case "$1" in --order|-o)[[ $# -ge 2 ]]||die "$1 requires a value.";list_order="$2";shift 2;; --asc)[[ "$list_direction_seen" != desc ]]||die "--asc and --desc cannot be combined.";list_direction=asc;list_direction_seen=asc;shift;; --desc)[[ "$list_direction_seen" != asc ]]||die "--asc and --desc cannot be combined.";list_direction=desc;list_direction_seen=desc;shift;; --*)die "Unknown option for --list: $1";; *)die "Unexpected argument for --list: $1";; esac;done
      case "$list_target" in local|ollama|ollama-experimental|draw-things);; *)die "Unknown list target: $list_target. Expected: local, ollama, ollama-experimental, or draw-things.";; esac; list_models_by_target "$list_target" "$list_order" "$list_direction" ;;
    --install)
      [[ $# -ge 1 ]]||die "Usage: ai --install MODEL [--backend ollama|draw-things] | ai --install --source URL [--backend ollama|draw-things] [--type auto|model|lora]";local install_target="" install_source="" install_backend=auto install_source_type=auto
      while [[ $# -gt 0 ]];do case "$1" in --source|-s)[[ $# -ge 2 ]]||die "$1 requires URL";install_source="$2";shift 2;; --backend|-b)[[ $# -ge 2 ]]||die "$1 requires backend";install_backend="$2";shift 2;; --type|-t)[[ $# -ge 2 ]]||die "$1 requires type";install_source_type="$2";shift 2;; --*)die "Unknown option for --install: $1";; *)[[ -z "$install_target" ]]||die "More than one model provided.";install_target="$1";shift;; esac;done
      if [[ -n "$install_source"&&-n "$install_target" ]];then die "Use either MODEL or --source.";elif [[ -n "$install_source" ]];then install_model_from_source "$install_source" "$install_backend" "$install_source_type";elif [[ -n "$install_target" ]];then [[ "$install_source_type" == auto ]]||die "--type can only be used together with --source."; install_named_model "$install_target" "$install_backend";else die "Missing model/source.";fi ;;
    --uninstall) [[ $# -ge 1 ]]||die "Usage: ai --uninstall MODEL";local uninstall_target="$1";shift;require_no_extra_args "$@";uninstall_named_model "$uninstall_target" ;;
    --set-base) [[ $# -ge 1 ]]||die "Usage: ai --set-base MODEL";local base_target="$1";shift;require_no_extra_args "$@";set_base_model "$base_target" ;;
    --image)
      local image_model="" image_width=800 image_height=600 image_output_dir="$PWD" image_file_name="" image_prompt=""
      while [[ $# -gt 0 ]];do case "$1" in --width|-w)[[ $# -ge 2 ]]||die "$1 requires width";image_width="$2";shift 2;; --height|-h)[[ $# -ge 2 ]]||die "$1 requires height";image_height="$2";shift 2;; --output-dir|-o)[[ $# -ge 2 ]]||die "$1 requires directory";image_output_dir="$2";shift 2;; --file-name|-n)[[ $# -ge 2 ]]||die "$1 requires name";image_file_name="$2";shift 2;; --prompt|-p)[[ $# -ge 2 ]]||die "$1 requires prompt";image_prompt="$2";shift 2;; --*)die "Unknown option for --image: $1";; *)[[ -z "$image_model" ]]||die "More than one image model provided.";image_model="$1";shift;; esac;done;[[ -n "$image_prompt" ]]||die "--image requires --prompt/-p.";generate_image "$image_model" "$image_width" "$image_height" "$image_output_dir" "$image_file_name" "$image_prompt" ;;
    --run)
      local run_target="" context_raw="";while [[ $# -gt 0 ]];do case "$1" in --context-length|-l)[[ $# -ge 2 ]]||die "$1 requires value";context_raw="$2";shift 2;; --*)die "Unknown option for --run: $1";; *)[[ -z "$run_target" ]]||die "More than one model provided.";run_target="$1";shift;; esac;done;run_target="$(resolve_model_or_base "$run_target")";run_model "$run_target" "$context_raw" ;;
    --chat)
      local chat_target="" context_raw="";while [[ $# -gt 0 ]];do case "$1" in --context-length|-l)[[ $# -ge 2 ]]||die "$1 requires value";context_raw="$2";shift 2;; --*)die "Unknown option for --chat: $1";; *)[[ -z "$chat_target" ]]||die "More than one model provided.";chat_target="$1";shift;; esac;done;chat_target="$(resolve_model_or_base "$chat_target")";chat_model "$chat_target" "$context_raw" ;;
    --agent)
      local agent_target="" agent_directory="" context_raw="" exec_mode=auto exec_mode_set=0;while [[ $# -gt 0 ]];do case "$1" in --directory|-d)[[ $# -ge 2 ]]||die "$1 requires directory";agent_directory="$2";shift 2;; --context-length|-l)[[ $# -ge 2 ]]||die "$1 requires value";context_raw="$2";shift 2;; --exec)[[ $# -ge 2 ]]||die "--exec requires mode";((exec_mode_set==0))||die "--exec repeated";exec_mode="$(validate_exec_mode "$2")";exec_mode_set=1;shift 2;; --*)die "Unknown option for --agent: $1";; *)[[ -z "$agent_target" ]]||die "More than one model provided.";agent_target="$1";shift;; esac;done;agent_target="$(resolve_model_or_base "$agent_target")";agent_model "$agent_target" "$agent_directory" "$context_raw" "$exec_mode" ;;
    --stop) local stop_target="${1:-}";[[ $# -eq 0 ]]||shift;require_no_extra_args "$@";stop_target="$(resolve_model_or_base "$stop_target")";stop_model "$stop_target" ;;
    --stop-all) require_no_extra_args "$@";stop_all_models ;;
    --purge) purge_component "$@" ;;
    --version) require_no_extra_args "$@";show_versions ;;
    *) die "Unknown command: $action. Run: ai --help" ;;
  esac
}


# -----------------------------------------------------------------------------
# 1.10.0 overrides: repeated input files + persistent TUI state
# -----------------------------------------------------------------------------

STATE_FILE="$CONFIG_DIR/state.conf"

state_get() {
  local key="$1" default_value="${2:-}" value
  if [[ -f "$STATE_FILE" ]]; then
    if value="$(LC_ALL=C awk -v k="$key" '
      index($0, k "=") == 1 { print substr($0, length(k) + 2); found=1; exit }
      END { if (!found) exit 1 }
    ' "$STATE_FILE" 2>/dev/null)"; then
      printf '%s\n' "$value"
      return 0
    fi
  fi
  printf '%s\n' "$default_value"
}

state_set() {
  local key="$1" value="$2" tmp
  mkdir -p "$CONFIG_DIR"
  tmp="$(mktemp -t ai-state.XXXXXX)"
  if [[ -f "$STATE_FILE" ]]; then
    LC_ALL=C awk -v k="$key" 'index($0, k "=") != 1 { print }' "$STATE_FILE" > "$tmp"
  else
    : > "$tmp"
  fi
  printf '%s=%s\n' "$key" "$value" >> "$tmp"
  mv "$tmp" "$STATE_FILE"
  chmod 600 "$STATE_FILE" 2>/dev/null || true
}

normalize_input_file_path() {
  local input="$1" dir base
  [[ -n "$input" ]] || die "--input-file/-i requires a file path."
  if [[ "$input" == "~" ]]; then
    input="$HOME"
  elif [[ "$input" == "~/"* ]]; then
    input="$HOME/${input#~/}"
  fi
  [[ -f "$input" ]] || die "Input file does not exist or is not a regular file: $input"
  [[ -r "$input" ]] || die "Input file is not readable: $input"
  dir="${input%/*}"
  base="${input##*/}"
  if [[ "$dir" == "$input" ]]; then dir="."; fi
  [[ -n "$dir" ]] || dir="/"
  dir="$(cd "$dir" 2>/dev/null && pwd -P)" || die "Could not access input file directory: $dir"
  printf '%s/%s\n' "$dir" "$base"
}

input_blob_append() {
  local blob="$1" path="$2" line
  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    [[ "$line" != "$path" ]] || { printf '%s\n' "$blob"; return 0; }
  done <<< "$blob"
  if [[ -n "$blob" ]]; then
    printf '%s\n%s\n' "$blob" "$path"
  else
    printf '%s\n' "$path"
  fi
}

input_blob_count() {
  local blob="$1"
  [[ -n "$blob" ]] || { printf '0\n'; return 0; }
  printf '%s\n' "$blob" | awk 'NF{n++} END{print n+0}'
}

is_image_input_file() {
  local lower
  lower="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$lower" in
    *.png|*.jpg|*.jpeg|*.webp|*.bmp|*.tif|*.tiff|*.heic|*.heif) return 0 ;;
    *) return 1 ;;
  esac
}

model_supports_vision() {
  model_has_capability "$1" vision
}

validate_image_strength() {
  local value="$1"
  [[ "$value" =~ ^([0-9]+([.][0-9]*)?|[.][0-9]+)$ ]] || die "Invalid image strength: $value. Expected a number from 0 to 1."
  LC_NUMERIC=C awk -v n="$value" 'BEGIN{exit !(n>=0 && n<=1)}' || die "Invalid image strength: $value. Expected a number from 0 to 1."
  printf '%s\n' "$value"
}

context_value_valid() {
  ( parse_context_length "$1" >/dev/null 2>&1 )
}

state_image_dimension() {
  local key="$1" fallback="$2" value
  value="$(state_get "$key" "$fallback")"
  if [[ "$value" =~ ^[0-9]+$ ]] && (( value >= 64 && value <= 8192 )); then
    printf '%s\n' "$value"
  else
    printf '%s\n' "$fallback"
  fi
}

input_list_summary() {
  local file="$1" count
  count="$(awk 'NF{n++} END{print n+0}' "$file" 2>/dev/null || printf 0)"
  if (( count == 0 )); then printf 'None\n'; elif (( count == 1 )); then printf '1 selected\n'; else printf '%s selected\n' "$count"; fi
}

tui_file_prompt() {
  local start="${1:-$PWD}" title="${2:-Select File}" current result status selected tag kind path name parent
  local map dirs files count display
  local -a items

  if [[ -f "$start" ]]; then
    current="${start%/*}"
    [[ -n "$current" ]] || current="/"
  elif [[ -d "$start" ]]; then
    current="${start%/}"
    [[ -n "$current" ]] || current="/"
  else
    current="$PWD"
  fi

  while true; do
    map="$(mktemp -t ai-file-browser-map.XXXXXX)"
    dirs="$(mktemp -t ai-file-browser-dirs.XXXXXX)"
    files="$(mktemp -t ai-file-browser-files.XXXXXX)"
    : > "$map"; : > "$dirs"; : > "$files"

    parent="${current%/*}"
    if [[ "$current" == "/" ]]; then parent="/"; elif [[ -z "$parent" ]]; then parent="/"; fi
    printf '000000	dir	%s
' "$parent" >> "$map"

    while IFS= read -r name; do
      [[ -n "$name" ]] || continue
      path="$current/$name"
      [[ "$current" == "/" ]] && path="/$name"
      if [[ -d "$path" ]]; then
        printf '%s
' "$name" >> "$dirs"
      else
        printf '%s
' "$name" >> "$files"
      fi
    done < <(LC_ALL=C command ls -A1 "$current" 2>/dev/null || true)

    items=( "000000" "[DIR]  .." )
    count=0
    while IFS= read -r name; do
      [[ -n "$name" ]] || continue
      count=$((count + 1)); tag="D$(printf '%06d' "$count")"
      path="$current/$name"; [[ "$current" == "/" ]] && path="/$name"
      printf '%s	dir	%s
' "$tag" "$path" >> "$map"
      display="[DIR]  $name/"
      items+=( "$tag" "$display" )
    done < "$dirs"

    count=0
    while IFS= read -r name; do
      [[ -n "$name" ]] || continue
      count=$((count + 1)); tag="F$(printf '%06d' "$count")"
      path="$current/$name"; [[ "$current" == "/" ]] && path="/$name"
      printf '%s	file	%s
' "$tag" "$path" >> "$map"
      display="[FILE] $name"
      items+=( "$tag" "$display" )
    done < "$files"

    result="$(tui_dialog_capture_status       --title "$title"       --ok-label "Open" --cancel-label "Back"       --extra-button --extra-label "Select"       --no-tags --no-hot-list --scrollbar       --hline "Enter: open folder / select file"       --menu "Directory: $current" 22 100 14 "${items[@]}")"
    status="${result%%|*}"; selected="${result#*|}"
    kind="$(awk -F '	' -v id="$selected" '$1==id{print $2;exit}' "$map")"
    path="$(awk -F '	' -v id="$selected" '$1==id{print $3;exit}' "$map")"
    rm -f "$map" "$dirs" "$files"

    case "$status" in
      0)
        # Enter is the default action. Open directories; select files.
        if [[ "$kind" == "dir" && -d "$path" ]]; then
          current="$path"
          continue
        fi
        if [[ "$kind" == "file" && -f "$path" ]]; then
          printf '%s
' "$path"
          return 0
        fi
        ;;
      3)
        # The explicit Select button accepts files only.
        if [[ "$kind" == "file" && -f "$path" ]]; then
          printf '%s
' "$path"
          return 0
        fi
        if [[ "$kind" == "dir" ]]; then
          tui_show_message "$title" "Select is only for files. Use Open or press Enter to enter the highlighted directory."
          continue
        fi
        ;;
      1|255|-1) return 1 ;;
    esac
  done
}
tui_input_files_editor() {
  local list_file="$1" mode="${2:-any}" title="${3:-Input Files}"
  local result status selected tag path start="$PWD" tmp count=0 display
  local -a items
  while true; do
    items=(); count=0
    while IFS= read -r path; do
      [[ -n "$path" ]] || continue
      count=$((count + 1)); tag="$(printf '%06d' "$count")"
      display="$path"
      items+=( "$tag" "$display" )
      start="${path%/*}"
    done < "$list_file"
    if (( count == 0 )); then items=( "__EMPTY__" "(no input files selected)" ); fi

    result="$(tui_dialog_capture_status \
      --title "$title" --no-tags --no-hot-list --scrollbar \
      --ok-label "Add" --cancel-label "Back" \
      --extra-button --extra-label "Remove" \
      --help-button --help-label "Clear" --help-tags \
      --hline "Up/Down Navigate   Add File   Remove Selected   Clear All   Esc Back" \
      --menu "Selected input files:" 0 0 12 "${items[@]}")"
    status="${result%%|*}"; selected="${result#*|}"
    case "$status" in
      0)
        if path="$(tui_file_prompt "$start" "Add Input File")"; then
          if [[ "$mode" == "image" ]] && ! is_image_input_file "$path"; then
            tui_show_message "$title" "Image Generation accepts image input files only."
            continue
          fi
          path="$(normalize_input_file_path "$path")"
          if grep -Fqx "$path" "$list_file" 2>/dev/null; then
            tui_show_message "$title" "This file is already selected."
          else
            printf '%s\n' "$path" >> "$list_file"
          fi
        fi
        ;;
      3)
        [[ "$selected" != "__EMPTY__" && -n "$selected" ]] || continue
        tmp="$(mktemp -t ai-input-list.XXXXXX)"
        LC_ALL=C awk -v n="$selected" 'NR != (n+0) { print }' "$list_file" > "$tmp"
        mv "$tmp" "$list_file"
        ;;
      2)
        : > "$list_file"
        ;;
      1|255|-1)
        return 0
        ;;
    esac
  done
}

# Auto-compose multiple init images when ImageMagick is already installed.
# This remains optional; without ImageMagick Draw Things receives the first image.
PREPARED_IMAGE_INPUT=""
PREPARED_IMAGE_TEMP_DIR=""
prepare_draw_things_input_image() {
  local blob="$1" path count=0 cols=2 output status=1
  local -a images
  images=()
  PREPARED_IMAGE_INPUT=""; PREPARED_IMAGE_TEMP_DIR=""
  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    is_image_input_file "$path" || die "Image Generation input must be an image: $path"
    images+=( "$path" ); count=$((count + 1))
  done <<< "$blob"
  (( count > 0 )) || return 0
  PREPARED_IMAGE_INPUT="${images[0]}"
  (( count > 1 )) || return 0

  if command -v magick >/dev/null 2>&1 || command -v montage >/dev/null 2>&1; then
    PREPARED_IMAGE_TEMP_DIR="$(mktemp -d -t ai-image-compose.XXXXXX)"
    output="$PREPARED_IMAGE_TEMP_DIR/composite.png"
    if (( count > 4 )); then cols=3; fi
    if (( count > 9 )); then cols=4; fi
    set +e
    if command -v magick >/dev/null 2>&1; then
      magick montage "${images[@]}" -auto-orient -thumbnail '1024x1024>' -geometry +8+8 -tile "${cols}x" "$output" >/dev/null 2>&1
      status=$?
    else
      montage "${images[@]}" -auto-orient -thumbnail '1024x1024>' -geometry +8+8 -tile "${cols}x" "$output" >/dev/null 2>&1
      status=$?
    fi
    set -e
    if (( status == 0 )) && [[ -s "$output" ]]; then
      PREPARED_IMAGE_INPUT="$output"
      info "Auto-composed $count input images for Draw Things."
      return 0
    fi
    rm -rf "$PREPARED_IMAGE_TEMP_DIR"; PREPARED_IMAGE_TEMP_DIR=""
  fi
  warn "Multiple input images were provided, but ImageMagick is not available (or composition failed). Draw Things will use the first image only."
}

generate_image_ollama() {
  local model="$1" width="$2" height="$3" output_dir="$4" file_name="$5" prompt="$6" input_blob="${7:-}" strength="${8:-}"
  local escaped_model escaped_prompt payload response b64 http_code error output_path
  [[ -z "$input_blob" ]] || die "The Ollama image-generation backend does not currently accept --input-file. Use a Draw Things model for img2img/reference images."
  [[ -z "$strength" ]] || die "--strength is available for Draw Things img2img only."
  ensure_ollama_cli; ensure_ollama_api; require_cmd curl; require_cmd base64
  [[ -n "$model" ]] || model="$(default_image_model 2>/dev/null || true)"
  [[ -n "$model" ]] || die "No installed Ollama image-generation model was found."
  model_is_installed "$model" || die "Image model is not installed: $model"
  model_supports_image_generation "$model" || die "Model $model does not advertise Ollama image-generation capability."
  width="$(validate_image_dimension width "$width")"; height="$(validate_image_dimension height "$height")"; [[ -n "$prompt" ]] || die "--prompt/-p is required."
  [[ -n "$output_dir" ]] || output_dir="$PWD"; [[ "$output_dir" != '~' ]] || output_dir="$HOME"; [[ "$output_dir" != '~/'* ]] || output_dir="$HOME/${output_dir#~/}"
  mkdir -p "$output_dir"; output_dir="$(cd "$output_dir" && pwd -P)"; file_name="$(normalize_image_file_name "$file_name")"; output_path="$output_dir/$file_name"
  payload="$(mktemp -t ai-image-payload.XXXXXX)"; response="$(mktemp -t ai-image-response.XXXXXX)"; b64="$(mktemp -t ai-image-base64.XXXXXX)"
  escaped_model="$(printf '%s' "$model" | json_escape_stdin)"; escaped_prompt="$(printf '%s' "$prompt" | json_escape_stdin)"
  printf '{"model":"%s","prompt":"%s","width":%s,"height":%s,"stream":false}\n' "$escaped_model" "$escaped_prompt" "$width" "$height" > "$payload"
  info "Generating image with $model (${width}x${height}) via Ollama..."
  http_code="$(curl -sS -o "$response" -w '%{http_code}' -H 'Content-Type: application/json' --data-binary "@$payload" "$OLLAMA_URL/api/generate" 2>/dev/null || printf 000)"
  case "$http_code" in 2??) ;; *) error="$(tr '\n\r' '  ' < "$response" | sed -n 's/.*"error"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"; rm -f "$payload" "$response" "$b64"; die "Image generation failed (HTTP $http_code)${error:+: $error}" ;; esac
  extract_image_base64 "$response" "$b64" || { rm -f "$payload" "$response" "$b64"; die "Ollama did not return an image."; }
  base64_decode_to_file "$b64" "$output_path" || { rm -f "$payload" "$response" "$b64"; die "Could not decode Ollama image."; }
  rm -f "$payload" "$response" "$b64"; success "Image saved: $output_path"
}

generate_image_draw_things() {
  local model="$1" width="$2" height="$3" output_dir="$4" file_name="$5" prompt="$6" input_blob="${7:-}" strength="${8:-}"
  local cli dir output_path dtw dth status=0 input_image=""
  local -a args
  cli="$(ensure_draw_things_cli)"; dir="$(draw_things_models_dir)"
  width="$(validate_image_dimension width "$width")"; height="$(validate_image_dimension height "$height")"
  dtw=$((width / 64 * 64)); dth=$((height / 64 * 64)); (( dtw >= 64 )) || dtw=64; (( dth >= 64 )) || dth=64
  if (( dtw != width || dth != height )); then warn "Draw Things requires dimensions divisible by 64; using ${dtw}x${dth}."; fi
  [[ -n "$output_dir" ]] || output_dir="$PWD"; mkdir -p "$output_dir"; output_dir="$(cd "$output_dir" && pwd -P)"; file_name="$(normalize_image_file_name "$file_name")"; output_path="$output_dir/$file_name"
  if [[ -n "$input_blob" ]]; then
    [[ -n "$strength" ]] || strength="0.35"
    strength="$(validate_image_strength "$strength")"
    prepare_draw_things_input_image "$input_blob"
    input_image="$PREPARED_IMAGE_INPUT"
  elif [[ -n "$strength" ]]; then
    die "--strength requires at least one --input-file/-i image."
  fi
  args=( generate --models-dir "$dir" --model "$model" --prompt "$prompt" --width "$dtw" --height "$dth" --output "$output_path" )
  if [[ -n "$input_image" ]]; then args+=( --image "$input_image" --strength "$strength" ); fi
  info "Generating image with $model (${dtw}x${dth}) via Draw Things..."
  set +e
  "$cli" "${args[@]}"
  status=$?
  set -e
  [[ -z "$PREPARED_IMAGE_TEMP_DIR" ]] || rm -rf "$PREPARED_IMAGE_TEMP_DIR"
  PREPARED_IMAGE_TEMP_DIR=""; PREPARED_IMAGE_INPUT=""
  (( status == 0 )) || die "Draw Things image generation failed."
  [[ -s "$output_path" ]] || die "Draw Things finished without creating: $output_path"
  success "Image saved: $output_path"
}

generate_image() {
  local model="$1" width="$2" height="$3" output_dir="$4" file_name="$5" prompt="$6" input_blob="${7:-}" strength="${8:-}"
  [[ -n "$model" ]] || model="$(default_image_model 2>/dev/null || true)"
  [[ -n "$model" ]] || die "No installed image-generation model was found."
  if draw_things_model_installed "$model"; then
    generate_image_draw_things "$model" "$width" "$height" "$output_dir" "$file_name" "$prompt" "$input_blob" "$strength"
  else
    generate_image_ollama "$model" "$width" "$height" "$output_dir" "$file_name" "$prompt" "$input_blob" "$strength"
  fi
}

chat_model_with_inputs() {
  local model="$1" context_raw="${2:-}" input_blob="$3" context="" list_file node_script status=0
  ensure_ollama_cli; ensure_ollama_api
  model_is_installed "$model" || die "Model $model is not installed. Install it first with: ai --install $model"
  require_cmd node
  if [[ -n "$context_raw" ]]; then context="$(parse_context_length "$context_raw")"; fi
  local p has_images=0
  while IFS= read -r p; do [[ -n "$p" ]] || continue; is_image_input_file "$p" && has_images=1; done <<< "$input_blob"
  if (( has_images == 1 )) && ! model_supports_vision "$model"; then
    die "Model $model does not advertise Ollama's vision capability, but image input files were provided."
  fi
  list_file="$(mktemp -t ai-chat-inputs.XXXXXX)"; node_script="$(mktemp -t ai-chat-inputs.XXXXXX.js)"
  printf '%s\n' "$input_blob" > "$list_file"
  cat > "$node_script" <<'NODECHAT'
const fs = require('fs');
const http = require('http');
const https = require('https');
const readline = require('readline');
const cp = require('child_process');
const base = process.argv[2];
const model = process.argv[3];
const context = Number(process.argv[4] || 0);
const listFile = process.argv[5];
const files = fs.readFileSync(listFile, 'utf8').split(/\r?\n/).filter(Boolean);
const imageRe = /\.(png|jpe?g|webp|bmp|tiff?|heic|heif)$/i;
let images = [];
let chunks = [];
let used = 0;
const maxTotal = context > 0 ? Math.max(32768, Math.min(524288, context * 2)) : 131072;
for (const file of files) {
  try {
    if (imageRe.test(file)) {
      images.push(fs.readFileSync(file).toString('base64'));
      continue;
    }
    let text = '';
    if (/\.pdf$/i.test(file)) {
      const r = cp.spawnSync('pdftotext', ['-layout', file, '-'], {encoding: 'utf8'});
      if (r.status === 0 && r.stdout) text = r.stdout;
      else {
        console.error(`WARN PDF skipped (pdftotext unavailable or failed): ${file}`);
        continue;
      }
    } else {
      const b = fs.readFileSync(file);
      if (b.includes(0)) {
        console.error(`WARN Binary input skipped: ${file}`);
        continue;
      }
      text = b.toString('utf8');
    }
    const remaining = maxTotal - used;
    if (remaining <= 0) break;
    if (Buffer.byteLength(text, 'utf8') > remaining) {
      text = Buffer.from(text, 'utf8').subarray(0, remaining).toString('utf8');
      console.error(`WARN Input context truncated to fit a conservative context budget: ${file}`);
    }
    used += Buffer.byteLength(text, 'utf8');
    chunks.push(`--- FILE: ${file} ---\n${text}`);
  } catch (e) {
    console.error(`WARN Could not read input file ${file}: ${e.message}`);
  }
}
function postChat(messages) {
  return new Promise((resolve, reject) => {
    const u = new URL('/api/chat', base.endsWith('/') ? base : base + '/');
    const payload = {model, messages, stream: false};
    if (context > 0) payload.options = {num_ctx: context};
    const data = Buffer.from(JSON.stringify(payload));
    const lib = u.protocol === 'https:' ? https : http;
    const req = lib.request({hostname:u.hostname, port:u.port || (u.protocol==='https:'?443:80), path:u.pathname, method:'POST', headers:{'Content-Type':'application/json','Content-Length':data.length}}, res => {
      let body=''; res.setEncoding('utf8'); res.on('data', c => body += c); res.on('end', () => {
        if (res.statusCode < 200 || res.statusCode >= 300) return reject(new Error(`HTTP ${res.statusCode}: ${body}`));
        try { resolve(JSON.parse(body)); } catch(e) { reject(e); }
      });
    });
    req.on('error', reject); req.write(data); req.end();
  });
}
(async () => {
  const rl = readline.createInterface({input:process.stdin, output:process.stdout, terminal:true});
  let messages=[]; let first=true;
  console.log(`Input files ready: ${files.length}. Type /bye or press Ctrl+D to exit.`);
  rl.setPrompt('>>> '); rl.prompt();
  for await (const raw of rl) {
    const line = raw.trim();
    if (!line) { rl.prompt(); continue; }
    if (line === '/bye' || line === '/exit') break;
    let content = raw;
    if (first && chunks.length) content = `Use the following input files as context for this conversation.\n\n${chunks.join('\n\n')}\n\nUSER MESSAGE:\n${raw}`;
    const msg = {role:'user', content};
    if (first && images.length) msg.images = images;
    try {
      const response = await postChat(messages.concat([msg]));
      const answer = response && response.message && response.message.content ? response.message.content : '';
      console.log(answer);
      messages.push(msg, {role:'assistant', content:answer});
      first=false;
    } catch(e) {
      console.error(`ERR ${e.message}`);
    }
    rl.prompt();
  }
  rl.close();
})().catch(e => { console.error(`ERR ${e.message}`); process.exit(1); });
NODECHAT
  info "Opening chat with $model and $(input_blob_count "$input_blob") input file(s)..."
  set +e
  node "$node_script" "$OLLAMA_URL" "$model" "$context" "$list_file"
  status=$?
  set -e
  rm -f "$node_script" "$list_file"
  return "$status"
}

chat_model() {
  local model="$1" context_raw="${2:-}" input_blob="${3:-}"
  local context="" chat_model_name="$model" temp_model="" modelfile="" status=0
  if [[ -n "$input_blob" ]]; then chat_model_with_inputs "$model" "$context_raw" "$input_blob"; return $?; fi
  ensure_ollama_cli; ensure_ollama_api
  model_is_installed "$model" || die "Model $model is not installed. Install it first with: ai --install $model"
  if [[ -n "$context_raw" ]]; then
    context="$(parse_context_length "$context_raw")"; temp_model="ai-chat-session-$$-${RANDOM}"; modelfile="$(mktemp -t ai-chat-modelfile.XXXXXX)"
    cat > "$modelfile" <<EOF_CHAT_MODEL
FROM $model
PARAMETER num_ctx $context
EOF_CHAT_MODEL
    info "Preparing chat with $model (context: $context tokens)..."
    if ! ollama create "$temp_model" -f "$modelfile" >/dev/null; then rm -f "$modelfile"; die "Could not create the temporary chat profile."; fi
    rm -f "$modelfile"; chat_model_name="$temp_model"
  else
    info "Opening chat with $model (Ollama default context)..."
  fi
  printf '%b\n' "${DIM}Type /bye or press Ctrl+D to exit.${RESET}"
  set +e; ollama run "$chat_model_name"; status=$?; set -e
  if [[ -n "$temp_model" ]]; then info "Removing temporary chat profile..."; ollama stop "$temp_model" >/dev/null 2>&1 || true; ollama rm "$temp_model" >/dev/null 2>&1 || warn "Could not remove temporary model profile: $temp_model"; fi
  return "$status"
}

codex_supports_image_flag() {
  codex --help 2>/dev/null | grep -Eq '(^|[[:space:]])(-i,?[[:space:]]*)?--image([=[:space:]]|$)'
}

agent_model() {
  local model="$1" directory="${2:-}" context_raw="${3:-}" exec_mode="${4:-auto}" input_blob="${5:-}"
  local workspace="" temp_workspace="" sandbox_mode="read-only" started_by_agent=0 status=0 staging_dir="" initial_prompt="" path base dest rel index=0 codex_has_image_args=0 agent_has_images=0 agent_model_vision=0 codex_image_supported=0
  local -a codex_exec_args codex_tool_args codex_input_args
  codex_exec_args=(); codex_tool_args=(); codex_input_args=()
  ensure_ollama_cli; ensure_ollama_api; ensure_codex_cli; exec_mode="$(validate_exec_mode "$exec_mode")"
  model_is_installed "$model" || die "Model $model is not installed. Install it first with: ai --install $model"
  model_supports_tools "$model" || die "Model $model does not advertise Ollama's 'tools' capability and cannot be used as a Codex agent."

  if [[ -n "$directory" ]]; then
    [[ "$directory" != "~" ]] || directory="$HOME"; [[ "$directory" != "~/"* ]] || directory="$HOME/${directory#~/}"
    mkdir -p "$directory" || die "Could not create agent directory: $directory"; workspace="$(cd "$directory" && pwd -P)" || die "Could not access agent directory: $directory"; sandbox_mode="workspace-write"
    info "Codex workspace: $workspace"; info "Sandbox: workspace-write"
  else
    temp_workspace="$(mktemp -d -t ai-agent-workspace.XXXXXX)"; workspace="$temp_workspace"; sandbox_mode="read-only"
    info "No --directory was provided."; info "Codex will use an empty temporary read-only workspace: $workspace"
  fi

  if [[ -n "$input_blob" ]]; then
    while IFS= read -r path; do
      [[ -n "$path" ]] || continue
      if is_image_input_file "$path"; then agent_has_images=1; fi
    done <<< "$input_blob"
    if (( agent_has_images == 1 )); then
      if model_supports_vision "$model"; then agent_model_vision=1; fi
      if codex_supports_image_flag; then codex_image_supported=1; fi
    fi
    staging_dir="$workspace/.ai-input-$$"; mkdir -p "$staging_dir" || die "Could not create temporary input-file staging directory."
    initial_prompt="The user provided the following input files as bootstrap context. Inspect them before answering or acting:"
    while IFS= read -r path; do
      [[ -n "$path" ]] || continue; index=$((index + 1)); base="${path##*/}"; dest="$staging_dir/$(printf '%02d' "$index")_$base"
      cp -p "$path" "$dest" || { rm -rf "$staging_dir"; die "Could not stage input file: $path"; }
      rel="${dest#$workspace/}"; initial_prompt="${initial_prompt}"$'\n'"- $rel"
      if is_image_input_file "$dest" && (( agent_model_vision == 1 && codex_image_supported == 1 )); then
        codex_input_args+=( --image "$dest" ); codex_has_image_args=1
      fi
    done <<< "$input_blob"
    initial_prompt="${initial_prompt}"$'\n\n'"Treat these files as context supplied explicitly by the user."
    info "Input files staged: $index"
    if (( agent_has_images == 1 && agent_model_vision == 0 )); then warn "The selected model does not advertise vision; image files can only be useful through enabled tools or other file-processing steps."; fi
  fi

  if model_is_running "$model"; then info "Model is already running: $model"; [[ -z "$context_raw" ]] || warn "The model is already running, so --context-length will not change its current context."; else run_model "$model" "$context_raw"; started_by_agent=1; fi
  info "Starting Codex with local model: $model"; info "Codex provider: ollama (${OLLAMA_URL%/}/v1)"; info "Execution approvals: $exec_mode"; info "Tools: $(tools_enabled_summary)"

  case "$exec_mode" in
    ask) codex_exec_args=( --ask-for-approval on-request -c 'approvals_reviewer="user"' ) ;;
    auto) codex_exec_args=( --ask-for-approval on-request -c 'approvals_reviewer="auto_review"' ) ;;
    no-ask) codex_exec_args=( --ask-for-approval never -c 'approvals_reviewer="user"' ) ;;
  esac
  if tool_is_enabled shell; then codex_tool_args+=( -c 'features.shell_tool=true' ); else codex_tool_args+=( -c 'features.shell_tool=false' ); fi
  if tool_is_enabled view-image; then codex_tool_args+=( -c 'tools.view_image=true' ); else codex_tool_args+=( -c 'tools.view_image=false' ); fi
  if tool_is_enabled web-search; then codex_tool_args+=( -c 'web_search="live"' ); else codex_tool_args+=( -c 'web_search="disabled"' ); fi

  set +e
  (
    cd "$workspace" || exit 1
    if [[ -n "$initial_prompt" ]]; then
      if (( codex_has_image_args == 1 )); then
        CODEX_OSS_BASE_URL="${OLLAMA_URL%/}/v1" codex --oss --local-provider ollama -m "$model" --sandbox "$sandbox_mode" -C "$workspace" "${codex_input_args[@]}" "${codex_tool_args[@]}" "${codex_exec_args[@]}" "$initial_prompt"
      else
        CODEX_OSS_BASE_URL="${OLLAMA_URL%/}/v1" codex --oss --local-provider ollama -m "$model" --sandbox "$sandbox_mode" -C "$workspace" "${codex_tool_args[@]}" "${codex_exec_args[@]}" "$initial_prompt"
      fi
    else
      CODEX_OSS_BASE_URL="${OLLAMA_URL%/}/v1" codex --oss --local-provider ollama -m "$model" --sandbox "$sandbox_mode" -C "$workspace" "${codex_tool_args[@]}" "${codex_exec_args[@]}"
    fi
  )
  status=$?
  set -e
  [[ -z "$staging_dir" ]] || rm -rf "$staging_dir"
  [[ -z "$temp_workspace" ]] || rm -rf "$temp_workspace"
  if (( started_by_agent == 1 )); then info "The model was started by --agent; stopping it now..."; ollama stop "$model" >/dev/null 2>&1 || warn "Could not stop model: $model"; fi
  return "$status"
}

tui_image_view() {
  local explicit_model="${1:-}" model width height target_dir file_name prompt strength="0.35" input_file result status field value display_model display_dir display_inputs blob remembered
  local -a items
  input_file="$(mktemp -t ai-tui-image-inputs.XXXXXX)"; : > "$input_file"
  if [[ -n "$explicit_model" ]]; then model="$explicit_model"; state_set image_model "$model"; else model="$(state_get image_model '')"; fi
  if [[ -z "$model" ]] || { ! draw_things_model_installed "$model" && { ! model_is_installed "$model" || ! model_supports_image_generation "$model"; }; }; then model="$(default_image_model 2>/dev/null || true)"; fi
  width="$(state_image_dimension image_width 800)"; height="$(state_image_dimension image_height 600)"
  target_dir="$(state_get image_target_dir "$PWD")"; [[ -d "$target_dir" ]] || target_dir="$PWD"
  file_name="$(default_image_file_name)"
  while true; do
    display_model="${model:-Not selected}"; display_dir="$(tui_display_workspace "$target_dir")"; display_inputs="$(input_list_summary "$input_file")"
    items=(
      model "$(printf '%-22s [%s]' 'Model' "$display_model")"
      width "$(printf '%-22s [%s]' 'Width' "$width")"
      height "$(printf '%-22s [%s]' 'Height' "$height")"
      dir "$(printf '%-22s [%s]' 'Target Directory' "$display_dir")"
      file "$(printf '%-22s [%s]' 'File Name' "$file_name")"
      inputs "$(printf '%-22s [%s]' 'Input Files' "$display_inputs")"
      strength "$(printf '%-22s [%s]' 'Strength' "$strength")"
    )
    result="$(tui_dialog_capture_status --title 'Image Generation' --no-tags --no-hot-list --ok-label Edit --cancel-label Back --extra-button --extra-label Run --hline 'Up/Down Navigate   Enter Edit   Run Prompt/Generate   Esc Back' --menu '' 19 94 9 "${items[@]}")"
    status="${result%%|*}"; field="${result#*|}"
    case "$status" in
      0)
        case "$field" in
          model) if value="$(tui_select_image_model 'Image Model' "$model")"; then model="$value"; state_set image_model "$model"; fi ;;
          width) if value="$(tui_image_dimension_prompt Width "$width")"; then width="$value"; state_set image_width "$width"; fi ;;
          height) if value="$(tui_image_dimension_prompt Height "$height")"; then height="$value"; state_set image_height "$height"; fi ;;
          dir) if tui_directory_prompt "$target_dir" 'Target Directory'; then target_dir="$TUI_SELECTED_DIRECTORY"; state_set image_target_dir "$target_dir"; fi ;;
          file) if value="$(tui_capture_dialog --title 'File Name' --cancel-label Back --inputbox 'PNG file name. .png is added automatically when omitted.' 9 68 "$file_name")"; then [[ -z "$value" ]] || file_name="$value"; fi ;;
          inputs) tui_input_files_editor "$input_file" image 'Input Files' ;;
          strength) if value="$(tui_capture_dialog --title Strength --cancel-label Back --inputbox 'Draw Things img2img denoising strength (0..1).' 9 66 "$strength")"; then if [[ "$value" =~ ^([0-9]+([.][0-9]*)?|[.][0-9]+)$ ]] && LC_NUMERIC=C awk -v n="$value" 'BEGIN{exit !(n>=0 && n<=1)}'; then strength="$value"; else tui_show_message Strength 'Enter a value from 0 to 1.'; fi; fi ;;
        esac
        ;;
      3)
        if [[ -z "$model" ]]; then tui_show_message 'Image Generation' 'Select or install an image-generation model first.'; continue; fi
        if prompt="$(tui_image_prompt)"; then blob="$(cat "$input_file")"; tui_run_terminal "Image Generation: $model" generate_image "$model" "$width" "$height" "$target_dir" "$file_name" "$prompt" "$blob" "$([[ -n "$blob" ]] && printf '%s' "$strength")"; file_name="$(default_image_file_name)"; fi
        ;;
      1|255|-1) rm -f "$input_file"; return 0 ;;
    esac
  done
}

tui_chat_view() {
  local model="${1:-}" explicit_context="${2:-}" context result status field value display_model display_inputs input_file blob remembered
  local -a items
  input_file="$(mktemp -t ai-tui-chat-inputs.XXXXXX)"; : > "$input_file"
  [[ -n "$model" ]] || model="$(tui_default_installed_model)"
  if [[ -n "$explicit_context" ]]; then context="$explicit_context"; else context="$(state_get chat_context 16K)"; fi
  context_value_valid "$context" || context=16K
  while true; do
    display_model="${model:-Not selected}"; display_inputs="$(input_list_summary "$input_file")"
    items=( model "$(printf '%-22s [%s]' 'Model' "$display_model")" context "$(printf '%-22s [%s]' 'Context Length' "$context")" inputs "$(printf '%-22s [%s]' 'Input Files' "$display_inputs")" )
    result="$(tui_dialog_capture_status --title 'Chat Options' --no-tags --no-hot-list --ok-label Edit --cancel-label Back --extra-button --extra-label Run --hline 'Up/Down Navigate   Enter Edit   Run Start Chat   Esc Back' --menu '' 14 82 5 "${items[@]}")"
    status="${result%%|*}"; field="${result#*|}"
    case "$status" in
      0) case "$field" in model) if value="$(tui_select_installed_model 'Chat Model' "$model")"; then model="$value"; fi ;; context) if value="$(tui_context_length_prompt "$context")"; then context="$value"; state_set chat_context "$context"; fi ;; inputs) tui_input_files_editor "$input_file" any 'Input Files' ;; esac ;;
      3) if [[ -z "$model" ]]; then tui_show_message 'Chat Options' 'Select an installed model before starting Chat.'; continue; fi; blob="$(cat "$input_file")"; tui_run_terminal "Chat: $model" chat_model "$model" "$context" "$blob" ;;
      1|255|-1) rm -f "$input_file"; return 0 ;;
    esac
  done
}

tui_agent_view() {
  local model="${1:-}" explicit_context="${2:-}" explicit_workspace="${3:-}" explicit_approval="${4:-}" context workspace approval result status field value display_model display_workspace display_tools display_inputs workspace_start="$PWD" input_file blob
  local -a items
  input_file="$(mktemp -t ai-tui-agent-inputs.XXXXXX)"; : > "$input_file"
  [[ -n "$model" ]] || model="$(tui_default_installed_model)"
  if [[ -n "$explicit_context" ]]; then context="$explicit_context"; else context="$(state_get agent_context 16K)"; fi; context_value_valid "$context" || context=16K
  if [[ -n "$explicit_workspace" ]]; then workspace="$explicit_workspace"; else workspace="$(state_get agent_workspace '')"; fi
  if [[ -n "$explicit_approval" ]]; then approval="$explicit_approval"; else approval="$(state_get agent_approval ask)"; fi
  case "$approval" in ask|auto|no-ask) ;; *) approval=ask ;; esac
  while true; do
    display_model="${model:-Not selected}"; display_workspace="$(tui_display_workspace "$workspace")"; display_tools="$(tools_enabled_summary)"; display_inputs="$(input_list_summary "$input_file")"
    items=(
      model "$(printf '%-22s [%s]' 'Model' "$display_model")"
      context "$(printf '%-22s [%s]' 'Context Length' "$context")"
      workspace "$(printf '%-22s [%s]' 'Workspace' "$display_workspace")"
      approval "$(printf '%-22s [%s]' 'Execution Approvals' "$approval")"
      tools "$(printf '%-22s [%s]' 'Tools' "$display_tools")"
      inputs "$(printf '%-22s [%s]' 'Input Files' "$display_inputs")"
    )
    result="$(tui_dialog_capture_status --title 'Codex Options' --no-tags --no-hot-list --ok-label Edit --cancel-label Back --extra-button --extra-label Run --hline 'Up/Down Navigate   Enter Edit   Run Start Codex   Esc Back' --menu '' 18 88 8 "${items[@]}")"
    status="${result%%|*}"; field="${result#*|}"
    case "$status" in
      0)
        case "$field" in
          model) if value="$(tui_select_installed_model 'Agent Model' "$model")"; then model="$value"; fi ;;
          context) if value="$(tui_context_length_prompt "$context")"; then context="$value"; state_set agent_context "$context"; fi ;;
          workspace) if [[ -n "$workspace" ]]; then workspace_start="$workspace"; else workspace_start="$PWD"; fi; if tui_agent_workspace_prompt "$workspace_start"; then workspace="$TUI_AGENT_WORKSPACE"; state_set agent_workspace "$workspace"; fi ;;
          approval) if value="$(tui_exec_mode_prompt "$approval")"; then approval="$value"; state_set agent_approval "$approval"; fi ;;
          tools) tui_tools_checklist || true ;;
          inputs) tui_input_files_editor "$input_file" any 'Input Files' ;;
        esac
        ;;
      3) if [[ -z "$model" ]]; then tui_show_message 'Codex Options' 'Select an installed model before running Codex.'; continue; fi; blob="$(cat "$input_file")"; tui_run_terminal "Codex agent: $model" agent_model "$model" "$workspace" "$context" "$approval" "$blob" ;;
      1|255|-1) rm -f "$input_file"; return 0 ;;
    esac
  done
}

tui_agent_flow() { tui_agent_view "$1"; }

main() {
  if [[ $# -eq 0 ]]; then tui_main; exit 0; fi
  local action="$1"; shift
  case "$action" in
    --help) require_no_extra_args "$@"; usage ;;
    --setup) require_no_extra_args "$@"; setup_all ;;
    --tools) require_no_extra_args "$@"; show_tools ;;
    --tool)
      [[ $# -ge 2 ]] || die "Usage: ai --tool [TOOL] --enable|-e|--disable|-d"; local tool_target="$1" tool_action="$2" tool_state=""; shift 2; require_no_extra_args "$@"; case "$tool_action" in --enable|-e)tool_state=enabled;; --disable|-d)tool_state=disabled;; *)die "Unknown tool action: $tool_action";; esac; tool_target="$(normalize_tool_name "$tool_target")"||die "Unknown tool: $tool_target";tool_set_state "$tool_target" "$tool_state";success "Tool $tool_target: $tool_state" ;;
    --list)
      local list_target=local list_order=model list_direction=auto list_direction_seen=""
      if [[ $# -gt 0 && "$1" != --* ]]; then list_target="$1";shift;fi
      while [[ $# -gt 0 ]];do case "$1" in --order|-o)[[ $# -ge 2 ]]||die "$1 requires a value.";list_order="$2";shift 2;; --asc)[[ "$list_direction_seen" != desc ]]||die "--asc and --desc cannot be combined.";list_direction=asc;list_direction_seen=asc;shift;; --desc)[[ "$list_direction_seen" != asc ]]||die "--asc and --desc cannot be combined.";list_direction=desc;list_direction_seen=desc;shift;; --*)die "Unknown option for --list: $1";; *)die "Unexpected argument for --list: $1";; esac;done
      case "$list_target" in local|ollama|ollama-experimental|draw-things);; *)die "Unknown list target: $list_target. Expected: local, ollama, ollama-experimental, or draw-things.";; esac; list_models_by_target "$list_target" "$list_order" "$list_direction" ;;
    --install)
      [[ $# -ge 1 ]]||die "Usage: ai --install MODEL [--backend ollama|draw-things] | ai --install --source URL [--backend ollama|draw-things] [--type auto|model|lora]";local install_target="" install_source="" install_backend=auto install_source_type=auto
      while [[ $# -gt 0 ]];do case "$1" in --source|-s)[[ $# -ge 2 ]]||die "$1 requires URL";install_source="$2";shift 2;; --backend|-b)[[ $# -ge 2 ]]||die "$1 requires backend";install_backend="$2";shift 2;; --type|-t)[[ $# -ge 2 ]]||die "$1 requires type";install_source_type="$2";shift 2;; --*)die "Unknown option for --install: $1";; *)[[ -z "$install_target" ]]||die "More than one model provided.";install_target="$1";shift;; esac;done
      if [[ -n "$install_source"&&-n "$install_target" ]];then die "Use either MODEL or --source.";elif [[ -n "$install_source" ]];then install_model_from_source "$install_source" "$install_backend" "$install_source_type";elif [[ -n "$install_target" ]];then [[ "$install_source_type" == auto ]]||die "--type can only be used together with --source."; install_named_model "$install_target" "$install_backend";else die "Missing model/source.";fi ;;
    --uninstall) [[ $# -ge 1 ]]||die "Usage: ai --uninstall MODEL";local uninstall_target="$1";shift;require_no_extra_args "$@";uninstall_named_model "$uninstall_target" ;;
    --set-base) [[ $# -ge 1 ]]||die "Usage: ai --set-base MODEL";local base_target="$1";shift;require_no_extra_args "$@";set_base_model "$base_target" ;;
    --image)
      local image_model="" image_width=800 image_height=600 image_output_dir="$PWD" image_file_name="" image_prompt="" image_strength="" input_blob="" normalized="" explicit_model=0 explicit_width=0 explicit_height=0 explicit_dir=0
      while [[ $# -gt 0 ]];do
        case "$1" in
          --width|-w) [[ $# -ge 2 ]]||die "$1 requires width"; image_width="$2"; explicit_width=1; shift 2 ;;
          --height|-h) [[ $# -ge 2 ]]||die "$1 requires height"; image_height="$2"; explicit_height=1; shift 2 ;;
          --output-dir|-o) [[ $# -ge 2 ]]||die "$1 requires directory"; image_output_dir="$2"; explicit_dir=1; shift 2 ;;
          --file-name|-n) [[ $# -ge 2 ]]||die "$1 requires name"; image_file_name="$2"; shift 2 ;;
          --prompt|-p) [[ $# -ge 2 ]]||die "$1 requires prompt"; image_prompt="$2"; shift 2 ;;
          --input-file|-i) [[ $# -ge 2 ]]||die "$1 requires a file"; normalized="$(normalize_input_file_path "$2")"; is_image_input_file "$normalized" || die "Image Generation input must be an image: $normalized"; input_blob="$(input_blob_append "$input_blob" "$normalized")"; shift 2 ;;
          --strength) [[ $# -ge 2 ]]||die "$1 requires a value from 0 to 1"; image_strength="$2"; shift 2 ;;
          --*) die "Unknown option for --image: $1" ;;
          *) [[ -z "$image_model" ]]||die "More than one image model provided."; image_model="$1"; explicit_model=1; shift ;;
        esac
      done
      [[ -n "$image_prompt" ]]||die "--image requires --prompt/-p."
      (( explicit_model == 0 )) || state_set image_model "$image_model"; (( explicit_width == 0 )) || state_set image_width "$image_width"; (( explicit_height == 0 )) || state_set image_height "$image_height"; (( explicit_dir == 0 )) || state_set image_target_dir "$image_output_dir"
      generate_image "$image_model" "$image_width" "$image_height" "$image_output_dir" "$image_file_name" "$image_prompt" "$input_blob" "$image_strength"
      ;;
    --run)
      local run_target="" context_raw="";while [[ $# -gt 0 ]];do case "$1" in --context-length|-l)[[ $# -ge 2 ]]||die "$1 requires value";context_raw="$2";shift 2;; --*)die "Unknown option for --run: $1";; *)[[ -z "$run_target" ]]||die "More than one model provided.";run_target="$1";shift;; esac;done;run_target="$(resolve_model_or_base "$run_target")";run_model "$run_target" "$context_raw" ;;
    --chat)
      local chat_target="" context_raw="" input_blob="" normalized="" context_seen=0
      while [[ $# -gt 0 ]];do case "$1" in --context-length|-l)[[ $# -ge 2 ]]||die "$1 requires value";context_raw="$2";context_seen=1;shift 2;; --input-file|-i)[[ $# -ge 2 ]]||die "$1 requires a file";normalized="$(normalize_input_file_path "$2")";input_blob="$(input_blob_append "$input_blob" "$normalized")";shift 2;; --*)die "Unknown option for --chat: $1";; *)[[ -z "$chat_target" ]]||die "More than one model provided.";chat_target="$1";shift;; esac;done
      (( context_seen == 0 )) || state_set chat_context "$context_raw"; chat_target="$(resolve_model_or_base "$chat_target")";chat_model "$chat_target" "$context_raw" "$input_blob"
      ;;
    --agent)
      local agent_target="" agent_directory="" context_raw="" exec_mode=auto exec_mode_set=0 input_blob="" normalized="" directory_seen=0 context_seen=0
      while [[ $# -gt 0 ]];do case "$1" in --directory|-d)[[ $# -ge 2 ]]||die "$1 requires directory";agent_directory="$2";directory_seen=1;shift 2;; --context-length|-l)[[ $# -ge 2 ]]||die "$1 requires value";context_raw="$2";context_seen=1;shift 2;; --exec)[[ $# -ge 2 ]]||die "--exec requires mode";((exec_mode_set==0))||die "--exec repeated";exec_mode="$(validate_exec_mode "$2")";exec_mode_set=1;shift 2;; --input-file|-i)[[ $# -ge 2 ]]||die "$1 requires a file";normalized="$(normalize_input_file_path "$2")";input_blob="$(input_blob_append "$input_blob" "$normalized")";shift 2;; --*)die "Unknown option for --agent: $1";; *)[[ -z "$agent_target" ]]||die "More than one model provided.";agent_target="$1";shift;; esac;done
      (( context_seen == 0 )) || state_set agent_context "$context_raw"; (( directory_seen == 0 )) || state_set agent_workspace "$agent_directory"; (( exec_mode_set == 0 )) || state_set agent_approval "$exec_mode"
      agent_target="$(resolve_model_or_base "$agent_target")";agent_model "$agent_target" "$agent_directory" "$context_raw" "$exec_mode" "$input_blob"
      ;;
    --stop) local stop_target="${1:-}";[[ $# -eq 0 ]]||shift;require_no_extra_args "$@";stop_target="$(resolve_model_or_base "$stop_target")";stop_model "$stop_target" ;;
    --stop-all) require_no_extra_args "$@";stop_all_models ;;
    --purge) purge_component "$@" ;;
    --version) require_no_extra_args "$@";show_versions ;;
    *) die "Unknown command: $action. Run: ai --help" ;;
  esac
}


# -----------------------------------------------------------------------------
# 1.11.0 overrides: named Chat/Agent session files
# -----------------------------------------------------------------------------

normalize_session_file_path() {
  local input="$1" dir base
  [[ -n "$input" ]] || die "--session/-s requires a file path."
  if [[ "$input" == "~" ]]; then
    die "--session/-s must name a file, not only the home directory."
  elif [[ "$input" == "~/"* ]]; then
    input="$HOME/${input#~/}"
  fi
  case "$input" in
    /*) ;;
    *) input="$PWD/$input" ;;
  esac
  dir="${input%/*}"; base="${input##*/}"
  [[ -n "$base" ]] || die "--session/-s must name a file."
  [[ -n "$dir" ]] || dir="/"
  mkdir -p "$dir" || die "Could not create session directory: $dir"
  dir="$(cd "$dir" 2>/dev/null && pwd -P)" || die "Could not access session directory: $dir"
  printf '%s/%s\n' "$dir" "$base"
}

session_json_get() {
  local file="$1" key="$2"
  [[ -s "$file" ]] || return 1
  require_cmd node
  node - "$file" "$key" <<'NODE_SESSION_GET'
const fs=require('fs');
const file=process.argv[2], key=process.argv[3];
try {
  const obj=JSON.parse(fs.readFileSync(file,'utf8'));
  let v=obj[key];
  if (v === undefined || v === null || v === '') process.exit(1);
  if (typeof v === 'object') process.stdout.write(JSON.stringify(v));
  else process.stdout.write(String(v));
} catch (_) { process.exit(2); }
NODE_SESSION_GET
}

session_file_format() {
  session_json_get "$1" format 2>/dev/null || true
}

agent_session_merge() {
  local file="$1" thread_id="$2" model="$3" workspace="$4" context_raw="$5" exec_mode="$6"
  require_cmd node
  node - "$file" "$thread_id" "$model" "$workspace" "$context_raw" "$exec_mode" <<'NODE_AGENT_SESSION'
const fs=require('fs'), path=require('path');
const file=process.argv[2], threadId=process.argv[3], model=process.argv[4], workspace=process.argv[5], contextRaw=process.argv[6], execMode=process.argv[7];
let obj={};
if (fs.existsSync(file) && fs.statSync(file).size>0) {
  try { obj=JSON.parse(fs.readFileSync(file,'utf8')); }
  catch(e) { console.error(`ERR Invalid Agent session JSON: ${file}`); process.exit(3); }
  if (obj.format && obj.format !== 'ai-agent-session') {
    console.error(`ERR Session file belongs to ${obj.format}, not Agent.`); process.exit(4);
  }
}
const now=new Date().toISOString();
obj.format='ai-agent-session'; obj.version=1;
if (!obj.created_at) obj.created_at=now;
obj.updated_at=now;
if (threadId) obj.thread_id=threadId;
else if (obj.thread_id === undefined) obj.thread_id=null;
if (model) obj.model=model;
if (workspace) obj.workspace=workspace;
if (contextRaw) obj.context=contextRaw;
else if (obj.context === undefined) obj.context='';
if (execMode) obj.execution_approvals=execMode;
const tmp=`${file}.tmp-${process.pid}`;
fs.writeFileSync(tmp, JSON.stringify(obj,null,2)+'\n', {mode:0o600});
try { fs.chmodSync(tmp,0o600); } catch(_) {}
fs.renameSync(tmp,file);
try { fs.chmodSync(file,0o600); } catch(_) {}
NODE_AGENT_SESSION
}

validate_session_file_for() {
  local file="$1" expected="$2" fmt
  [[ -e "$file" ]] || return 0
  [[ -f "$file" ]] || die "Session path exists but is not a regular file: $file"
  [[ -s "$file" ]] || return 0
  fmt="$(session_file_format "$file")"
  [[ -n "$fmt" ]] || die "Session file is not valid JSON or has no format marker: $file"
  case "$expected:$fmt" in
    chat:ai-chat-session|agent:ai-agent-session) return 0 ;;
    *) die "Session file type mismatch: expected $expected session, found $fmt: $file" ;;
  esac
}

codex_sessions_root() {
  printf '%s/sessions\n' "${CODEX_HOME:-$HOME/.codex}"
}

codex_session_snapshot() {
  local output="$1" root
  root="$(codex_sessions_root)"
  : > "$output"
  [[ -d "$root" ]] || return 0
  find "$root" -type f -name 'rollout-*.jsonl*' -print 2>/dev/null | LC_ALL=C sort > "$output"
}

codex_uuid_from_rollout_path() {
  local path="$1" base
  base="${path##*/}"
  printf '%s\n' "$base" | grep -Eo '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}' | head -n 1
}

codex_new_thread_id_from_snapshot() {
  local before="$1" after candidate id
  after="$(mktemp -t ai-codex-sessions-after.XXXXXX)"
  codex_session_snapshot "$after"
  candidate="$(comm -13 "$before" "$after" 2>/dev/null | LC_ALL=C sort | head -n 1 || true)"
  rm -f "$after"
  [[ -n "$candidate" ]] || return 1
  id="$(codex_uuid_from_rollout_path "$candidate" || true)"
  [[ -n "$id" ]] || return 1
  printf '%s\n' "$id"
}

chat_model_with_inputs() {
  local model="$1" context_raw="${2:-}" input_blob="${3:-}" session_file="${4:-}" context="" list_file node_script status=0
  ensure_ollama_cli; ensure_ollama_api
  model_is_installed "$model" || die "Model $model is not installed. Install it first with: ai --install $model"
  require_cmd node
  if [[ -n "$context_raw" ]]; then context="$(parse_context_length "$context_raw")"; fi
  if [[ -n "$session_file" ]]; then
    session_file="$(normalize_session_file_path "$session_file")"
    validate_session_file_for "$session_file" chat
  fi
  local p has_images=0
  while IFS= read -r p; do [[ -n "$p" ]] || continue; is_image_input_file "$p" && has_images=1; done <<< "$input_blob"
  if (( has_images == 1 )) && ! model_supports_vision "$model"; then
    die "Model $model does not advertise Ollama's vision capability, but image input files were provided."
  fi
  list_file="$(mktemp -t ai-chat-inputs.XXXXXX)"; node_script="$(mktemp -t ai-chat-session.XXXXXX.js)"
  printf '%s\n' "$input_blob" > "$list_file"
  cat > "$node_script" <<'NODECHAT_SESSION'
const fs = require('fs');
const http = require('http');
const https = require('https');
const readline = require('readline');
const cp = require('child_process');
const base = process.argv[2];
const model = process.argv[3];
const context = Number(process.argv[4] || 0);
const contextRaw = process.argv[5] || '';
const listFile = process.argv[6];
const sessionFile = process.argv[7] || '';
const files = fs.readFileSync(listFile, 'utf8').split(/\r?\n/).filter(Boolean);
const imageRe = /\.(png|jpe?g|webp|bmp|tiff?|heic|heif)$/i;
let imagePaths = [];
let chunks = [];
let used = 0;
const maxTotal = context > 0 ? Math.max(32768, Math.min(524288, context * 2)) : 131072;
for (const file of files) {
  try {
    if (imageRe.test(file)) { imagePaths.push(file); continue; }
    let text = '';
    if (/\.pdf$/i.test(file)) {
      const r = cp.spawnSync('pdftotext', ['-layout', file, '-'], {encoding: 'utf8'});
      if (r.status === 0 && r.stdout) text = r.stdout;
      else { console.error(`WARN PDF skipped (pdftotext unavailable or failed): ${file}`); continue; }
    } else {
      const b = fs.readFileSync(file);
      if (b.includes(0)) { console.error(`WARN Binary input skipped: ${file}`); continue; }
      text = b.toString('utf8');
    }
    const remaining = maxTotal - used;
    if (remaining <= 0) break;
    if (Buffer.byteLength(text,'utf8') > remaining) {
      text = Buffer.from(text,'utf8').subarray(0,remaining).toString('utf8');
      console.error(`WARN Input context truncated to fit a conservative context budget: ${file}`);
    }
    used += Buffer.byteLength(text,'utf8');
    chunks.push(`--- FILE: ${file} ---\n${text}`);
  } catch(e) { console.error(`WARN Could not read input file ${file}: ${e.message}`); }
}
let messages=[];
let sessionObj=null;
function saveSession() {
  if (!sessionFile) return;
  const now=new Date().toISOString();
  if (!sessionObj) sessionObj={format:'ai-chat-session',version:1,created_at:now};
  sessionObj.format='ai-chat-session'; sessionObj.version=1;
  sessionObj.updated_at=now; sessionObj.model=model; sessionObj.context=contextRaw;
  sessionObj.messages=messages;
  const tmp=`${sessionFile}.tmp-${process.pid}`;
  fs.writeFileSync(tmp, JSON.stringify(sessionObj,null,2)+'\n', {mode:0o600});
  try { fs.chmodSync(tmp,0o600); } catch(_) {}
  fs.renameSync(tmp,sessionFile);
  try { fs.chmodSync(sessionFile,0o600); } catch(_) {}
}
if (sessionFile && fs.existsSync(sessionFile) && fs.statSync(sessionFile).size>0) {
  try { sessionObj=JSON.parse(fs.readFileSync(sessionFile,'utf8')); }
  catch(e) { console.error(`ERR Invalid Chat session JSON: ${sessionFile}`); process.exit(3); }
  if (sessionObj.format !== 'ai-chat-session') { console.error(`ERR Not a Chat session file: ${sessionFile}`); process.exit(4); }
  if (!Array.isArray(sessionObj.messages)) { console.error(`ERR Chat session has no valid messages array: ${sessionFile}`); process.exit(5); }
  messages=sessionObj.messages;
  if (sessionObj.model && sessionObj.model !== model) console.error(`WARN Session was created with model ${sessionObj.model}; continuing with ${model}.`);
  console.log(`Session loaded: ${sessionFile} (${messages.length} stored messages)`);
} else if (sessionFile) {
  sessionObj={format:'ai-chat-session',version:1,created_at:new Date().toISOString(),model,context:contextRaw,messages:[]};
  saveSession();
  console.log(`Session created: ${sessionFile}`);
}
function apiMessages(stored) {
  return stored.map(m => {
    const out={role:m.role, content:m.content || ''};
    if (Array.isArray(m.image_paths) && m.image_paths.length) {
      const imgs=[];
      for (const p of m.image_paths) {
        try { imgs.push(fs.readFileSync(p).toString('base64')); }
        catch(e) { console.error(`WARN Session image unavailable, skipped: ${p}`); }
      }
      if (imgs.length) out.images=imgs;
    }
    return out;
  });
}
function postChat(storedMessages) {
  return new Promise((resolve,reject) => {
    const u=new URL('/api/chat', base.endsWith('/') ? base : base + '/');
    const payload={model, messages:apiMessages(storedMessages), stream:false};
    if (context>0) payload.options={num_ctx:context};
    const data=Buffer.from(JSON.stringify(payload));
    const lib=u.protocol==='https:'?https:http;
    const req=lib.request({hostname:u.hostname,port:u.port||(u.protocol==='https:'?443:80),path:u.pathname,method:'POST',headers:{'Content-Type':'application/json','Content-Length':data.length}},res=>{
      let body='';res.setEncoding('utf8');res.on('data',c=>body+=c);res.on('end',()=>{
        if(res.statusCode<200||res.statusCode>=300)return reject(new Error(`HTTP ${res.statusCode}: ${body}`));
        try{resolve(JSON.parse(body));}catch(e){reject(e);}
      });
    });
    req.on('error',reject);req.write(data);req.end();
  });
}
(async()=>{
  const rl=readline.createInterface({input:process.stdin,output:process.stdout,terminal:true});
  let invocationFirst=true;
  if (files.length) console.log(`Input files ready: ${files.length}.`);
  console.log('Type /bye or press Ctrl+D to exit.');
  rl.setPrompt('>>> ');rl.prompt();
  for await(const raw of rl){
    const line=raw.trim();
    if(!line){rl.prompt();continue;}
    if(line==='/bye'||line==='/exit')break;
    let content=raw;
    if(invocationFirst&&chunks.length) content=`Use the following input files as context for this conversation.\n\n${chunks.join('\n\n')}\n\nUSER MESSAGE:\n${raw}`;
    const msg={role:'user',content};
    if(invocationFirst&&imagePaths.length) msg.image_paths=imagePaths.slice();
    try{
      const response=await postChat(messages.concat([msg]));
      const answer=response&&response.message&&response.message.content?response.message.content:'';
      console.log(answer);
      messages.push(msg,{role:'assistant',content:answer});
      saveSession();
      invocationFirst=false;
    }catch(e){console.error(`ERR ${e.message}`);}
    rl.prompt();
  }
  rl.close();
})().catch(e=>{console.error(`ERR ${e.message}`);process.exit(1);});
NODECHAT_SESSION
  if [[ -n "$session_file" ]]; then
    info "Opening chat with $model using session: $session_file"
  else
    info "Opening chat with $model and $(input_blob_count "$input_blob") input file(s)..."
  fi
  set +e
  node "$node_script" "$OLLAMA_URL" "$model" "$context" "$context_raw" "$list_file" "$session_file"
  status=$?
  set -e
  rm -f "$node_script" "$list_file"
  return "$status"
}

chat_model() {
  local model="$1" context_raw="${2:-}" input_blob="${3:-}" session_file="${4:-}"
  local context="" chat_model_name="$model" temp_model="" modelfile="" status=0
  if [[ -n "$input_blob" || -n "$session_file" ]]; then
    chat_model_with_inputs "$model" "$context_raw" "$input_blob" "$session_file"
    return $?
  fi
  ensure_ollama_cli; ensure_ollama_api
  model_is_installed "$model" || die "Model $model is not installed. Install it first with: ai --install $model"
  if [[ -n "$context_raw" ]]; then
    context="$(parse_context_length "$context_raw")"; temp_model="ai-chat-session-$$-${RANDOM}"; modelfile="$(mktemp -t ai-chat-modelfile.XXXXXX)"
    cat > "$modelfile" <<EOF_CHAT_MODEL_111
FROM $model
PARAMETER num_ctx $context
EOF_CHAT_MODEL_111
    info "Preparing chat with $model (context: $context tokens)..."
    if ! ollama create "$temp_model" -f "$modelfile" >/dev/null; then rm -f "$modelfile"; die "Could not create the temporary chat profile."; fi
    rm -f "$modelfile"; chat_model_name="$temp_model"
  else
    info "Opening chat with $model (Ollama default context)..."
  fi
  printf '%b\n' "${DIM}Type /bye or press Ctrl+D to exit.${RESET}"
  set +e; ollama run "$chat_model_name"; status=$?; set -e
  if [[ -n "$temp_model" ]]; then info "Removing temporary chat profile..."; ollama stop "$temp_model" >/dev/null 2>&1 || true; ollama rm "$temp_model" >/dev/null 2>&1 || warn "Could not remove temporary model profile: $temp_model"; fi
  return "$status"
}

agent_model() {
  local model="$1" directory="${2:-}" context_raw="${3:-}" exec_mode="${4:-auto}" input_blob="${5:-}" session_file="${6:-}"
  local workspace="" temp_workspace="" sandbox_mode="read-only" started_by_agent=0 status=0 staging_dir="" initial_prompt="" path base dest rel index=0 codex_has_image_args=0 agent_has_images=0 agent_model_vision=0 codex_image_supported=0
  local session_thread_id="" session_is_resume=0 snapshot="" detected_thread_id="" session_workspace_meta=""
  local -a codex_exec_args codex_tool_args codex_input_args codex_common_args
  codex_exec_args=(); codex_tool_args=(); codex_input_args=(); codex_common_args=()
  ensure_ollama_cli; ensure_ollama_api; ensure_codex_cli; exec_mode="$(validate_exec_mode "$exec_mode")"
  model_is_installed "$model" || die "Model $model is not installed. Install it first with: ai --install $model"
  model_supports_tools "$model" || die "Model $model does not advertise Ollama's 'tools' capability and cannot be used as a Codex agent."

  if [[ -n "$directory" ]]; then
    [[ "$directory" != "~" ]] || directory="$HOME"; [[ "$directory" != "~/"* ]] || directory="$HOME/${directory#~/}"
    mkdir -p "$directory" || die "Could not create agent directory: $directory"; workspace="$(cd "$directory" && pwd -P)" || die "Could not access agent directory: $directory"; sandbox_mode="workspace-write"
    info "Codex workspace: $workspace"; info "Sandbox: workspace-write"
  else
    temp_workspace="$(mktemp -d -t ai-agent-workspace.XXXXXX)"; workspace="$temp_workspace"; sandbox_mode="read-only"
    info "No --directory was provided."; info "Codex will use an empty temporary read-only workspace: $workspace"
  fi

  if [[ -n "$directory" ]]; then session_workspace_meta="$workspace"; fi

  if [[ -n "$session_file" ]]; then
    session_file="$(normalize_session_file_path "$session_file")"
    validate_session_file_for "$session_file" agent
    if [[ -s "$session_file" ]]; then session_thread_id="$(session_json_get "$session_file" thread_id 2>/dev/null || true)"; fi
    if [[ -n "$session_thread_id" ]]; then session_is_resume=1; info "Codex session: resuming $session_thread_id"; else info "Codex session: creating $session_file"; fi
    agent_session_merge "$session_file" "$session_thread_id" "$model" "$session_workspace_meta" "$context_raw" "$exec_mode" || die "Could not initialize Agent session file: $session_file"
  fi

  if [[ -n "$input_blob" ]]; then
    while IFS= read -r path; do [[ -n "$path" ]] || continue; if is_image_input_file "$path"; then agent_has_images=1; fi; done <<< "$input_blob"
    if (( agent_has_images == 1 )); then if model_supports_vision "$model"; then agent_model_vision=1; fi; if codex_supports_image_flag; then codex_image_supported=1; fi; fi
    staging_dir="$workspace/.ai-input-$$"; mkdir -p "$staging_dir" || die "Could not create temporary input-file staging directory."
    initial_prompt="The user provided the following input files as bootstrap context. Inspect them before answering or acting:"
    while IFS= read -r path; do
      [[ -n "$path" ]] || continue; index=$((index + 1)); base="${path##*/}"; dest="$staging_dir/$(printf '%02d' "$index")_$base"
      cp -p "$path" "$dest" || { rm -rf "$staging_dir"; die "Could not stage input file: $path"; }
      rel="${dest#$workspace/}"; initial_prompt="${initial_prompt}"$'\n'"- $rel"
      if is_image_input_file "$dest" && (( agent_model_vision == 1 && codex_image_supported == 1 )); then codex_input_args+=( --image "$dest" ); codex_has_image_args=1; fi
    done <<< "$input_blob"
    initial_prompt="${initial_prompt}"$'\n\n'"Treat these files as context supplied explicitly by the user."
    info "Input files staged: $index"
    if (( agent_has_images == 1 && agent_model_vision == 0 )); then warn "The selected model does not advertise vision; image files can only be useful through enabled tools or other file-processing steps."; fi
  fi

  if model_is_running "$model"; then info "Model is already running: $model"; [[ -z "$context_raw" ]] || warn "The model is already running, so --context-length will not change its current context."; else run_model "$model" "$context_raw"; started_by_agent=1; fi
  info "Starting Codex with local model: $model"; info "Codex provider: ollama (${OLLAMA_URL%/}/v1)"; info "Execution approvals: $exec_mode"; info "Tools: $(tools_enabled_summary)"
  case "$exec_mode" in
    ask) codex_exec_args=( --ask-for-approval on-request -c 'approvals_reviewer="user"' ) ;;
    auto) codex_exec_args=( --ask-for-approval on-request -c 'approvals_reviewer="auto_review"' ) ;;
    no-ask) codex_exec_args=( --ask-for-approval never -c 'approvals_reviewer="user"' ) ;;
  esac
  if tool_is_enabled shell; then codex_tool_args+=( -c 'features.shell_tool=true' ); else codex_tool_args+=( -c 'features.shell_tool=false' ); fi
  if tool_is_enabled view-image; then codex_tool_args+=( -c 'tools.view_image=true' ); else codex_tool_args+=( -c 'tools.view_image=false' ); fi
  if tool_is_enabled web-search; then codex_tool_args+=( -c 'web_search="live"' ); else codex_tool_args+=( -c 'web_search="disabled"' ); fi
  codex_common_args=( --oss --local-provider ollama -m "$model" --sandbox "$sandbox_mode" -C "$workspace" )
  if (( codex_has_image_args == 1 )); then codex_common_args+=( "${codex_input_args[@]}" ); fi
  codex_common_args+=( "${codex_tool_args[@]}" "${codex_exec_args[@]}" )

  if [[ -n "$session_file" && $session_is_resume -eq 0 ]]; then snapshot="$(mktemp -t ai-codex-sessions-before.XXXXXX)"; codex_session_snapshot "$snapshot"; fi
  set +e
  (
    cd "$workspace" || exit 1
    if (( session_is_resume == 1 )); then
      if [[ -n "$initial_prompt" ]]; then
        CODEX_OSS_BASE_URL="${OLLAMA_URL%/}/v1" codex "${codex_common_args[@]}" resume "$session_thread_id" "$initial_prompt"
      else
        CODEX_OSS_BASE_URL="${OLLAMA_URL%/}/v1" codex "${codex_common_args[@]}" resume "$session_thread_id"
      fi
    else
      if [[ -n "$initial_prompt" ]]; then
        CODEX_OSS_BASE_URL="${OLLAMA_URL%/}/v1" codex "${codex_common_args[@]}" "$initial_prompt"
      else
        CODEX_OSS_BASE_URL="${OLLAMA_URL%/}/v1" codex "${codex_common_args[@]}"
      fi
    fi
  )
  status=$?
  set -e

  if [[ -n "$session_file" && $session_is_resume -eq 0 ]]; then
    detected_thread_id="$(codex_new_thread_id_from_snapshot "$snapshot" 2>/dev/null || true)"
    rm -f "$snapshot"
    if [[ -n "$detected_thread_id" ]]; then
      agent_session_merge "$session_file" "$detected_thread_id" "$model" "$session_workspace_meta" "$context_raw" "$exec_mode" >/dev/null || true
      success "Agent session saved: $session_file"
    else
      warn "Codex session file was created, but the new native Codex session ID could not be detected. The next run will start a new session."
    fi
  elif [[ -n "$session_file" ]]; then
    agent_session_merge "$session_file" "$session_thread_id" "$model" "$session_workspace_meta" "$context_raw" "$exec_mode" >/dev/null || true
  fi

  [[ -z "$staging_dir" ]] || rm -rf "$staging_dir"
  [[ -z "$temp_workspace" ]] || rm -rf "$temp_workspace"
  if (( started_by_agent == 1 )); then info "The model was started by --agent; stopping it now..."; ollama stop "$model" >/dev/null 2>&1 || warn "Could not stop model: $model"; fi
  return "$status"
}

tui_session_path_prompt() {
  local current="${1:-}" title="${2:-Session}" value
  if value="$(tui_capture_dialog --title "$title" --cancel-label Back --ok-label Save --inputbox \
      "Session file path. Leave empty for no session. A missing file is created on Run." 10 86 "$current")"; then
    if [[ -z "$value" ]]; then printf '\n'; else normalize_session_file_path "$value"; fi
    return 0
  fi
  return 1
}

tui_chat_view() {
  local model="${1:-}" explicit_context="${2:-}" context result status field value display_model display_inputs display_session input_file blob session_file=""
  local -a items
  input_file="$(mktemp -t ai-tui-chat-inputs.XXXXXX)"; : > "$input_file"
  [[ -n "$model" ]] || model="$(tui_default_installed_model)"
  if [[ -n "$explicit_context" ]]; then context="$explicit_context"; else context="$(state_get chat_context 16K)"; fi
  context_value_valid "$context" || context=16K
  while true; do
    display_model="${model:-Not selected}"; display_inputs="$(input_list_summary "$input_file")"; display_session="${session_file:-None}"
    items=(
      model "$(printf '%-22s [%s]' 'Model' "$display_model")"
      context "$(printf '%-22s [%s]' 'Context Length' "$context")"
      session "$(printf '%-22s [%s]' 'Session' "$display_session")"
      inputs "$(printf '%-22s [%s]' 'Input Files' "$display_inputs")"
    )
    result="$(tui_dialog_capture_status --title 'Chat Options' --no-tags --no-hot-list --ok-label Edit --cancel-label Back --extra-button --extra-label Run --hline 'Up/Down Navigate   Enter Edit   Run Start Chat   Esc Back' --menu '' 16 94 6 "${items[@]}")"
    status="${result%%|*}"; field="${result#*|}"
    case "$status" in
      0)
        case "$field" in
          model) if value="$(tui_select_installed_model 'Chat Model' "$model")"; then model="$value"; fi ;;
          context) if value="$(tui_context_length_prompt "$context")"; then context="$value"; state_set chat_context "$context"; fi ;;
          session) if value="$(tui_session_path_prompt "$session_file" 'Chat Session')"; then session_file="$value"; fi ;;
          inputs) tui_input_files_editor "$input_file" any 'Input Files' ;;
        esac
        ;;
      3)
        if [[ -z "$model" ]]; then tui_show_message 'Chat Options' 'Select an installed model before starting Chat.'; continue; fi
        blob="$(cat "$input_file")"; tui_run_terminal "Chat: $model" chat_model "$model" "$context" "$blob" "$session_file"
        ;;
      1|255|-1) rm -f "$input_file"; return 0 ;;
    esac
  done
}

tui_agent_view() {
  local model="${1:-}" explicit_context="${2:-}" explicit_workspace="${3:-}" explicit_approval="${4:-}" context workspace approval result status field value display_model display_workspace display_tools display_inputs display_session workspace_start="$PWD" input_file blob session_file=""
  local -a items
  input_file="$(mktemp -t ai-tui-agent-inputs.XXXXXX)"; : > "$input_file"
  [[ -n "$model" ]] || model="$(tui_default_installed_model)"
  if [[ -n "$explicit_context" ]]; then context="$explicit_context"; else context="$(state_get agent_context 16K)"; fi; context_value_valid "$context" || context=16K
  if [[ -n "$explicit_workspace" ]]; then workspace="$explicit_workspace"; else workspace="$(state_get agent_workspace '')"; fi
  if [[ -n "$explicit_approval" ]]; then approval="$explicit_approval"; else approval="$(state_get agent_approval ask)"; fi
  case "$approval" in ask|auto|no-ask) ;; *) approval=ask ;; esac
  while true; do
    display_model="${model:-Not selected}"; display_workspace="$(tui_display_workspace "$workspace")"; display_tools="$(tools_enabled_summary)"; display_inputs="$(input_list_summary "$input_file")"; display_session="${session_file:-None}"
    items=(
      model "$(printf '%-22s [%s]' 'Model' "$display_model")"
      context "$(printf '%-22s [%s]' 'Context Length' "$context")"
      workspace "$(printf '%-22s [%s]' 'Workspace' "$display_workspace")"
      approval "$(printf '%-22s [%s]' 'Execution Approvals' "$approval")"
      tools "$(printf '%-22s [%s]' 'Tools' "$display_tools")"
      session "$(printf '%-22s [%s]' 'Session' "$display_session")"
      inputs "$(printf '%-22s [%s]' 'Input Files' "$display_inputs")"
    )
    result="$(tui_dialog_capture_status --title 'Codex Options' --no-tags --no-hot-list --ok-label Edit --cancel-label Back --extra-button --extra-label Run --hline 'Up/Down Navigate   Enter Edit   Run Start Codex   Esc Back' --menu '' 20 98 9 "${items[@]}")"
    status="${result%%|*}"; field="${result#*|}"
    case "$status" in
      0)
        case "$field" in
          model) if value="$(tui_select_installed_model 'Agent Model' "$model")"; then model="$value"; fi ;;
          context) if value="$(tui_context_length_prompt "$context")"; then context="$value"; state_set agent_context "$context"; fi ;;
          workspace) if [[ -n "$workspace" ]]; then workspace_start="$workspace"; else workspace_start="$PWD"; fi; if tui_agent_workspace_prompt "$workspace_start"; then workspace="$TUI_AGENT_WORKSPACE"; state_set agent_workspace "$workspace"; fi ;;
          approval) if value="$(tui_exec_mode_prompt "$approval")"; then approval="$value"; state_set agent_approval "$approval"; fi ;;
          tools) tui_tools_checklist || true ;;
          session) if value="$(tui_session_path_prompt "$session_file" 'Agent Session')"; then session_file="$value"; fi ;;
          inputs) tui_input_files_editor "$input_file" any 'Input Files' ;;
        esac
        ;;
      3)
        if [[ -z "$model" ]]; then tui_show_message 'Codex Options' 'Select an installed model before running Codex.'; continue; fi
        blob="$(cat "$input_file")"; tui_run_terminal "Codex agent: $model" agent_model "$model" "$workspace" "$context" "$approval" "$blob" "$session_file"
        ;;
      1|255|-1) rm -f "$input_file"; return 0 ;;
    esac
  done
}

tui_agent_flow() { tui_agent_view "$1"; }

main() {
  if [[ $# -eq 0 ]]; then tui_main; exit 0; fi
  local action="$1"; shift
  case "$action" in
    --help) require_no_extra_args "$@"; usage ;;
    --setup) require_no_extra_args "$@"; setup_all ;;
    --tools) require_no_extra_args "$@"; show_tools ;;
    --tool)
      [[ $# -ge 2 ]] || die "Usage: ai --tool [TOOL] --enable|-e|--disable|-d"; local tool_target="$1" tool_action="$2" tool_state=""; shift 2; require_no_extra_args "$@"; case "$tool_action" in --enable|-e)tool_state=enabled;; --disable|-d)tool_state=disabled;; *)die "Unknown tool action: $tool_action";; esac; tool_target="$(normalize_tool_name "$tool_target")"||die "Unknown tool: $tool_target";tool_set_state "$tool_target" "$tool_state";success "Tool $tool_target: $tool_state" ;;
    --list)
      local list_target=local list_order=model list_direction=auto list_direction_seen=""
      if [[ $# -gt 0 && "$1" != --* ]]; then list_target="$1";shift;fi
      while [[ $# -gt 0 ]];do case "$1" in --order|-o)[[ $# -ge 2 ]]||die "$1 requires a value.";list_order="$2";shift 2;; --asc)[[ "$list_direction_seen" != desc ]]||die "--asc and --desc cannot be combined.";list_direction=asc;list_direction_seen=asc;shift;; --desc)[[ "$list_direction_seen" != asc ]]||die "--asc and --desc cannot be combined.";list_direction=desc;list_direction_seen=desc;shift;; --*)die "Unknown option for --list: $1";; *)die "Unexpected argument for --list: $1";; esac;done
      case "$list_target" in local|ollama|ollama-experimental|draw-things);; *)die "Unknown list target: $list_target. Expected: local, ollama, ollama-experimental, or draw-things.";; esac; list_models_by_target "$list_target" "$list_order" "$list_direction" ;;
    --install)
      [[ $# -ge 1 ]]||die "Usage: ai --install MODEL [--backend ollama|draw-things] | ai --install --source URL [--backend ollama|draw-things] [--type auto|model|lora]";local install_target="" install_source="" install_backend=auto install_source_type=auto
      while [[ $# -gt 0 ]];do case "$1" in --source|-s)[[ $# -ge 2 ]]||die "$1 requires URL";install_source="$2";shift 2;; --backend|-b)[[ $# -ge 2 ]]||die "$1 requires backend";install_backend="$2";shift 2;; --type|-t)[[ $# -ge 2 ]]||die "$1 requires type";install_source_type="$2";shift 2;; --*)die "Unknown option for --install: $1";; *)[[ -z "$install_target" ]]||die "More than one model provided.";install_target="$1";shift;; esac;done
      if [[ -n "$install_source"&&-n "$install_target" ]];then die "Use either MODEL or --source.";elif [[ -n "$install_source" ]];then install_model_from_source "$install_source" "$install_backend" "$install_source_type";elif [[ -n "$install_target" ]];then [[ "$install_source_type" == auto ]]||die "--type can only be used together with --source."; install_named_model "$install_target" "$install_backend";else die "Missing model/source.";fi ;;
    --uninstall) [[ $# -ge 1 ]]||die "Usage: ai --uninstall MODEL";local uninstall_target="$1";shift;require_no_extra_args "$@";uninstall_named_model "$uninstall_target" ;;
    --set-base) [[ $# -ge 1 ]]||die "Usage: ai --set-base MODEL";local base_target="$1";shift;require_no_extra_args "$@";set_base_model "$base_target" ;;
    --image)
      local image_model="" image_width=800 image_height=600 image_output_dir="$PWD" image_file_name="" image_prompt="" image_strength="" input_blob="" normalized="" explicit_model=0 explicit_width=0 explicit_height=0 explicit_dir=0
      while [[ $# -gt 0 ]];do
        case "$1" in
          --width|-w) [[ $# -ge 2 ]]||die "$1 requires width"; image_width="$2"; explicit_width=1; shift 2 ;;
          --height|-h) [[ $# -ge 2 ]]||die "$1 requires height"; image_height="$2"; explicit_height=1; shift 2 ;;
          --output-dir|-o) [[ $# -ge 2 ]]||die "$1 requires directory"; image_output_dir="$2"; explicit_dir=1; shift 2 ;;
          --file-name|-n) [[ $# -ge 2 ]]||die "$1 requires name"; image_file_name="$2"; shift 2 ;;
          --prompt|-p) [[ $# -ge 2 ]]||die "$1 requires prompt"; image_prompt="$2"; shift 2 ;;
          --input-file|-i) [[ $# -ge 2 ]]||die "$1 requires a file"; normalized="$(normalize_input_file_path "$2")"; is_image_input_file "$normalized" || die "Image Generation input must be an image: $normalized"; input_blob="$(input_blob_append "$input_blob" "$normalized")"; shift 2 ;;
          --strength) [[ $# -ge 2 ]]||die "$1 requires a value from 0 to 1"; image_strength="$2"; shift 2 ;;
          --*) die "Unknown option for --image: $1" ;;
          *) [[ -z "$image_model" ]]||die "More than one image model provided."; image_model="$1"; explicit_model=1; shift ;;
        esac
      done
      [[ -n "$image_prompt" ]]||die "--image requires --prompt/-p."
      (( explicit_model == 0 )) || state_set image_model "$image_model"; (( explicit_width == 0 )) || state_set image_width "$image_width"; (( explicit_height == 0 )) || state_set image_height "$image_height"; (( explicit_dir == 0 )) || state_set image_target_dir "$image_output_dir"
      generate_image "$image_model" "$image_width" "$image_height" "$image_output_dir" "$image_file_name" "$image_prompt" "$input_blob" "$image_strength"
      ;;
    --run)
      local run_target="" context_raw="";while [[ $# -gt 0 ]];do case "$1" in --context-length|-l)[[ $# -ge 2 ]]||die "$1 requires value";context_raw="$2";shift 2;; --*)die "Unknown option for --run: $1";; *)[[ -z "$run_target" ]]||die "More than one model provided.";run_target="$1";shift;; esac;done;run_target="$(resolve_model_or_base "$run_target")";run_model "$run_target" "$context_raw" ;;
    --chat)
      local chat_target="" context_raw="" input_blob="" normalized="" context_seen=0 chat_model_seen=0 session_file="" session_seen=0 stored=""
      while [[ $# -gt 0 ]];do
        case "$1" in
          --context-length|-l) [[ $# -ge 2 ]]||die "$1 requires value"; context_raw="$2"; context_seen=1; shift 2 ;;
          --input-file|-i) [[ $# -ge 2 ]]||die "$1 requires a file"; normalized="$(normalize_input_file_path "$2")"; input_blob="$(input_blob_append "$input_blob" "$normalized")"; shift 2 ;;
          --session|-s) [[ $# -ge 2 ]]||die "$1 requires a session file"; (( session_seen == 0 ))||die "--session/-s was provided more than once."; session_file="$(normalize_session_file_path "$2")"; session_seen=1; shift 2 ;;
          --*) die "Unknown option for --chat: $1" ;;
          *) [[ -z "$chat_target" ]]||die "More than one model provided."; chat_target="$1"; chat_model_seen=1; shift ;;
        esac
      done
      if [[ -n "$session_file" ]]; then
        validate_session_file_for "$session_file" chat
        if [[ -s "$session_file" ]]; then
          if (( chat_model_seen == 0 )); then stored="$(session_json_get "$session_file" model 2>/dev/null || true)"; [[ -z "$stored" ]] || chat_target="$stored"; fi
          if (( context_seen == 0 )); then stored="$(session_json_get "$session_file" context 2>/dev/null || true)"; [[ -z "$stored" ]] || context_raw="$stored"; fi
        fi
      fi
      (( context_seen == 0 )) || state_set chat_context "$context_raw"
      chat_target="$(resolve_model_or_base "$chat_target")";chat_model "$chat_target" "$context_raw" "$input_blob" "$session_file"
      ;;
    --agent)
      local agent_target="" agent_directory="" context_raw="" exec_mode=auto exec_mode_set=0 input_blob="" normalized="" directory_seen=0 context_seen=0 agent_model_seen=0 session_file="" session_seen=0 stored=""
      while [[ $# -gt 0 ]];do
        case "$1" in
          --directory|-d) [[ $# -ge 2 ]]||die "$1 requires directory"; agent_directory="$2"; directory_seen=1; shift 2 ;;
          --context-length|-l) [[ $# -ge 2 ]]||die "$1 requires value"; context_raw="$2"; context_seen=1; shift 2 ;;
          --exec) [[ $# -ge 2 ]]||die "--exec requires mode";((exec_mode_set==0))||die "--exec repeated";exec_mode="$(validate_exec_mode "$2")";exec_mode_set=1;shift 2 ;;
          --input-file|-i) [[ $# -ge 2 ]]||die "$1 requires a file"; normalized="$(normalize_input_file_path "$2")"; input_blob="$(input_blob_append "$input_blob" "$normalized")"; shift 2 ;;
          --session|-s) [[ $# -ge 2 ]]||die "$1 requires a session file"; (( session_seen == 0 ))||die "--session/-s was provided more than once."; session_file="$(normalize_session_file_path "$2")"; session_seen=1; shift 2 ;;
          --*) die "Unknown option for --agent: $1" ;;
          *) [[ -z "$agent_target" ]]||die "More than one model provided."; agent_target="$1"; agent_model_seen=1; shift ;;
        esac
      done
      if [[ -n "$session_file" ]]; then
        validate_session_file_for "$session_file" agent
        if [[ -s "$session_file" ]]; then
          if (( agent_model_seen == 0 )); then stored="$(session_json_get "$session_file" model 2>/dev/null || true)"; [[ -z "$stored" ]] || agent_target="$stored"; fi
          if (( directory_seen == 0 )); then stored="$(session_json_get "$session_file" workspace 2>/dev/null || true)"; [[ -z "$stored" ]] || agent_directory="$stored"; fi
          if (( context_seen == 0 )); then stored="$(session_json_get "$session_file" context 2>/dev/null || true)"; [[ -z "$stored" ]] || context_raw="$stored"; fi
          if (( exec_mode_set == 0 )); then stored="$(session_json_get "$session_file" execution_approvals 2>/dev/null || true)"; case "$stored" in ask|auto|no-ask) exec_mode="$stored" ;; esac; fi
        fi
      fi
      (( context_seen == 0 )) || state_set agent_context "$context_raw"; (( directory_seen == 0 )) || state_set agent_workspace "$agent_directory"; (( exec_mode_set == 0 )) || state_set agent_approval "$exec_mode"
      agent_target="$(resolve_model_or_base "$agent_target")";agent_model "$agent_target" "$agent_directory" "$context_raw" "$exec_mode" "$input_blob" "$session_file"
      ;;
    --stop) local stop_target="${1:-}";[[ $# -eq 0 ]]||shift;require_no_extra_args "$@";stop_target="$(resolve_model_or_base "$stop_target")";stop_model "$stop_target" ;;
    --stop-all) require_no_extra_args "$@";stop_all_models ;;
    --purge) purge_component "$@" ;;
    --version) require_no_extra_args "$@";show_versions ;;
    *) die "Unknown command: $action. Run: ai --help" ;;
  esac
}



# -----------------------------------------------------------------------------
# 1.11.1 overrides: Draw Things content-filter visibility
# -----------------------------------------------------------------------------

# Conservative technical heuristic for the *runtime prompt/safety gate* only.
# "None*" does not mean that a model has no license, use-policy, or legal limits.
# Unknown families stay Unknown rather than being guessed as unrestricted.
draw_things_filter_for() {
  local value
  value="$(printf '%s' "$*" | tr '[:upper:]' '[:lower:]')"
  case "$value" in
    *sd_v1*|*sd-v1*|*stable\ diffusion\ v1*|*sd_v2*|*sd-v2*|*stable\ diffusion\ v2*|*sd_xl*|*sd-xl*|*sdxl*|*stable\ diffusion\ xl*|\
    *minisd*|*instruct_pix2pix*|*ssd_1b*|*counterfeit*|*deliberate*|*disney_pixar*|*dreamshaper*|*juggernaut*|*majicmix*|*realistic_vision*|*realvisxl*|*rev_animated*|\
    *anything_v3*|*arcane_v3*|*balloonart*|*classicanim*|*cyberpunk_anime*|*dnd_*|*eldenring*|*f222*|*ghibli*|*hassanblend*|*hna_3dkx*|*inkpunk*|*lvngvncnt*|*mdjrny*|*modi*|*nitro*|*papercut*|*redshift*|*samdoesart*|*seek_art*|*spiderverse*|*supermarionation*|*trnlgcy*|*voxelart*|*wd_v1.3*|\
    *animagine_xl*|*colorfulxl*|*fooocus_inpaint_sd_xl*|*icatcher_cartoon*|*icatcher_realistic*|*pixelwave*|*proteus_v0.3*|*playground_v2*|*pixart_sigma*|*kandinsky*)
      printf '%s\n' 'None*'
      ;;
    *)
      printf '%s\n' 'Unknown'
      ;;
  esac
}

collect_draw_things_model_rows() {
  local output="$1" order_spec="${2:-model}" direction="${3:-auto}" skip_installed="${4:-0}"
  local hw os arch chip device ram_gb model bytes name source note size_gb size rating category description installed unsorted filter
  hw="$(detect_hardware)"; IFS='|' read -r os arch chip device ram_gb <<< "$hw"
  installed="$(draw_things_downloaded_models | cut -d'|' -f1 || true)"
  unsorted="$(mktemp -t ai-dt-rows-unsorted.XXXXXX)"; : > "$unsorted"
  while IFS='|' read -r model bytes name source note; do
    [[ -n "$model" ]] || continue
    if (( skip_installed == 1 )) && printf '%s\n' "$installed" | grep -Fqx "$model"; then continue; fi
    size_gb="$(bytes_to_gb "$bytes")"
    size="$(format_size_gb "$size_gb")"
    rating="$(hardware_rating "$size_gb" "$ram_gb")"
    category="$(draw_things_category_for "$model $name")"
    filter="$(draw_things_filter_for "$model" "$name")"
    description="$name"
    [[ -n "$source" ]] && description="$description [$source]"
    [[ -n "$note" && "$note" != "-" ]] && description="$description - $note"
    # Field 8 is mode-specific metadata. sort_model_rows already preserves it.
    printf '%s\tavailable\t%s\t%s\tN/A\t%s\t%s\t%s\n' \
      "$model" "$size" "$rating" "$category" "$description" "$filter" >> "$unsorted"
  done < <(draw_things_remote_catalog)
  sort_model_rows "$unsorted" "$output" "$order_spec" "$direction"
  rm -f "$unsorted"
}

print_draw_things_model_table() {
  local file="$1" cols
  cols="$(terminal_columns)"
  LC_ALL=C awk -F '\t' -v term="$cols" \
    -v reset="$RESET" -v header_color="$LIST_HEADER" -v model_color="$LIST_MODEL" \
    -v size_color="$LIST_SIZE" -v description_color="$LIST_DESCRIPTION" \
    -v separator_color="$LIST_SEPARATOR" -v green="$BRIGHT_GREEN" \
    -v yellow="$BRIGHT_YELLOW" -v dim="$DIM" '
    function clip(s,w){if(w<=0)return "";if(length(s)<=w)return s;if(w<=3)return substr(s,1,w);return substr(s,1,w-3)"..."}
    function dashes(w, s,i){s="";for(i=0;i<w;i++)s=s"-";return s}
    function fcolor(v){if(v=="None*")return green;if(v=="Unknown")return dim;return yellow}
    BEGIN{
      if(term>1)term--
      h1="Model";h2="Size";h3="Rating";h4="Filter";h5="Category";h6="Description"
      w2=length(h2);w3=length(h3);w4=length(h4);w5=length(h5)
    }
    NF>=8{
      rows[++n]=$0
      if(length($3)>w2)w2=length($3)
      if(length($4)>w3)w3=length($4)
      if(length($8)>w4)w4=length($8)
      if(length($6)>w5)w5=length($6)
      if(length($1)>maxmodel)maxmodel=length($1)
    }
    END{
      sep=10
      fixed=w2+w3+w4+w5+sep
      free=term-fixed
      if(free<32)free=32
      w1=maxmodel; if(w1<18)w1=18; if(w1>52)w1=52
      w6=free-w1
      if(w6<14){w6=14;w1=free-w6;if(w1<18)w1=18}
      printf "%s%-*s  %*s  %*s  %-*s  %-*s  %-*s%s\n",header_color,w1,h1,w2,h2,w3,h3,w4,h4,w5,h5,w6,h6,reset
      printf "%s%-*s  %*s  %*s  %-*s  %-*s  %-*s%s\n",separator_color,w1,dashes(w1),w2,dashes(w2),w3,dashes(w3),w4,dashes(w4),w5,dashes(w5),w6,dashes(w6),reset
      for(r=1;r<=n;r++){
        split(rows[r],a,"\t")
        printf "%s%-*s%s  %s%*s%s  %*s  %s%-*s%s  %-*s  %s%-*s%s\n",model_color,w1,clip(a[1],w1),reset,size_color,w2,a[3],reset,w3,a[4],fcolor(a[8]),w4,a[8],reset,w5,a[6],description_color,w6,clip(a[7],w6),reset
      }
    }' "$file"
  printf '\n%b\n' "${DIM}Filter: None* = no known runtime prompt/safety gate for this family in local Draw Things; Unknown = not classified.${RESET}"
  printf '%b\n' "${DIM}This is a technical heuristic only; model licenses, use policies, and applicable law still apply.${RESET}"
}

tui_prepare_draw_things_model_menu_data() {
  local input="$1" output="$2" header_file="$3" content_width="$4"
  (( content_width >= 58 )) || content_width=58
  LC_ALL=C awk -F '\t' -v OFS='\t' -v maxwidth="$content_width" -v header_file="$header_file" -v output="$output" '
    function clipped(s,w){if(length(s)<=w)return s;if(w<=3)return substr(s,1,w);return substr(s,1,w-3)"..."}
    function spaces(n, s,i){s="";for(i=0;i<n;i++)s=s" ";return s}
    BEGIN{h[1]="Model";h[2]="Size";h[3]="Rating";h[4]="Filter";h[5]="Category";for(i=1;i<=5;i++)w[i]=length(h[i])}
    NF>=8{
      rows[++n]=$0;v[1]=$1;v[2]=$3;v[3]=$4;v[4]=$8;v[5]=$6
      for(i=1;i<=5;i++)if(length(v[i])>w[i])w[i]=length(v[i])
    }
    END{
      separators=8;fixed=w[2]+w[3]+w[4]+w[5]+separators;model_space=maxwidth-fixed
      if(model_space<16)model_space=16;if(w[1]>model_space)w[1]=model_space
      header=sprintf("%-*s  %*s  %*s  %-*s  %-*s",w[1],h[1],w[2],h[2],w[3],h[3],w[4],h[4],w[5],h[5])
      pad=int((maxwidth-length(header))/2);if(pad<0)pad=0;print spaces(pad) header > header_file
      for(r=1;r<=n;r++){
        split(rows[r],a,"\t")
        display=sprintf("%-*s  %*s  %*s  %-*s  %-*s",w[1],clipped(a[1],w[1]),w[2],a[3],w[3],a[4],w[4],a[8],w[5],a[6])
        printf "%06d\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n",r,a[1],a[2],a[3],a[4],a[5],a[6],a[7],a[8],display > output
      }
    }' "$input"
}

tui_draw_things_row_by_id() {
  local data_file="$1" id="$2"
  LC_ALL=C awk -F '\t' -v id="$id" 'BEGIN{OFS="\t"}$1==id{print $2,$3,$4,$5,$6,$7,$8,$9;exit}' "$data_file"
}

tui_show_draw_things_model_details() {
  local row="$1" model status size rating code category description filter tmp
  IFS=$'\t' read -r model status size rating code category description filter <<< "$row"
  tmp="$(mktemp -t ai-tui-dt-details.XXXXXX)"
  cat > "$tmp" <<EOF
Model:       $model
Size:        $size
Rating:      $rating
Filter:      $filter
Category:    $category

Description:
$description

Filter meaning:
None*   - no known runtime prompt/safety gate for this model family in the local Draw Things path.
Unknown - the catalog metadata is insufficient for ai to classify it conservatively.

This is a technical heuristic only. It does not override model licenses, use policies, or applicable law.
EOF
  tui_show_text_file "Draw Things Model Details" "$tmp"
  rm -f "$tmp"
}

tui_draw_things_models_view() {
  local order="rating:desc|size:asc|model:asc|category:asc" selected_model="" rows data header rc result status output id row sort_result sorted_rows
  local screen_cols screen_rows dialog_width dialog_height menu_height content_width default_id header_text refresh_needed=1 layout_needed=1 last_content_width=0 description model_name
  local -a items
  ensure_draw_things_cli >/dev/null
  rc="$(tui_model_dialog_rc)";rows="$(mktemp -t ai-dt-tui-rows.XXXXXX)";data="$(mktemp -t ai-dt-tui-data.XXXXXX)";header="$(mktemp -t ai-dt-tui-header.XXXXXX)"
  while true;do
    screen_cols="$(terminal_columns)";screen_rows="$(terminal_lines)";dialog_width=$((screen_cols-4));dialog_height=$((screen_rows-4));((dialog_width>=76))||dialog_width=76;((dialog_height>=16))||dialog_height=16;menu_height=$((dialog_height-8));((menu_height>=6))||menu_height=6;content_width=$((dialog_width-10))
    if ((refresh_needed==1));then
      tui_dialog --title "Install Draw Things Models" --infobox "Loading Draw Things online catalog..." 5 66||true
      :>"$rows";collect_draw_things_model_rows "$rows" "$order" per-field 1
      if [[ ! -s "$rows" ]];then rm -f "$rows" "$data" "$header" "$rc";tui_show_message "Install Draw Things Models" "No installable Draw Things models could be loaded.";return 0;fi
      refresh_needed=0;layout_needed=1
    fi
    if ((layout_needed==1||last_content_width!=content_width));then :>"$data";:>"$header";tui_prepare_draw_things_model_menu_data "$rows" "$data" "$header" "$content_width";last_content_width=$content_width;layout_needed=0;fi
    header_text="$(cat "$header")";items=();default_id=""
    while IFS=$'\t' read -r id model st sz rt cx cat desc filter display;do
      [[ -n "$id" ]]||continue;items+=( "$id" "$display" );[[ -n "$selected_model"&&"$model"=="$selected_model" ]]&&default_id="$id"
    done < "$data"
    [[ -n "$default_id" ]]||default_id=000001
    result="$(tui_model_dialog_capture "$rc" --title "Install Draw Things Models" --default-item "$default_id" --no-tags --no-hot-list --scrollbar --cr-wrap --ok-label "Install" --cancel-label "Sort" --extra-button --extra-label "Details" --help-button --help-label "Back" --help-tags --hline "Up/Down Navigate   Enter Install   F1 Details   F2 Sort   Esc Back" --menu "$header_text" "$dialog_height" "$dialog_width" "$menu_height" "${items[@]}")";status="${result%%|*}";output="${result#*|}"
    case "$status" in
      0)
        id="$output";row="$(tui_draw_things_row_by_id "$data" "$id")"
        if [[ -n "$row" ]];then selected_model="${row%%$'\t'*}";description="$(printf '%s' "$row"|awk -F'\t' '{print $7}')";model_name="${description%% \[*}";if tui_confirm "Install Draw Things model" "Install $model_name?\n\nModel file: $selected_model";then tui_run_terminal "Install Draw Things model" install_draw_things_model "$selected_model" "$model_name";refresh_needed=1;fi;fi
        ;;
      3) id="$output";row="$(tui_draw_things_row_by_id "$data" "$id")";[[ -z "$row" ]]||tui_show_draw_things_model_details "$row" ;;
      1) if sort_result="$(tui_model_sort_menu "$order")";then order="$sort_result";sorted_rows="$(mktemp -t ai-dt-sorted.XXXXXX)";sort_model_rows "$rows" "$sorted_rows" "$order" per-field&&mv "$sorted_rows" "$rows"||rm -f "$sorted_rows";layout_needed=1;fi ;;
      2|255|-1) rm -f "$rows" "$data" "$header" "$rc";return 0 ;;
    esac
  done
}

list_models_by_target() {
  local target="${1:-local}" order="${2:-model}" direction="${3:-auto}" rows hw os arch chip device ram_gb
  order="$(normalize_list_order "$order")"
  case "$target" in
    local|'')
      rows="$(mktemp -t ai-list-local.XXXXXX)"; collect_combined_local_model_rows "$rows" "$order"
      print_hardware_summary_v191; printf '\n%s%s%s\n' "$LIST_HEADER" 'Local models / Draw Things assets:' "$RESET"
      if [[ -s "$rows" ]]; then print_local_combined_table "$rows" "$(get_base_model)"; else printf '%s(no local models installed)%s\n' "$DIM" "$RESET"; fi
      rm -f "$rows"
      ;;
    ollama)
      rows="$(mktemp -t ai-list-ollama.XXXXXX)"; tui_collect_install_model_rows "$rows" "$order"
      print_hardware_summary_v191; printf '\n%s%s%s\n' "$LIST_HEADER" 'Available Ollama models:' "$RESET"
      [[ -s "$rows" ]] && print_dynamic_model_table "$rows" available || printf '%s(no Ollama catalog available)%s\n' "$DIM" "$RESET"; rm -f "$rows"
      ;;
    ollama-experimental)
      hw="$(detect_hardware)"; IFS='|' read -r os arch chip device ram_gb <<< "$hw"; rows="$(mktemp -t ai-list-ollama-exp.XXXXXX)"; collect_experimental_model_rows "$rows" "$order" "$direction" "$ram_gb" 0
      print_hardware_summary_v191; printf '\n%s%s%s\n' "$LIST_HEADER" 'Experimental Ollama models:' "$RESET"
      [[ -s "$rows" ]] && print_dynamic_model_table "$rows" experimental || printf '%s(no experimental models available)%s\n' "$DIM" "$RESET"; rm -f "$rows"
      ;;
    draw-things)
      rows="$(mktemp -t ai-list-dt.XXXXXX)"; collect_draw_things_model_rows "$rows" "$order" "$direction" 0
      print_hardware_summary_v191; printf '\n%s%s%s\n' "$LIST_HEADER" 'Draw Things models:' "$RESET"
      [[ -s "$rows" ]] && print_draw_things_model_table "$rows" || printf '%s(no Draw Things catalog available)%s\n' "$DIM" "$RESET"; rm -f "$rows"
      ;;
    *) die "Unknown list target: $target. Expected: local, ollama, ollama-experimental, or draw-things." ;;
  esac
}


# -----------------------------------------------------------------------------
# 1.11.5 overrides: show all Draw Things disk assets in Local Models
# -----------------------------------------------------------------------------

# Preserve the optional ninth row field used by Local Models for the asset type.
# Other model lists still use the first eight fields and simply carry an empty ninth.
sort_model_rows() {
  local input="$1" output="$2" order_spec="$3" direction_override="$4"
  local enriched tab token key token_direction direction spec has_model=0
  local -a keys sort_args
  enriched="$(mktemp "${TMPDIR:-/tmp}/ai-sort.XXXXXX")"; tab="$(printf '\t')"
  LC_ALL=C awk -F '\t' 'BEGIN{OFS="\t"} NF>=7 {
    backend=(NF>=8?$8:""); asset_type=(NF>=9?$9:"")
    status_rank=0
    if($2=="available") status_rank=1; else if($2=="stopped"||$2=="Stopped"||$2=="installed"||$2=="Installed") status_rank=2; else if($2=="running"||$2=="Running") status_rank=3; else if($2=="base") status_rank=4; else if($2=="base/run") status_rank=5
    size_num=$3; gsub(/[^0-9.]/,"",size_num); if(size_num=="") size_num=0
    rating_num=$4; gsub(/[^0-9.]/,"",rating_num); if(rating_num=="") rating_num=-1
    codex_rank=0; if($5=="Unknown")codex_rank=1; else if($5=="Limited")codex_rank=2; else if($5=="General")codex_rank=3; else if($5=="Good")codex_rank=4; else if($5=="Very good")codex_rank=5; else if($5=="Excellent")codex_rank=6
    print $1,$2,$3,$4,$5,$6,$7,backend,asset_type,status_rank,size_num,rating_num,codex_rank
  }' "$input" > "$enriched"
  IFS='|' read -r -a keys <<< "$order_spec"; sort_args=( -s -t "$tab" )
  for token in "${keys[@]}"; do
    key="${token%%:*}"; token_direction=""; [[ "$token" == *:* ]] && token_direction="${token#*:}"
    if [[ "$direction_override" == "per-field" ]]; then
      direction="$token_direction"; [[ "$direction" == asc || "$direction" == desc ]] || { [[ "$key" == rating ]] && direction=desc || direction=asc; }
    else
      direction="$direction_override"; [[ "$direction" != auto ]] || { [[ "$key" == rating ]] && direction=desc || direction=asc; }
    fi
    case "$key" in
      model) spec="1,1"; has_model=1 ;;
      status) spec="10,10n" ;;
      size) spec="11,11n" ;;
      rating) spec="12,12n" ;;
      codex) spec="13,13n" ;;
      category) spec="6,6" ;;
      description) spec="7,7" ;;
      *) rm -f "$enriched"; die "Internal error: unsupported sort field: $key" ;;
    esac
    [[ "$direction" != desc ]] || spec="${spec}r"
    sort_args+=( "-k${spec}" )
  done
  (( has_model == 1 )) || sort_args+=( "-k1,1" )
  LC_ALL=C sort "${sort_args[@]}" "$enriched" | cut -f1-9 > "$output" || { rm -f "$enriched"; return 1; }
  rm -f "$enriched"
}

# Return bytes for one Draw Things asset and its optional -tensordata companion.
draw_things_asset_bytes() {
  local file="$1" total=0 n companion
  [[ -f "$file" ]] || { printf '0\n'; return 0; }
  n="$(wc -c < "$file" 2>/dev/null | tr -d '[:space:]' || true)"; [[ "$n" =~ ^[0-9]+$ ]] || n=0
  total=$((total + n))
  companion="${file}-tensordata"
  if [[ -f "$companion" ]]; then
    n="$(wc -c < "$companion" 2>/dev/null | tr -d '[:space:]' || true)"; [[ "$n" =~ ^[0-9]+$ ]] || n=0
    total=$((total + n))
  fi
  printf '%s\n' "$total"
}

# Conservative type classification for files that Draw Things itself did not expose
# as a downloaded model. Known downloaded model IDs are handled separately as Model.
draw_things_aux_asset_type() {
  local name
  name="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$name" in
    *lora*|*lycoris*|*locon*|*loha*|*lokr*) printf 'LoRA\n' ;;
    *.json|*.plist|*.sqlite|*.sqlite3|*.db|*.yaml|*.yml|*.txt) printf 'Metadata\n' ;;
    *) printf 'Dependency\n' ;;
  esac
}

# True when a filename is one of the main downloaded model IDs already emitted.
draw_things_known_model_file() {
  local known_file="$1" name="$2"
  grep -Fqx "$name" "$known_file" 2>/dev/null
}

collect_combined_local_model_rows() {
  local output="$1" order="${2:-status:desc|rating:desc|size:asc|model:asc|codex:desc|category:asc}"
  local hw os arch chip device ram_gb running name size_text size_value size_unit size_gb rating codex category description status display_size unsorted model dt_name bytes
  local dir known file base aux_type aux_category
  : > "$output"; hw="$(detect_hardware)"; IFS='|' read -r os arch chip device ram_gb <<< "$hw"
  unsorted="$(mktemp -t ai-local-combined.XXXXXX)"; known="$(mktemp -t ai-dt-known.XXXXXX)"; : > "$unsorted"; : > "$known"

  if command -v ollama >/dev/null 2>&1; then
    start_ollama_if_possible >/dev/null 2>&1 || true
    running="$(ollama ps 2>/dev/null | awk 'NR>1{print $1}' || true)"
    while IFS='|' read -r name size_text; do
      [[ -n "$name" ]] || continue
      size_value="${size_text%% *}"; size_unit="${size_text##* }"; size_gb="$(size_to_gb "$size_value" "$size_unit")"
      rating="$(hardware_rating "$size_gb" "$ram_gb")"; codex="$(codex_rating_for_model "$name" installed)"; category="$(model_category_for "$name")"; description="$(model_description_for "$name")"
      if name_list_contains "$name" "$running"; then status="Running"; else status="Stopped"; fi
      display_size="$(format_size_gb "$size_gb")"
      printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\tOllama\tModel\n' "$name" "$status" "$display_size" "$rating" "$codex" "$category" "$description" >> "$unsorted"
    done < <(installed_models_data)
  fi

  # First emit every model Draw Things knows as downloaded. Its -tensordata file is
  # counted in the same row, matching the pre-1.11.5 behavior.
  while IFS='|' read -r model dt_name; do
    [[ -n "$model" ]] || continue
    printf '%s\n' "$model" >> "$known"
    bytes="$(draw_things_model_bytes "$model")"; size_gb="$(bytes_to_gb "$bytes")"; display_size="$(format_size_gb "$size_gb")"; rating="$(hardware_rating "$size_gb" "$ram_gb")"; category="$(draw_things_category_for "$model $dt_name")"
    printf '%s\tInstalled\t%s\t%s\tN/A\t%s\t%s\tDraw Things\tModel\n' "$model" "$display_size" "$rating" "$category" "$dt_name" >> "$unsorted"
  done < <(draw_things_downloaded_models)

  # Then account for every other regular file in the Draw Things Models directory.
  # This makes downloaded CLIP/T5/VAE/etc. dependencies visible instead of silently
  # consuming disk space. A -tensordata companion is folded into its parent row.
  dir="$(draw_things_models_dir)"
  if [[ -d "$dir" ]]; then
    for file in "$dir"/*; do
      [[ -f "$file" ]] || continue
      name="${file##*/}"
      [[ "$name" == ".DS_Store" ]] && continue
      if draw_things_known_model_file "$known" "$name"; then continue; fi
      case "$name" in
        *-tensordata)
          base="${name%-tensordata}"
          if draw_things_known_model_file "$known" "$base" || [[ -f "$dir/$base" ]]; then continue; fi
          ;;
      esac
      bytes="$(draw_things_asset_bytes "$file")"
      size_gb="$(bytes_to_gb "$bytes")"; display_size="$(format_size_gb "$size_gb")"
      aux_type="$(draw_things_aux_asset_type "$name")"
      case "$aux_type" in
        LoRA) aux_category="Adapter"; description="Draw Things LoRA/adapter file detected in the Models directory" ;;
        Metadata) aux_category="Support"; description="Draw Things metadata/support file" ;;
        *) aux_category="Support"; description="Draw Things dependency/support file (may be shared by multiple models)" ;;
      esac
      printf '%s\tInstalled\t%s\tN/A\tN/A\t%s\t%s\tDraw Things\t%s\n' "$name" "$display_size" "$aux_category" "$description" "$aux_type" >> "$unsorted"
    done
  fi

  sort_model_rows "$unsorted" "$output" "$order" "per-field"
  rm -f "$unsorted" "$known"
}

tui_collect_local_model_rows() { collect_combined_local_model_rows "$@"; }

print_local_combined_table() {
  local file="$1" base="${2:-}" cols normalized_base=""
  cols="$(terminal_columns)"; [[ -z "$base" ]] || normalized_base="$(normalize_model_name "$base")"
  LC_ALL=C awk -F'\t' -v term="$cols" -v base="$normalized_base" '
    BEGIN{h1="Model / File";h2="Backend";h3="Type";h4="Status";h5="Size";h6="Rating";h7="Codex";h8="Category";w1=length(h1);w2=length(h2);w3=length(h3);w4=length(h4);w5=length(h5);w6=length(h6);w7=length(h7);w8=length(h8)}
    NF>=9{rows[++n]=$0; if(length($1)>w1)w1=length($1); if(length($8)>w2)w2=length($8); if(length($9)>w3)w3=length($9); if(length($2)>w4)w4=length($2); if(length($3)>w5)w5=length($3); if(length($4)>w6)w6=length($4); if(length($5)>w7)w7=length($5); if(length($6)>w8)w8=length($6)}
    function line(w,s,i){s="";for(i=0;i<w;i++)s=s"-";return s}
    END{
      printf "%-*s  %-*s  %-*s  %-*s  %*s  %*s  %-*s  %-*s\n",w1,h1,w2,h2,w3,h3,w4,h4,w5,h5,w6,h6,w7,h7,w8,h8
      printf "%-*s  %-*s  %-*s  %-*s  %*s  %*s  %-*s  %-*s\n",w1,line(w1),w2,line(w2),w3,line(w3),w4,line(w4),w5,line(w5),w6,line(w6),w7,line(w7),w8,line(w8)
      for(r=1;r<=n;r++){split(rows[r],a,"\t");printf "%-*s  %-*s  %-*s  %-*s  %*s  %*s  %-*s  %-*s\n",w1,a[1],w2,a[8],w3,a[9],w4,a[2],w5,a[3],w6,a[4],w7,a[5],w8,a[6]}
    }' "$file"
  printf '\n%b\n' "${DIM}Draw Things Type: Model = runnable checkpoint; LoRA = adapter; Dependency = support weights; Metadata = support/config file.${RESET}"
  printf '%b\n' "${DIM}A matching -tensordata companion is included in the parent row size and is not listed twice.${RESET}"
  printf '\n%b%s%b\n' "$BOLD" "Disk usage: $(local_models_storage_summary)" "$RESET"
}

prepare_local_combined_menu_data() {
  local input="$1" output="$2" header_file="$3" content_width="$4" base_model="${5:-}"
  ((content_width>=78)) || content_width=78
  LC_ALL=C awk -F'\t' -v output="$output" -v header_file="$header_file" -v maxwidth="$content_width" -v base="$base_model" '
    function clip(s,w){if(length(s)<=w)return s;if(w<=3)return substr(s,1,w);return substr(s,1,w-3)"..."}
    BEGIN{h[1]="Model / File";h[2]="Backend";h[3]="Type";h[4]="Status";h[5]="Size";h[6]="Rating";h[7]="Codex";h[8]="Category";for(i=1;i<=8;i++)w[i]=length(h[i])}
    NF>=9{rows[++n]=$0;vals[1]=$1;vals[2]=$8;vals[3]=$9;vals[4]=$2;vals[5]=$3;vals[6]=$4;vals[7]=$5;vals[8]=$6;for(i=1;i<=8;i++)if(length(vals[i])>w[i])w[i]=length(vals[i])}
    END{sep=14;fixed=w[2]+w[3]+w[4]+w[5]+w[6]+w[7]+w[8]+sep;avail=maxwidth-fixed;if(avail<18)avail=18;if(w[1]>avail)w[1]=avail;header=sprintf("%-*s  %-*s  %-*s  %-*s  %*s  %*s  %-*s  %-*s",w[1],h[1],w[2],h[2],w[3],h[3],w[4],h[4],w[5],h[5],w[6],h[6],w[7],h[7],w[8],h[8]);print header > header_file;for(r=1;r<=n;r++){split(rows[r],a,"\t");display=sprintf("%-*s  %-*s  %-*s  %-*s  %*s  %*s  %-*s  %-*s",w[1],clip(a[1],w[1]),w[2],a[8],w[3],a[9],w[4],a[2],w[5],a[3],w[6],a[4],w[7],a[5],w[8],a[6]);printf "%06d\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n",r,a[1],a[2],a[3],a[4],a[5],a[6],a[7],a[8],a[9],display > output}}
  ' "$input"
}

tui_local_combined_row_by_id() {
  LC_ALL=C awk -F'\t' -v id="$2" 'BEGIN{OFS="\t"}$1==id{print $2,$3,$4,$5,$6,$7,$8,$9,$10;exit}' "$1"
}

tui_show_model_details() {
  local row="$1" model status size rating codex category description backend asset_type tmp path
  IFS=$'\t' read -r model status size rating codex category description backend asset_type <<< "$row"
  tmp="$(mktemp -t ai-model-details.XXXXXX)"
  path=""
  if [[ "$backend" == "Draw Things" ]]; then
    path="$(draw_things_models_dir)/$model"
    [[ -f "$path" ]] || [[ -f "${path}-tensordata" ]] && path="${path}-tensordata"
  fi
  cat > "$tmp" <<EOF
Model / File: $model
Backend:      ${backend:-Ollama}
Type:         ${asset_type:-Model}
Status:       $status
Size:         $size
Rating:       $rating
Codex:        $codex
Category:     $category
${path:+Path:         $path}

Description:
$description
EOF
  tui_show_text_file "Model Details" "$tmp"; rm -f "$tmp"
}

tui_reveal_draw_things_asset() {
  local name="$1" path
  path="$(draw_things_models_dir)/$name"
  [[ -f "$path" ]] || { [[ -f "${path}-tensordata" ]] && path="${path}-tensordata"; }
  [[ -e "$path" ]] || { tui_show_message "Draw Things asset" "File not found: $path"; return 0; }
  if [[ "$(uname -s 2>/dev/null || true)" == Darwin && -x /usr/bin/open ]]; then
    /usr/bin/open -R "$path" >/dev/null 2>&1 || tui_show_message "Draw Things asset" "$path"
  else
    tui_show_message "Draw Things asset" "$path"
  fi
}

tui_local_model_options() {
  local row="$1" model status size rating codex category description backend asset_type choice
  local -a items
  IFS=$'\t' read -r model status size rating codex category description backend asset_type <<< "$row"; [[ -n "$backend" ]] || backend=Ollama; [[ -n "$asset_type" ]] || asset_type=Model
  if [[ "$backend" == "Draw Things" ]]; then
    if [[ "$asset_type" != "Model" ]]; then
      while true; do
        items=( "Details" "Show information about this Draw Things asset" "Reveal" "Reveal the file in Finder" )
        if ! choice="$(tui_capture_dialog --title "Local Model Options" --cancel-label "Back" --menu "File: $model\nBackend: Draw Things   Type: $asset_type   Size: $size" 0 0 10 "${items[@]}")"; then return 0; fi
        case "$choice" in Details)tui_show_model_details "$row";; Reveal)tui_reveal_draw_things_asset "$model";; esac
      done
    fi
    while true; do
      items=( "Image" "Open Image Generation with this model" "Reveal" "Reveal the model file in Finder" "Uninstall" "Remove this Draw Things model" )
      if ! choice="$(tui_capture_dialog --title "Local Model Options" --cancel-label "Back" --menu "Model: $model\nBackend: Draw Things   Type: Model   Size: $size   Rating: $rating   Category: $category" 0 0 10 "${items[@]}")"; then return 0; fi
      case "$choice" in Image)tui_image_view "$model";; Reveal)tui_reveal_draw_things_asset "$model";; Uninstall)if tui_confirm "Uninstall model" "Remove $model? Dependency/support files are kept and will remain visible in Local Models."; then tui_run_terminal "Uninstall Draw Things model" uninstall_draw_things_model "$model"; return 10; fi;; esac
    done
  fi
  while true; do
    if model_is_running "$model"; then status=running; else status=stopped; fi
    items=( "Agent" "Open Codex Options with this model selected" "Chat" "Open Chat Options with this model selected" "Run" "Load this model into memory" "Stop" "Stop this model" "Set as default" "Use this model as the default/base model" "Uninstall" "Stop and remove this model" )
    if ! choice="$(tui_capture_dialog --title "Local Model Options" --cancel-label "Back" --menu "Model: $model\nBackend: Ollama   Status: $status   Size: $size   Rating: $rating   Codex: $codex" 0 0 12 "${items[@]}")"; then return 0; fi
    case "$choice" in Agent)tui_agent_view "$model";; Chat)tui_chat_view "$model";; Run)tui_run_captured "Run model: $model" run_model "$model" "";; Stop)model_is_running "$model" && tui_run_captured "Stop model: $model" stop_model "$model" || tui_show_message "Stop model" "$model is already stopped.";; "Set as default")tui_run_captured "Set default model" set_base_model "$model"; return 11;; Uninstall)if tui_confirm "Uninstall model" "Remove $model?"; then tui_run_terminal "Uninstall model" uninstall_model "$model"; return 10; fi;; esac
  done
}

tui_local_models_view() {
  local order="status:desc|rating:desc|size:asc|model:asc|codex:desc|category:asc" selected_model="" rows data header rc result status output id row sort_result action_status sorted_rows base_model
  local screen_cols screen_rows dialog_width dialog_height menu_height content_width default_id header_text storage_summary=""
  local refresh_needed=1 layout_needed=1 last_content_width=0
  local -a items
  rc="$(tui_local_model_dialog_rc)"; rows="$(mktemp -t ai-local-rows.XXXXXX)"; data="$(mktemp -t ai-local-data.XXXXXX)"; header="$(mktemp -t ai-local-header.XXXXXX)"
  while true; do
    screen_cols="$(terminal_columns)";screen_rows="$(terminal_lines)";dialog_width=$((screen_cols-4));dialog_height=$((screen_rows-4));((dialog_width>=90))||dialog_width=90;((dialog_height>=16))||dialog_height=16;menu_height=$((dialog_height-8));((menu_height>=6))||menu_height=6;content_width=$((dialog_width-10))
    if ((refresh_needed==1)); then : > "$rows";collect_combined_local_model_rows "$rows" "$order";if [[ ! -s "$rows" ]];then rm -f "$rows" "$data" "$header" "$rc";tui_show_message "Local Models" "No local models or Draw Things assets are installed.";return 0;fi;base_model="$(get_base_model)";storage_summary="$(local_models_storage_summary)";refresh_needed=0;layout_needed=1;fi
    if ((layout_needed==1 || last_content_width!=content_width));then :>"$data";:>"$header";prepare_local_combined_menu_data "$rows" "$data" "$header" "$content_width" "$base_model";last_content_width=$content_width;layout_needed=0;fi
    header_text="Disk usage: $storage_summary\n\n$(cat "$header")";items=();default_id="";while IFS=$'\t' read -r id model st sz rt cx cat desc backend asset_type display;do [[ -n "$id" ]]||continue;items+=( "$id" "$display" );[[ -n "$selected_model" && "$model" == "$selected_model" ]]&&default_id="$id";done < "$data";[[ -n "$default_id" ]]||default_id=000001
    items+=( "__STOP_ALL__" "< Stop All Ollama Models >" )
    result="$(tui_model_dialog_capture "$rc" --title "Local Models" --default-item "$default_id" --no-tags --no-hot-list --scrollbar --cr-wrap --ok-label "Options" --cancel-label "Sort" --extra-button --extra-label "Details" --help-button --help-label "Back" --help-tags --hline "Up/Down Navigate   Enter Options   F1 Details   F2 Sort   Esc Back" --menu "$header_text" "$dialog_height" "$dialog_width" "$menu_height" "${items[@]}")";status="${result%%|*}";output="${result#*|}"
    case "$status" in
      0)id="$output";if [[ "$id" == __STOP_ALL__ ]];then tui_confirm "Stop all models" "Stop every Ollama model?"&&tui_run_captured "Stop all models" stop_all_models;refresh_needed=1;continue;fi;row="$(tui_local_combined_row_by_id "$data" "$id")";if [[ -n "$row" ]];then selected_model="${row%%$'\t'*}";if tui_local_model_options "$row";then action_status=0;else action_status=$?;fi;refresh_needed=1;fi;;
      3)id="$output";[[ "$id" == __STOP_ALL__ ]]&&continue;row="$(tui_local_combined_row_by_id "$data" "$id")";[[ -z "$row" ]]||tui_show_model_details "$row";;
      1)if sort_result="$(tui_model_sort_menu "$order")";then order="$sort_result";sorted_rows="$(mktemp -t ai-local-sorted.XXXXXX)";sort_model_rows "$rows" "$sorted_rows" "$order" per-field&&mv "$sorted_rows" "$rows"||rm -f "$sorted_rows";layout_needed=1;fi;;
      2|255|-1)rm -f "$rows" "$data" "$header" "$rc";return 0;;
    esac
  done
}


# -----------------------------------------------------------------------------
# 1.11.7 overrides: richer sorting + Draw Things dependency relationships
# -----------------------------------------------------------------------------

DRAW_THINGS_DEPENDENCY_CACHE="$CACHE_DIR/draw-things-dependencies-v1.tsv"
DRAW_THINGS_DEPENDENCY_REGISTRY="$CONFIG_DIR/draw-things-dependencies.tsv"

normalize_tui_sort_spec() {
  local raw="${1:-}" token key direction normalized=""
  local -a tokens
  [[ -n "$raw" ]] || raw="status:desc|rating:desc|size:asc|model:asc|codex:asc|category:asc"
  IFS='|' read -r -a tokens <<< "$raw"
  for token in "${tokens[@]}"; do
    key="${token%%:*}"
    direction="${token#*:}"
    case "$key" in
      model|status|size|rating|codex|category|backend|type|filter) ;;
      *) die "Internal error: unsupported TUI sort field: $key" ;;
    esac
    if [[ "$token" != *:* ]]; then
      if [[ "$key" == rating ]]; then direction=desc; else direction=asc; fi
    fi
    [[ "$direction" == asc || "$direction" == desc ]] || die "Internal error: unsupported TUI sort direction: $direction"
    case "|$normalized|" in
      *"|$key:"*) ;;
      *) if [[ -n "$normalized" ]]; then normalized="${normalized}|${key}:${direction}"; else normalized="${key}:${direction}"; fi ;;
    esac
  done
  printf '%s\n' "$normalized"
}

tui_sort_field_description() {
  case "$1" in
    model)    printf '%s\n' "Model / file name" ;;
    status)   printf '%s\n' "Lifecycle state" ;;
    size)     printf '%s\n' "Model / asset size" ;;
    rating)   printf '%s\n' "Hardware Rating percentage" ;;
    codex)    printf '%s\n' "Codex compatibility, then coding quality" ;;
    category) printf '%s\n' "Model category" ;;
    backend)  printf '%s\n' "Ollama or Draw Things" ;;
    type)     printf '%s\n' "Model, LoRA, Dependency, Metadata" ;;
    filter)   printf '%s\n' "Draw Things content-filter classification" ;;
    *)        printf '%s\n' "" ;;
  esac
}

# Field 8 is backend in Local Models and filter in the Draw Things catalog.
# Field 9 is the Local Models asset type. Both aliases are intentional.
sort_model_rows() {
  local input="$1" output="$2" order_spec="$3" direction_override="$4"
  local enriched tab token key token_direction direction spec has_model=0
  local -a keys sort_args
  enriched="$(mktemp "${TMPDIR:-/tmp}/ai-sort.XXXXXX")"; tab="$(printf '\t')"
  LC_ALL=C awk -F '\t' 'BEGIN{OFS="\t"} NF>=7 {
    backend=(NF>=8?$8:""); asset_type=(NF>=9?$9:"")
    status_rank=0
    if($2=="available") status_rank=1; else if($2=="stopped"||$2=="Stopped"||$2=="installed"||$2=="Installed") status_rank=2; else if($2=="running"||$2=="Running") status_rank=3; else if($2=="base") status_rank=4; else if($2=="base/run") status_rank=5
    size_num=$3; gsub(/[^0-9.]/,"",size_num); if(size_num=="") size_num=0
    rating_num=$4; gsub(/[^0-9.]/,"",rating_num); if(rating_num=="") rating_num=-1
    codex_rank=0; if($5=="Unknown")codex_rank=1; else if($5=="Limited")codex_rank=2; else if($5=="General")codex_rank=3; else if($5=="Good")codex_rank=4; else if($5=="Very good")codex_rank=5; else if($5=="Excellent")codex_rank=6
    print $1,$2,$3,$4,$5,$6,$7,backend,asset_type,status_rank,size_num,rating_num,codex_rank
  }' "$input" > "$enriched"
  IFS='|' read -r -a keys <<< "$order_spec"; sort_args=( -s -t "$tab" )
  for token in "${keys[@]}"; do
    key="${token%%:*}"; token_direction=""; [[ "$token" == *:* ]] && token_direction="${token#*:}"
    if [[ "$direction_override" == per-field ]]; then
      direction="$token_direction"; [[ "$direction" == asc || "$direction" == desc ]] || { [[ "$key" == rating ]] && direction=desc || direction=asc; }
    else
      direction="$direction_override"; [[ "$direction" != auto ]] || { [[ "$key" == rating ]] && direction=desc || direction=asc; }
    fi
    case "$key" in
      model) spec="1,1"; has_model=1 ;;
      status) spec="10,10n" ;;
      size) spec="11,11n" ;;
      rating) spec="12,12n" ;;
      codex) spec="13,13n" ;;
      category) spec="6,6" ;;
      description) spec="7,7" ;;
      backend|filter) spec="8,8" ;;
      type) spec="9,9" ;;
      *) rm -f "$enriched"; die "Internal error: unsupported sort field: $key" ;;
    esac
    [[ "$direction" != desc ]] || spec="${spec}r"
    sort_args+=( "-k${spec}" )
  done
  (( has_model == 1 )) || sort_args+=( "-k1,1" )
  LC_ALL=C sort "${sort_args[@]}" "$enriched" | cut -f1-9 > "$output" || { rm -f "$enriched"; return 1; }
  rm -f "$enriched"
}

draw_things_dependency_cache_fresh() {
  local now mtime age
  [[ -s "$DRAW_THINGS_DEPENDENCY_CACHE" ]] || return 1
  [[ "$DRAW_THINGS_CATALOG_TTL" =~ ^[0-9]+$ ]] || return 1
  now="$(date +%s)"; mtime="$(file_mtime "$DRAW_THINGS_DEPENDENCY_CACHE")"
  [[ "$mtime" =~ ^[0-9]+$ ]] || return 1
  age=$((now - mtime)); (( age >= 0 && age < DRAW_THINGS_CATALOG_TTL ))
}

draw_things_dependency_catalog_refresh() {
  local models tmp
  command -v curl >/dev/null 2>&1 || return 1
  command -v node >/dev/null 2>&1 || return 1
  mkdir -p "$CACHE_DIR"
  models="$(mktemp -t ai-dt-deps-json.XXXXXX)"; tmp="$(mktemp -t ai-dt-deps.XXXXXX)"
  if ! curl -fsSL --connect-timeout 3 --max-time 10 "$DRAW_THINGS_MODELS_URL" -o "$models"; then rm -f "$models" "$tmp"; return 1; fi
  if ! node - "$models" > "$tmp" <<'NODEDEPS'
const fs=require('fs');
let models=[]; try{models=JSON.parse(fs.readFileSync(process.argv[2],'utf8'))}catch(_){process.exit(1)}
const basename=v=>String(v).split(/[?#]/)[0].split('/').pop();
const isWeight=v=>/\.(?:ckpt|safetensors)$/i.test(String(v).split(/[?#]/)[0]);
function collect(v,out){
  if(typeof v==='string'){ if(isWeight(v)) out.add(basename(v)); return; }
  if(Array.isArray(v)){ for(const x of v) collect(x,out); return; }
  if(v && typeof v==='object'){ for(const [k,x] of Object.entries(v)) if(k!=='file') collect(x,out); }
}
const rows=[];
for(const m of (Array.isArray(models)?models:[])){
  if(!m || !m.file) continue;
  const model=basename(m.file); const deps=new Set();
  for(const [k,v] of Object.entries(m)) if(k!=='file') collect(v,deps);
  for(const dep of deps) if(dep && dep!==model) rows.push(model+'\t'+dep);
}
rows.sort(); let last=''; for(const r of rows){if(r!==last)console.log(r);last=r;}
NODEDEPS
  then rm -f "$models" "$tmp"; return 1; fi
  mv "$tmp" "$DRAW_THINGS_DEPENDENCY_CACHE"; rm -f "$models"; return 0
}

draw_things_dependency_catalog_pairs() {
  if ! draw_things_dependency_cache_fresh; then draw_things_dependency_catalog_refresh >/dev/null 2>&1 || true; fi
  [[ -s "$DRAW_THINGS_DEPENDENCY_CACHE" ]] && cat "$DRAW_THINGS_DEPENDENCY_CACHE" || true
}

draw_things_dependency_registry_add() {
  local model="$1" dep="$2" tmp
  [[ -n "$model" && -n "$dep" && "$model" != "$dep" ]] || return 0
  mkdir -p "$CONFIG_DIR"; touch "$DRAW_THINGS_DEPENDENCY_REGISTRY"
  if awk -F '\t' -v m="$model" -v d="$dep" '$1==m&&$2==d{found=1}END{exit !found}' "$DRAW_THINGS_DEPENDENCY_REGISTRY" 2>/dev/null; then return 0; fi
  printf '%s\t%s\n' "$model" "$dep" >> "$DRAW_THINGS_DEPENDENCY_REGISTRY"
  tmp="$(mktemp -t ai-dt-dep-reg.XXXXXX)"; LC_ALL=C sort -u "$DRAW_THINGS_DEPENDENCY_REGISTRY" > "$tmp"; mv "$tmp" "$DRAW_THINGS_DEPENDENCY_REGISTRY"
}

draw_things_dependency_registry_remove_model() {
  local model="$1" tmp
  [[ -f "$DRAW_THINGS_DEPENDENCY_REGISTRY" ]] || return 0
  tmp="$(mktemp -t ai-dt-dep-reg.XXXXXX)"
  awk -F '\t' -v m="$model" '$1!=m' "$DRAW_THINGS_DEPENDENCY_REGISTRY" > "$tmp"
  mv "$tmp" "$DRAW_THINGS_DEPENDENCY_REGISTRY"
}

draw_things_local_custom_dependency_pairs() {
  local dir json
  dir="$(draw_things_models_dir)"
  command -v node >/dev/null 2>&1 || return 0
  for json in "$dir/custom.json" "$dir/models.json"; do
    [[ -s "$json" ]] || continue
    node - "$json" <<'NODECUSTOM' 2>/dev/null || true
const fs=require('fs'); let root; try{root=JSON.parse(fs.readFileSync(process.argv[2],'utf8'))}catch(_){process.exit(0)}
const basename=v=>String(v).split(/[?#]/)[0].split('/').pop();
const isWeight=v=>/\.(?:ckpt|safetensors)$/i.test(String(v).split(/[?#]/)[0]);
function refs(v,out,skipFile){
 if(typeof v==='string'){if(isWeight(v))out.add(basename(v));return}
 if(Array.isArray(v)){for(const x of v)refs(x,out,skipFile);return}
 if(v&&typeof v==='object'){for(const [k,x] of Object.entries(v))if(!(skipFile&&k==='file'))refs(x,out,false)}
}
function walk(v){
 if(Array.isArray(v)){for(const x of v)walk(x);return}
 if(!v||typeof v!=='object')return;
 if(typeof v.file==='string'&&isWeight(v.file)){
   const model=basename(v.file), deps=new Set();
   for(const [k,x] of Object.entries(v))if(k!=='file')refs(x,deps,false);
   for(const d of deps)if(d&&d!==model)console.log(model+'\t'+d);
 }
 for(const x of Object.values(v))walk(x);
}
walk(root);
NODECUSTOM
  done
}

draw_things_dependency_pairs() {
  { draw_things_dependency_catalog_pairs; [[ -s "$DRAW_THINGS_DEPENDENCY_REGISTRY" ]] && cat "$DRAW_THINGS_DEPENDENCY_REGISTRY" || true; draw_things_local_custom_dependency_pairs; } | LC_ALL=C sort -u
}

draw_things_installed_model_file() {
  local output="$1"
  draw_things_downloaded_models 2>/dev/null | cut -d'|' -f1 | awk 'NF&&!seen[$0]++' > "$output" || : > "$output"
}

draw_things_model_dependencies_all() {
  local model="$1"
  draw_things_dependency_pairs | awk -F '\t' -v m="$model" '$1==m&&$2!=""&&!seen[$2]++{print $2}'
}

draw_things_model_dependencies_installed() {
  local model="$1" dir dep
  dir="$(draw_things_models_dir)"
  while IFS= read -r dep; do
    [[ -n "$dep" ]] || continue
    if [[ -f "$dir/$dep" || -f "$dir/$dep-tensordata" ]]; then printf '%s\n' "$dep"; fi
  done < <(draw_things_model_dependencies_all "$model")
}

draw_things_dependency_users() {
  local dep="$1" installed pairs model
  installed="$(mktemp -t ai-dt-installed.XXXXXX)"; pairs="$(mktemp -t ai-dt-pairs.XXXXXX)"
  draw_things_installed_model_file "$installed"; draw_things_dependency_pairs > "$pairs"
  awk -F '\t' -v d="$dep" '$2==d&&$1!=""&&!seen[$1]++{print $1}' "$pairs" | while IFS= read -r model; do
    [[ -n "$model" ]] || continue
    grep -Fqx -- "$model" "$installed" 2>/dev/null && printf '%s\n' "$model"
  done
  rm -f "$installed" "$pairs"
}

draw_things_record_model_dependencies() {
  local model="$1" before_file="$2" after_file="$3" dir dep new_file
  dir="$(draw_things_models_dir)"
  while IFS= read -r dep; do
    [[ -n "$dep" ]] || continue
    if [[ -f "$dir/$dep" || -f "$dir/$dep-tensordata" ]]; then draw_things_dependency_registry_add "$model" "$dep"; fi
  done < <(draw_things_model_dependencies_all "$model")
  if [[ -s "$after_file" ]]; then
    while IFS= read -r new_file; do
      [[ -n "$new_file" ]] || continue
      [[ "$new_file" == "$model" || "$new_file" == "$model-tensordata" || "$new_file" == *-tensordata ]] && continue
      case "$new_file" in *.ckpt|*.CKPT|*.safetensors|*.SAFETENSORS) draw_things_dependency_registry_add "$model" "$new_file" ;; esac
    done < <(comm -13 "$before_file" "$after_file" 2>/dev/null || true)
  fi
}

draw_things_snapshot_files() {
  local dir="$1" output="$2" f tmp
  : > "$output"
  [[ -d "$dir" ]] || return 0
  for f in "$dir"/*; do [[ -f "$f" ]] && printf '%s\n' "${f##*/}" >> "$output"; done
  tmp="$(mktemp -t ai-dt-snapshot.XXXXXX)"; LC_ALL=C sort -u "$output" > "$tmp"; mv "$tmp" "$output"
}

install_draw_things_model() {
  local model="$1" name="${2:-$1}" cli dir before after status
  cli="$(ensure_draw_things_cli)"; dir="$(draw_things_models_dir)"; mkdir -p "$dir"
  before="$(mktemp -t ai-dt-before.XXXXXX)"; after="$(mktemp -t ai-dt-after.XXXXXX)"
  draw_things_snapshot_files "$dir" "$before"
  info "Downloading Draw Things model: $name"
  set +e; "$cli" models ensure --models-dir "$dir" --model "$model"; status=$?; set -e
  if (( status != 0 )); then rm -f "$before" "$after"; return "$status"; fi
  draw_things_snapshot_files "$dir" "$after"
  draw_things_registry_add "$model" "$name"
  draw_things_record_model_dependencies "$model" "$before" "$after"
  rm -f "$before" "$after"
  success "Draw Things model installed: $name"
}

uninstall_draw_things_model() {
  local model="$1" dir
  dir="$(draw_things_models_dir)"
  rm -f "$dir/$model" "$dir/$model-tensordata"
  draw_things_registry_remove "$model"
  draw_things_dependency_registry_remove_model "$model"
  success "Draw Things model removed: $model"
}

draw_things_delete_dependency() {
  local dep="$1" dir
  dir="$(draw_things_models_dir)"
  rm -f "$dir/$dep" "$dir/$dep-tensordata"
  success "Draw Things dependency removed: $dep"
}

draw_things_execute_removal_plan() {
  local models_blob="$1" deps_blob="$2" item
  while IFS= read -r item; do [[ -n "$item" ]] && uninstall_draw_things_model "$item"; done <<< "$models_blob"
  while IFS= read -r item; do [[ -n "$item" ]] && draw_things_delete_dependency "$item"; done <<< "$deps_blob"
}

draw_things_dependency_size_label() {
  local dep="$1" dir bytes gb
  dir="$(draw_things_models_dir)"; bytes="$(draw_things_asset_bytes "$dir/$dep")"; gb="$(bytes_to_gb "$bytes")"; format_size_gb "$gb"
}

draw_things_other_users() {
  local dep="$1" exclude="$2" model
  while IFS= read -r model; do [[ -n "$model" && "$model" != "$exclude" ]] && printf '%s\n' "$model"; done < <(draw_things_dependency_users "$dep")
}

tui_dependency_shared_action() {
  local dep="$1" users="$2" choice list
  list="$(printf '%s\n' "$users" | sed '/^$/d;s/^/  - /')"
  if choice="$(tui_capture_dialog --title "Shared Dependency Warning" --cancel-label "Cancel" --menu "Dependency:\n$dep\n\nIt is also used by these installed models:\n$list\n\nChoose what to do:" 0 0 12 \
      "Keep" "Keep this dependency installed" \
      "Remove Dependency" "Delete it anyway; the listed models may stop working" \
      "Remove Dependency + Models" "Delete it and uninstall the listed models too")"; then
    case "$choice" in
      Keep) printf 'keep\n' ;;
      "Remove Dependency") printf 'remove\n' ;;
      "Remove Dependency + Models") printf 'remove-models\n' ;;
    esac
    return 0
  fi
  return 1
}

tui_uninstall_draw_things_dependency() {
  local dep="$1" users action models_blob="" prompt
  users="$(draw_things_dependency_users "$dep" || true)"
  if [[ -n "$users" ]]; then
    if ! action="$(tui_dependency_shared_action "$dep" "$users")"; then return 1; fi
    case "$action" in
      keep) return 1 ;;
      remove) ;;
      remove-models) models_blob="$users" ;;
    esac
  else
    tui_confirm "Remove dependency" "Remove dependency $dep?\n\nNo installed model is currently known to use it." || return 1
  fi
  prompt="Remove dependency $dep?"
  [[ -z "$models_blob" ]] || prompt="$prompt\n\nThe following models will also be uninstalled:\n$(printf '%s\n' "$models_blob" | sed 's/^/  - /')"
  tui_confirm "Confirm removal" "$prompt" || return 1
  tui_run_terminal "Remove Draw Things dependency" draw_things_execute_removal_plan "$models_blob" "$dep"
  return 0
}

tui_uninstall_draw_things_model() {
  local model="$1" dep size users other action selection="" models_blob="" deps_blob="" summary local_count extra_model
  local -a items
  models_blob="$model"
  items=()
  while IFS= read -r dep; do
    [[ -n "$dep" ]] || continue
    size="$(draw_things_dependency_size_label "$dep")"; users="$(draw_things_dependency_users "$dep" || true)"
    if [[ -n "$users" ]]; then
      local_count="$(printf '%s\n' "$users" | awk 'NF{n++}END{print n+0}')"
      if (( local_count > 1 )); then items+=( "$dep" "$size | shared by $local_count installed models" off ); else items+=( "$dep" "$size | used by this model" off ); fi
    else
      items+=( "$dep" "$size | known dependency" off )
    fi
  done < <(draw_things_model_dependencies_installed "$model")

  if (( ${#items[@]} > 0 )); then
    if ! selection="$(tui_capture_dialog --title "Uninstall Draw Things Model" --ok-label "Continue" --cancel-label "Back" --separate-output --checklist \
        "Model: $model\n\nSelect any dependencies you also want to remove. Shared dependencies are OFF by default." 0 0 12 "${items[@]}")"; then return 1; fi
  fi

  while IFS= read -r dep; do
    [[ -n "$dep" ]] || continue
    other="$(draw_things_other_users "$dep" "$model" || true)"
    if [[ -n "$other" ]]; then
      if ! action="$(tui_dependency_shared_action "$dep" "$other")"; then return 1; fi
      case "$action" in
        keep) continue ;;
        remove) deps_blob="${deps_blob}${deps_blob:+$'\n'}${dep}" ;;
        remove-models)
          deps_blob="${deps_blob}${deps_blob:+$'\n'}${dep}"
          while IFS= read -r extra_model; do
            [[ -n "$extra_model" ]] || continue
            if ! printf '%s\n' "$models_blob" | grep -Fqx -- "$extra_model"; then models_blob="${models_blob}${models_blob:+$'\n'}${extra_model}"; fi
          done <<< "$other"
          ;;
      esac
    else
      deps_blob="${deps_blob}${deps_blob:+$'\n'}${dep}"
    fi
  done <<< "$selection"

  summary="Remove model:\n  - $model"
  if [[ "$(printf '%s\n' "$models_blob" | awk 'NF{n++}END{print n+0}')" -gt 1 ]]; then
    summary="$summary\n\nAdditional models to remove:\n$(printf '%s\n' "$models_blob" | awk -v first="$model" '$0!=""&&$0!=first{print "  - "$0}')"
  fi
  if [[ -n "$deps_blob" ]]; then summary="$summary\n\nDependencies to remove:\n$(printf '%s\n' "$deps_blob" | sed 's/^/  - /')"; else summary="$summary\n\nDependencies will be kept."; fi
  tui_confirm "Confirm uninstall" "$summary" || return 1
  tui_run_terminal "Uninstall Draw Things" draw_things_execute_removal_plan "$models_blob" "$deps_blob"
  return 0
}

tui_show_model_details() {
  local row="$1" model status size rating codex category description backend asset_type tmp path dep users usage size_label installed_flag deps_list
  IFS=$'\t' read -r model status size rating codex category description backend asset_type <<< "$row"
  tmp="$(mktemp -t ai-model-details.XXXXXX)"; path=""
  if [[ "$backend" == "Draw Things" ]]; then
    path="$(draw_things_models_dir)/$model"; [[ -f "$path" ]] || { [[ -f "${path}-tensordata" ]] && path="${path}-tensordata"; }
  fi
  cat > "$tmp" <<EOFDETAIL
Model / File: $model
Backend:      ${backend:-Ollama}
Type:         ${asset_type:-Model}
Status:       $status
Size:         $size
Rating:       $rating
Codex:        $codex
Category:     $category
${path:+Path:         $path}

Description:
$description
EOFDETAIL
  if [[ "$backend" == "Draw Things" && "$asset_type" == Model ]]; then
    printf '\nDependencies:\n' >> "$tmp"
    deps_list="$(draw_things_model_dependencies_all "$model" || true)"
    if [[ -n "$deps_list" ]]; then
      while IFS= read -r dep; do
        [[ -n "$dep" ]] || continue
        if [[ -f "$(draw_things_models_dir)/$dep" || -f "$(draw_things_models_dir)/$dep-tensordata" ]]; then installed_flag="installed"; size_label="$(draw_things_dependency_size_label "$dep")"; else installed_flag="missing"; size_label="-"; fi
        users="$(draw_things_dependency_users "$dep" || true)"; usage="$(printf '%s\n' "$users" | awk 'NF{n++}END{print n+0}')"
        printf '  - %s [%s, %s, used by %s installed model(s)]\n' "$dep" "$installed_flag" "$size_label" "$usage" >> "$tmp"
      done <<< "$deps_list"
    else
      printf '  (No dependency relationship is known for this model.)\n' >> "$tmp"
    fi
  elif [[ "$backend" == "Draw Things" && "$asset_type" == Dependency ]]; then
    printf '\nUsed by installed models:\n' >> "$tmp"
    users="$(draw_things_dependency_users "$model" || true)"
    if [[ -n "$users" ]]; then printf '%s\n' "$users" | sed 's/^/  - /' >> "$tmp"; else printf '  (No installed model is currently known to use this dependency.)\n' >> "$tmp"; fi
  fi
  tui_show_text_file "Model Details" "$tmp"; rm -f "$tmp"
}

tui_local_model_options() {
  local row="$1" model status size rating codex category description backend asset_type choice
  local -a items
  IFS=$'\t' read -r model status size rating codex category description backend asset_type <<< "$row"; [[ -n "$backend" ]] || backend=Ollama; [[ -n "$asset_type" ]] || asset_type=Model
  if [[ "$backend" == "Draw Things" ]]; then
    if [[ "$asset_type" != Model ]]; then
      while true; do
        if [[ "$asset_type" == Dependency ]]; then
          items=( "Details" "Show dependency usage and information" "Reveal" "Reveal the file in Finder" "Uninstall" "Remove this dependency" )
        else
          items=( "Details" "Show information about this Draw Things asset" "Reveal" "Reveal the file in Finder" )
        fi
        if ! choice="$(tui_capture_dialog --title "Local Model Options" --cancel-label "Back" --menu "File: $model\nBackend: Draw Things   Type: $asset_type   Size: $size" 0 0 10 "${items[@]}")"; then return 0; fi
        case "$choice" in
          Details) tui_show_model_details "$row" ;;
          Reveal) tui_reveal_draw_things_asset "$model" ;;
          Uninstall) if tui_uninstall_draw_things_dependency "$model"; then return 10; fi ;;
        esac
      done
    fi
    while true; do
      items=( "Image" "Open Image Generation with this model" "Details" "Show dependencies and model information" "Reveal" "Reveal the model file in Finder" "Uninstall" "Remove model and optionally selected dependencies" )
      if ! choice="$(tui_capture_dialog --title "Local Model Options" --cancel-label "Back" --menu "Model: $model\nBackend: Draw Things   Type: Model   Size: $size   Rating: $rating   Category: $category" 0 0 10 "${items[@]}")"; then return 0; fi
      case "$choice" in
        Image) tui_image_view "$model" ;;
        Details) tui_show_model_details "$row" ;;
        Reveal) tui_reveal_draw_things_asset "$model" ;;
        Uninstall) if tui_uninstall_draw_things_model "$model"; then return 10; fi ;;
      esac
    done
  fi
  while true; do
    if model_is_running "$model"; then status=running; else status=stopped; fi
    items=( "Agent" "Open Codex Options with this model selected" "Chat" "Open Chat Options with this model selected" "Run" "Load this model into memory" "Stop" "Stop this model" "Set as default" "Use this model as the default/base model" "Uninstall" "Stop and remove this model" )
    if ! choice="$(tui_capture_dialog --title "Local Model Options" --cancel-label "Back" --menu "Model: $model\nBackend: Ollama   Status: $status   Size: $size   Rating: $rating   Codex: $codex" 0 0 12 "${items[@]}")"; then return 0; fi
    case "$choice" in Agent)tui_agent_view "$model";; Chat)tui_chat_view "$model";; Run)tui_run_captured "Run model: $model" run_model "$model" "";; Stop)model_is_running "$model" && tui_run_captured "Stop model: $model" stop_model "$model" || tui_show_message "Stop model" "$model is already stopped.";; "Set as default")tui_run_captured "Set default model" set_base_model "$model"; return 11;; Uninstall)if tui_confirm "Uninstall model" "Remove $model?"; then tui_run_terminal "Uninstall model" uninstall_model "$model"; return 10; fi;; esac
  done
}

tui_draw_things_models_view() {
  local order="rating:desc|filter:asc|size:asc|model:asc|category:asc" selected_model="" rows data header rc result status output id row sort_result sorted_rows
  local screen_cols screen_rows dialog_width dialog_height menu_height content_width default_id header_text refresh_needed=1 layout_needed=1 last_content_width=0 description model_name
  local -a items
  ensure_draw_things_cli >/dev/null
  rc="$(tui_model_dialog_rc)";rows="$(mktemp -t ai-dt-tui-rows.XXXXXX)";data="$(mktemp -t ai-dt-tui-data.XXXXXX)";header="$(mktemp -t ai-dt-tui-header.XXXXXX)"
  while true;do
    screen_cols="$(terminal_columns)";screen_rows="$(terminal_lines)";dialog_width=$((screen_cols-4));dialog_height=$((screen_rows-4));((dialog_width>=76))||dialog_width=76;((dialog_height>=16))||dialog_height=16;menu_height=$((dialog_height-8));((menu_height>=6))||menu_height=6;content_width=$((dialog_width-10))
    if ((refresh_needed==1));then tui_dialog --title "Install Draw Things Models" --infobox "Loading Draw Things online catalog..." 5 66||true;:>"$rows";collect_draw_things_model_rows "$rows" "$order" per-field 1;if [[ ! -s "$rows" ]];then rm -f "$rows" "$data" "$header" "$rc";tui_show_message "Install Draw Things Models" "No installable Draw Things models could be loaded.";return 0;fi;refresh_needed=0;layout_needed=1;fi
    if ((layout_needed==1||last_content_width!=content_width));then :>"$data";:>"$header";tui_prepare_draw_things_model_menu_data "$rows" "$data" "$header" "$content_width";last_content_width=$content_width;layout_needed=0;fi
    header_text="$(cat "$header")";items=();default_id=""
    while IFS=$'\t' read -r id model st sz rt cx cat desc filter display;do [[ -n "$id" ]]||continue;items+=( "$id" "$display" );[[ -n "$selected_model"&&"$model"=="$selected_model" ]]&&default_id="$id";done < "$data"
    [[ -n "$default_id" ]]||default_id=000001
    result="$(tui_model_dialog_capture "$rc" --title "Install Draw Things Models" --default-item "$default_id" --no-tags --no-hot-list --scrollbar --cr-wrap --ok-label "Install" --cancel-label "Sort" --extra-button --extra-label "Details" --help-button --help-label "Back" --help-tags --hline "Up/Down Navigate   Enter Install   F1 Details   F2 Sort   Esc Back" --menu "$header_text" "$dialog_height" "$dialog_width" "$menu_height" "${items[@]}")";status="${result%%|*}";output="${result#*|}"
    case "$status" in
      0) id="$output";row="$(tui_draw_things_row_by_id "$data" "$id")";if [[ -n "$row" ]];then selected_model="${row%%$'\t'*}";description="$(printf '%s' "$row"|awk -F'\t' '{print $7}')";model_name="${description%% \[*}";if tui_confirm "Install Draw Things model" "Install $model_name?\n\nModel file: $selected_model";then tui_run_terminal "Install Draw Things model" install_draw_things_model "$selected_model" "$model_name";refresh_needed=1;fi;fi ;;
      3) id="$output";row="$(tui_draw_things_row_by_id "$data" "$id")";[[ -z "$row" ]]||tui_show_draw_things_model_details "$row" ;;
      1) if sort_result="$(tui_model_sort_menu "$order")";then order="$sort_result";sorted_rows="$(mktemp -t ai-dt-sorted.XXXXXX)";sort_model_rows "$rows" "$sorted_rows" "$order" per-field&&mv "$sorted_rows" "$rows"||rm -f "$sorted_rows";layout_needed=1;fi ;;
      2|255|-1) rm -f "$rows" "$data" "$header" "$rc";return 0 ;;
    esac
  done
}

tui_local_models_view() {
  local order="status:desc|backend:asc|type:asc|rating:desc|size:asc|model:asc|codex:desc|category:asc" selected_model="" rows data header rc result status output id row sort_result action_status sorted_rows base_model
  local screen_cols screen_rows dialog_width dialog_height menu_height content_width default_id header_text storage_summary=""
  local refresh_needed=1 layout_needed=1 last_content_width=0
  local -a items
  rc="$(tui_local_model_dialog_rc)"; rows="$(mktemp -t ai-local-rows.XXXXXX)"; data="$(mktemp -t ai-local-data.XXXXXX)"; header="$(mktemp -t ai-local-header.XXXXXX)"
  while true; do
    screen_cols="$(terminal_columns)";screen_rows="$(terminal_lines)";dialog_width=$((screen_cols-4));dialog_height=$((screen_rows-4));((dialog_width>=90))||dialog_width=90;((dialog_height>=16))||dialog_height=16;menu_height=$((dialog_height-8));((menu_height>=6))||menu_height=6;content_width=$((dialog_width-10))
    if ((refresh_needed==1)); then : > "$rows";collect_combined_local_model_rows "$rows" "$order";if [[ ! -s "$rows" ]];then rm -f "$rows" "$data" "$header" "$rc";tui_show_message "Local Models" "No local models or Draw Things assets are installed.";return 0;fi;base_model="$(get_base_model)";storage_summary="$(local_models_storage_summary)";refresh_needed=0;layout_needed=1;fi
    if ((layout_needed==1 || last_content_width!=content_width));then :>"$data";:>"$header";prepare_local_combined_menu_data "$rows" "$data" "$header" "$content_width" "$base_model";last_content_width=$content_width;layout_needed=0;fi
    header_text="Disk usage: $storage_summary\n\n$(cat "$header")";items=();default_id="";while IFS=$'\t' read -r id model st sz rt cx cat desc backend asset_type display;do [[ -n "$id" ]]||continue;items+=( "$id" "$display" );[[ -n "$selected_model" && "$model" == "$selected_model" ]]&&default_id="$id";done < "$data";[[ -n "$default_id" ]]||default_id=000001
    items+=( "__STOP_ALL__" "< Stop All Ollama Models >" )
    result="$(tui_model_dialog_capture "$rc" --title "Local Models" --default-item "$default_id" --no-tags --no-hot-list --scrollbar --cr-wrap --ok-label "Options" --cancel-label "Sort" --extra-button --extra-label "Details" --help-button --help-label "Back" --help-tags --hline "Up/Down Navigate   Enter Options   F1 Details   F2 Sort   Esc Back" --menu "$header_text" "$dialog_height" "$dialog_width" "$menu_height" "${items[@]}")";status="${result%%|*}";output="${result#*|}"
    case "$status" in
      0)id="$output";if [[ "$id" == __STOP_ALL__ ]];then tui_confirm "Stop all models" "Stop every Ollama model?"&&tui_run_captured "Stop all models" stop_all_models;refresh_needed=1;continue;fi;row="$(tui_local_combined_row_by_id "$data" "$id")";if [[ -n "$row" ]];then selected_model="${row%%$'\t'*}";if tui_local_model_options "$row";then action_status=0;else action_status=$?;fi;refresh_needed=1;fi ;;
      3)id="$output";[[ "$id" == __STOP_ALL__ ]]&&continue;row="$(tui_local_combined_row_by_id "$data" "$id")";[[ -z "$row" ]]||tui_show_model_details "$row" ;;
      1)if sort_result="$(tui_model_sort_menu "$order")";then order="$sort_result";sorted_rows="$(mktemp -t ai-local-sorted.XXXXXX)";sort_model_rows "$rows" "$sorted_rows" "$order" per-field&&mv "$sorted_rows" "$rows"||rm -f "$sorted_rows";layout_needed=1;fi ;;
      2|255|-1)rm -f "$rows" "$data" "$header" "$rc";return 0 ;;
    esac
  done
}


# -----------------------------------------------------------------------------
# 1.11.8 override: make ASC/DESC symmetric for every sortable model column.
# Distinct displayed values must never collapse onto the same hidden sort rank.
# -----------------------------------------------------------------------------
sort_model_rows() {
  local input="$1" output="$2" order_spec="$3" direction_override="$4"
  local enriched tab token key token_direction direction suffix has_model=0
  local -a keys sort_args
  enriched="$(mktemp "${TMPDIR:-/tmp}/ai-sort.XXXXXX")"
  tab="$(printf '\t')"

  LC_ALL=C awk -F '\t' 'BEGIN{OFS="\t"}
    function lower(s) { return tolower(s) }
    function size_gb(s, n,u) {
      if (s=="" || s=="-" || toupper(s)=="N/A") return -1
      n=s
      gsub(/[^0-9.]/,"",n)
      if (n=="") return -1
      u=toupper(s)
      gsub(/^[[:space:]]*[0-9.]+[[:space:]]*/,"",u)
      gsub(/[[:space:]]/,"",u)
      if (u=="TB" || u=="TIB") return n*1024
      if (u=="GB" || u=="GIB" || u=="") return n+0
      if (u=="MB" || u=="MIB") return n/1024
      if (u=="KB" || u=="KIB") return n/1048576
      if (u=="B" || u=="BYTES") return n/1073741824
      return n+0
    }
    function status_rank(s) {
      s=lower(s)
      if (s=="available") return 1
      if (s=="installed") return 2
      if (s=="stopped") return 3
      if (s=="running") return 4
      if (s=="base") return 5
      if (s=="base/run") return 6
      return 100
    }
    function codex_rank(s) {
      s=lower(s)
      if (s=="n/a" || s=="-") return 0
      if (s=="no") return 1
      if (s=="unknown") return 2
      if (s=="limited") return 3
      if (s=="general") return 4
      if (s=="good") return 5
      if (s=="very good") return 6
      if (s=="excellent") return 7
      return 100
    }
    NF>=7 {
      backend=(NF>=8?$8:"")
      asset_type=(NF>=9?$9:"")
      sr=status_rank($2)
      sg=sprintf("%.12f",size_gb($3))
      rn=$4
      gsub(/[^0-9.]/,"",rn)
      if (rn=="") rn=-1
      cr=codex_rank($5)
      print $1,$2,$3,$4,$5,$6,$7,backend,asset_type, \
            sr,sg,rn,cr,lower($2),lower($5),lower($1),lower($6),lower(backend),lower(asset_type),lower($7)
    }
  ' "$input" > "$enriched"

  IFS='|' read -r -a keys <<< "$order_spec"
  sort_args=( -s -t "$tab" )

  for token in "${keys[@]}"; do
    key="${token%%:*}"
    token_direction=""
    [[ "$token" == *:* ]] && token_direction="${token#*:}"

    if [[ "$direction_override" == per-field ]]; then
      direction="$token_direction"
      if [[ "$direction" != asc && "$direction" != desc ]]; then
        if [[ "$key" == rating ]]; then direction=desc; else direction=asc; fi
      fi
    else
      direction="$direction_override"
      if [[ "$direction" == auto ]]; then
        if [[ "$key" == rating ]]; then direction=desc; else direction=asc; fi
      fi
    fi
    [[ "$direction" == asc || "$direction" == desc ]] || { rm -f "$enriched"; die "Internal error: unsupported sort direction: $direction"; }
    if [[ "$direction" == desc ]]; then suffix="r"; else suffix=""; fi

    case "$key" in
      model)
        sort_args+=( "-k16,16${suffix}" "-k1,1${suffix}" )
        has_model=1
        ;;
      status)
        sort_args+=( "-k10,10n${suffix}" "-k14,14${suffix}" "-k2,2${suffix}" )
        ;;
      size)
        sort_args+=( "-k11,11n${suffix}" "-k3,3${suffix}" )
        ;;
      rating)
        sort_args+=( "-k12,12n${suffix}" "-k4,4${suffix}" )
        ;;
      codex)
        sort_args+=( "-k13,13n${suffix}" "-k15,15${suffix}" "-k5,5${suffix}" )
        ;;
      category)
        sort_args+=( "-k17,17${suffix}" "-k6,6${suffix}" )
        ;;
      description)
        sort_args+=( "-k20,20${suffix}" "-k7,7${suffix}" )
        ;;
      backend|filter)
        sort_args+=( "-k18,18${suffix}" "-k8,8${suffix}" )
        ;;
      type)
        sort_args+=( "-k19,19${suffix}" "-k9,9${suffix}" )
        ;;
      *)
        rm -f "$enriched"
        die "Internal error: unsupported sort field: $key"
        ;;
    esac
  done

  # Stable deterministic tie-breaker. Explicit model sorting keeps its own direction;
  # otherwise equal values fall back to model name ascending, as before.
  (( has_model == 1 )) || sort_args+=( "-k16,16" "-k1,1" )

  LC_ALL=C sort "${sort_args[@]}" "$enriched" | cut -f1-9 > "$output" || { rm -f "$enriched"; return 1; }
  rm -f "$enriched"
}


# -----------------------------------------------------------------------------
# 1.11.10 override: preserve the highlighted item when returning to model lists.
# F1 (Details) and F2 (Sort) both return the highlighted tag. A successful
# install/uninstall intentionally clears the selection so the refreshed list
# starts at the top.
# -----------------------------------------------------------------------------

tui_model_dialog_rc() {
  local rc
  rc="$(mktemp -t ai-tui-dialogrc.XXXXXX)"
  if [[ -n "${DIALOGRC:-}" ]] && [[ -r "$DIALOGRC" ]]; then
    cp "$DIALOGRC" "$rc"
  elif [[ -r "$HOME/.dialogrc" ]]; then
    cp "$HOME/.dialogrc" "$rc"
  else
    rm -f "$rc"
    dialog --create-rc "$rc" >/dev/null 2>&1 || : > "$rc"
  fi
  cat >> "$rc" <<'DIALOG_KEYS'

# ai model-browser shortcuts
bindkey menubox F1 EXTRA
bindkey menu F1 EXTRA
bindkey menubox F2 HELP
bindkey menu F2 HELP
DIALOG_KEYS
  printf '%s\n' "$rc"
}

tui_local_model_dialog_rc() {
  local rc
  rc="$(mktemp -t ai-tui-local-dialogrc.XXXXXX)"
  if [[ -n "${DIALOGRC:-}" ]] && [[ -r "$DIALOGRC" ]]; then
    cp "$DIALOGRC" "$rc"
  elif [[ -r "$HOME/.dialogrc" ]]; then
    cp "$HOME/.dialogrc" "$rc"
  else
    rm -f "$rc"
    dialog --create-rc "$rc" >/dev/null 2>&1 || : > "$rc"
  fi
  cat >> "$rc" <<'DIALOG_KEYS'

# ai local-model browser shortcuts
bindkey menubox F1 EXTRA
bindkey menu F1 EXTRA
bindkey menubox F2 HELP
bindkey menu F2 HELP
DIALOG_KEYS
  printf '%s\n' "$rc"
}

tui_dialog_help_tag() {
  local value="$1"
  case "$value" in
    "HELP "*) value="${value#HELP }" ;;
    HELP*) value="${value#HELP}"; value="${value# }" ;;
  esac
  case "$value" in
    \"*\") value="${value#\"}"; value="${value%\"}" ;;
  esac
  printf '%s\n' "$value"
}

tui_local_row_selection_key() {
  local row="$1" model status size rating codex category description backend asset_type
  IFS=$'\t' read -r model status size rating codex category description backend asset_type <<< "$row"
  printf '%s|%s|%s\n' "$backend" "$asset_type" "$model"
}

# Keep tui_run_terminal's historical return value (0), but expose the command's
# actual exit status so callers can distinguish a successful mutation from a
# failed one without changing older call sites.
TUI_LAST_COMMAND_STATUS=0

tui_run_terminal() {
  local title="$1"
  shift
  local status
  tui_restore_terminal_mode
  tui_clear_terminal
  printf '%b\n\n' "${BOLD}${BRIGHT_CYAN}$title${RESET}"
  set +e
  ( "$@" )
  status=$?
  set -e
  TUI_LAST_COMMAND_STATUS="$status"
  tui_restore_terminal_mode
  if (( status != 0 )); then
    printf '\n%b\n' "${RED}Command exited with status $status.${RESET}"
  fi
  tui_pause_terminal
  return 0
}

tui_uninstall_draw_things_dependency() {
  local dep="$1" users action models_blob="" prompt
  users="$(draw_things_dependency_users "$dep" || true)"
  if [[ -n "$users" ]]; then
    if ! action="$(tui_dependency_shared_action "$dep" "$users")"; then return 1; fi
    case "$action" in
      keep) return 1 ;;
      remove) ;;
      remove-models) models_blob="$users" ;;
    esac
  else
    tui_confirm "Remove dependency" "Remove dependency $dep?\n\nNo installed model is currently known to use it." || return 1
  fi
  prompt="Remove dependency $dep?"
  [[ -z "$models_blob" ]] || prompt="$prompt\n\nThe following models will also be uninstalled:\n$(printf '%s\n' "$models_blob" | sed 's/^/  - /')"
  tui_confirm "Confirm removal" "$prompt" || return 1
  tui_run_terminal "Remove Draw Things dependency" draw_things_execute_removal_plan "$models_blob" "$dep"
  (( TUI_LAST_COMMAND_STATUS == 0 )) || return 1
  return 0
}

tui_uninstall_draw_things_model() {
  local model="$1" dep size users other action selection="" models_blob="" deps_blob="" summary local_count extra_model
  local -a items
  models_blob="$model"
  items=()
  while IFS= read -r dep; do
    [[ -n "$dep" ]] || continue
    size="$(draw_things_dependency_size_label "$dep")"; users="$(draw_things_dependency_users "$dep" || true)"
    if [[ -n "$users" ]]; then
      local_count="$(printf '%s\n' "$users" | awk 'NF{n++}END{print n+0}')"
      if (( local_count > 1 )); then items+=( "$dep" "$size | shared by $local_count installed models" off ); else items+=( "$dep" "$size | used by this model" off ); fi
    else
      items+=( "$dep" "$size | known dependency" off )
    fi
  done < <(draw_things_model_dependencies_installed "$model")

  if (( ${#items[@]} > 0 )); then
    if ! selection="$(tui_capture_dialog --title "Uninstall Draw Things Model" --ok-label "Continue" --cancel-label "Back" --separate-output --checklist \
        "Model: $model\n\nSelect any dependencies you also want to remove. Shared dependencies are OFF by default." 0 0 12 "${items[@]}")"; then return 1; fi
  fi

  while IFS= read -r dep; do
    [[ -n "$dep" ]] || continue
    other="$(draw_things_other_users "$dep" "$model" || true)"
    if [[ -n "$other" ]]; then
      if ! action="$(tui_dependency_shared_action "$dep" "$other")"; then return 1; fi
      case "$action" in
        keep) continue ;;
        remove) deps_blob="${deps_blob}${deps_blob:+$'\n'}${dep}" ;;
        remove-models)
          deps_blob="${deps_blob}${deps_blob:+$'\n'}${dep}"
          while IFS= read -r extra_model; do
            [[ -n "$extra_model" ]] || continue
            if ! printf '%s\n' "$models_blob" | grep -Fqx -- "$extra_model"; then models_blob="${models_blob}${models_blob:+$'\n'}${extra_model}"; fi
          done <<< "$other"
          ;;
      esac
    else
      deps_blob="${deps_blob}${deps_blob:+$'\n'}${dep}"
    fi
  done <<< "$selection"

  summary="Remove model:\n  - $model"
  if [[ "$(printf '%s\n' "$models_blob" | awk 'NF{n++}END{print n+0}')" -gt 1 ]]; then
    summary="$summary\n\nAdditional models to remove:\n$(printf '%s\n' "$models_blob" | awk -v first="$model" '$0!=""&&$0!=first{print "  - "$0}')"
  fi
  if [[ -n "$deps_blob" ]]; then summary="$summary\n\nDependencies to remove:\n$(printf '%s\n' "$deps_blob" | sed 's/^/  - /')"; else summary="$summary\n\nDependencies will be kept."; fi
  tui_confirm "Confirm uninstall" "$summary" || return 1
  tui_run_terminal "Uninstall Draw Things" draw_things_execute_removal_plan "$models_blob" "$deps_blob"
  (( TUI_LAST_COMMAND_STATUS == 0 )) || return 1
  return 0
}

tui_local_model_options() {
  local row="$1" model status size rating codex category description backend asset_type choice selected_choice
  local -a items menu_args
  IFS=$'\t' read -r model status size rating codex category description backend asset_type <<< "$row"

  if [[ "$backend" == "Draw Things" ]]; then
    if [[ "$asset_type" != Model ]]; then
      selected_choice="Details"
      while true; do
        if [[ "$asset_type" == Dependency ]]; then
          items=( "Details" "Show dependency usage and information" "Reveal" "Reveal the file in Finder" "Uninstall" "Remove this dependency" )
        else
          items=( "Details" "Show information about this Draw Things asset" "Reveal" "Reveal the file in Finder" )
        fi
        if ! choice="$(tui_capture_dialog --title "Local Model Options" --default-item "$selected_choice" --cancel-label "Back" --menu "File: $model\nBackend: Draw Things   Type: $asset_type   Size: $size" 0 0 10 "${items[@]}")"; then return 0; fi
        selected_choice="$choice"
        case "$choice" in
          Details) tui_show_model_details "$row" ;;
          Reveal) tui_reveal_draw_things_asset "$model" ;;
          Uninstall) if tui_uninstall_draw_things_dependency "$model"; then return 10; fi ;;
        esac
      done
    fi
    selected_choice="Image"
    while true; do
      items=( "Image" "Open Image Generation with this model" "Details" "Show dependencies and model information" "Reveal" "Reveal the model file in Finder" "Uninstall" "Remove model and optionally selected dependencies" )
      if ! choice="$(tui_capture_dialog --title "Local Model Options" --default-item "$selected_choice" --cancel-label "Back" --menu "Model: $model\nBackend: Draw Things   Type: Model   Size: $size   Rating: $rating   Category: $category" 0 0 10 "${items[@]}")"; then return 0; fi
      selected_choice="$choice"
      case "$choice" in
        Image) tui_image_view "$model" ;;
        Details) tui_show_model_details "$row" ;;
        Reveal) tui_reveal_draw_things_asset "$model" ;;
        Uninstall) if tui_uninstall_draw_things_model "$model"; then return 10; fi ;;
      esac
    done
  fi

  selected_choice="Agent"
  while true; do
    if model_is_running "$model"; then status=running; else status=stopped; fi
    items=( "Agent" "Open Codex Options with this model selected" "Chat" "Open Chat Options with this model selected" "Run" "Load this model into memory" "Stop" "Stop this model" "Set as default" "Use this model as the default/base model" "Uninstall" "Stop and remove this model" )
    if ! choice="$(tui_capture_dialog --title "Local Model Options" --default-item "$selected_choice" --cancel-label "Back" --menu "Model: $model\nBackend: Ollama   Status: $status   Size: $size   Rating: $rating   Codex: $codex" 0 0 12 "${items[@]}")"; then return 0; fi
    selected_choice="$choice"
    case "$choice" in
      Agent) tui_agent_view "$model" ;;
      Chat) tui_chat_view "$model" ;;
      Run) tui_run_captured "Run model: $model" run_model "$model" "" ;;
      Stop) model_is_running "$model" && tui_run_captured "Stop model: $model" stop_model "$model" || tui_show_message "Stop model" "$model is already stopped." ;;
      "Set as default") tui_run_captured "Set default model" set_base_model "$model"; return 11 ;;
      Uninstall)
        if tui_confirm "Uninstall model" "Remove $model?"; then
          tui_run_terminal "Uninstall model" uninstall_model "$model"
          if (( TUI_LAST_COMMAND_STATUS == 0 )); then return 10; fi
        fi
        ;;
    esac
  done
}

tui_experimental_models_view() {
  local order="rating:desc|size:asc|model:asc|category:asc" selected_model=""
  local rows data header rc result status output id row sort_result sorted_rows
  local hw os arch chip device ram_gb screen_cols screen_rows dialog_width dialog_height menu_height content_width default_id header_text
  local refresh_needed=1 layout_needed=1 last_content_width=0
  local -a items
  rc="$(tui_model_dialog_rc)"
  rows="$(mktemp -t ai-tui-experimental-rows.XXXXXX)"; data="$(mktemp -t ai-tui-experimental-data.XXXXXX)"; header="$(mktemp -t ai-tui-experimental-header.XXXXXX)"
  hw="$(detect_hardware)"; IFS='|' read -r os arch chip device ram_gb <<< "$hw"
  while true; do
    screen_cols="$(terminal_columns)"; screen_rows="$(terminal_lines)"; dialog_width=$((screen_cols-4)); dialog_height=$((screen_rows-4)); ((dialog_width>=72))||dialog_width=72; ((dialog_height>=16))||dialog_height=16; menu_height=$((dialog_height-8)); ((menu_height>=6))||menu_height=6; content_width=$((dialog_width-10))
    if ((refresh_needed==1)); then tui_dialog --title "Experimental Models" --infobox "Loading Experimental Ollama models..." 5 64 || true; :>"$rows"; collect_experimental_model_rows "$rows" "$order" per-field "$ram_gb" 1; if [[ ! -s "$rows" ]]; then rm -f "$rows" "$data" "$header" "$rc"; tui_show_message "Experimental Models" "No installable experimental models could be loaded."; return 0; fi; refresh_needed=0; layout_needed=1; fi
    if ((layout_needed==1 || last_content_width!=content_width)); then :>"$data"; :>"$header"; tui_prepare_experimental_model_menu_data "$rows" "$data" "$header" "$content_width"; last_content_width=$content_width; layout_needed=0; fi
    header_text="$(cat "$header")"; items=(); default_id=""
    while IFS=$'\t' read -r id model st sz rt cx cat desc display; do [[ -n "$id" ]]||continue; items+=( "$id" "$display" ); [[ -n "$selected_model" && "$model" == "$selected_model" ]]&&default_id="$id"; done < "$data"
    [[ -n "$default_id" ]]||default_id=000001
    result="$(tui_model_dialog_capture "$rc" --title "Experimental Models" --default-item "$default_id" --no-tags --no-hot-list --scrollbar --cr-wrap --ok-label "Install" --cancel-label "Back" --extra-button --extra-label "Details" --help-button --help-label "Sort" --help-tags --hline "Up/Down Navigate   Enter Install   F1 Details   F2 Sort   Esc Back" --menu "$header_text" "$dialog_height" "$dialog_width" "$menu_height" "${items[@]}")"; status="${result%%|*}"; output="${result#*|}"
    case "$status" in
      0)
        id="$output"; row="$(tui_model_row_by_id "$data" "$id")"
        if [[ -n "$row" ]]; then selected_model="${row%%$'\t'*}"; if tui_confirm "Install experimental model" "Install $selected_model?"; then tui_run_terminal "Install model: $selected_model" install_model "$selected_model"; if ((TUI_LAST_COMMAND_STATUS==0)); then selected_model=""; fi; refresh_needed=1; fi; fi
        ;;
      3)
        id="$output"; row="$(tui_model_row_by_id "$data" "$id")"; if [[ -n "$row" ]]; then selected_model="${row%%$'\t'*}"; tui_show_experimental_model_details "$row"; fi
        ;;
      2)
        id="$(tui_dialog_help_tag "$output")"; row="$(tui_model_row_by_id "$data" "$id")"; [[ -z "$row" ]]||selected_model="${row%%$'\t'*}"
        if sort_result="$(tui_model_sort_menu "$order")"; then order="$sort_result"; sorted_rows="$(mktemp -t ai-tui-experimental-sorted.XXXXXX)"; sort_model_rows "$rows" "$sorted_rows" "$order" per-field&&mv "$sorted_rows" "$rows"||rm -f "$sorted_rows"; layout_needed=1; dialog --clear >/dev/null 2>&1 || true; fi
        ;;
      1|255|-1) rm -f "$rows" "$data" "$header" "$rc"; return 0 ;;
    esac
  done
}

tui_install_models_view() {
  local order="rating:desc|size:asc|model:asc|codex:desc|category:asc" selected_model=""
  local rows data header rc result status output id row sort_result sorted_rows
  local screen_cols screen_rows dialog_width dialog_height menu_height content_width default_id header_text
  local refresh_needed=1 layout_needed=1 last_content_width=0
  local -a items
  rc="$(tui_model_dialog_rc)"; rows="$(mktemp -t ai-tui-install-rows.XXXXXX)"; data="$(mktemp -t ai-tui-install-data.XXXXXX)"; header="$(mktemp -t ai-tui-install-header.XXXXXX)"
  while true; do
    screen_cols="$(terminal_columns)"; screen_rows="$(terminal_lines)"; dialog_width=$((screen_cols-4)); dialog_height=$((screen_rows-4)); ((dialog_width>=72))||dialog_width=72; ((dialog_height>=16))||dialog_height=16; menu_height=$((dialog_height-8)); ((menu_height>=6))||menu_height=6; content_width=$((dialog_width-10))
    if ((refresh_needed==1)); then tui_dialog --title "Install Models" --infobox "Loading Ollama Library catalog..." 5 64 || true; :>"$rows"; tui_collect_install_model_rows "$rows" "$order"; if [[ ! -s "$rows" ]]; then rm -f "$rows" "$data" "$header" "$rc"; tui_show_message "Install Models" "No installable models could be loaded."; return 0; fi; refresh_needed=0; layout_needed=1; fi
    if ((layout_needed==1 || last_content_width!=content_width)); then :>"$data"; :>"$header"; tui_prepare_install_model_menu_data "$rows" "$data" "$header" "$content_width"; last_content_width=$content_width; layout_needed=0; fi
    header_text="$(cat "$header")"; items=(); default_id=""
    while IFS=$'\t' read -r id model st sz rt cx cat desc display; do [[ -n "$id" ]]||continue; items+=( "$id" "$display" ); [[ -n "$selected_model" && "$model" == "$selected_model" ]]&&default_id="$id"; done < "$data"
    [[ -n "$default_id" ]]||default_id=000001
    result="$(tui_model_dialog_capture "$rc" --title "Install Models" --default-item "$default_id" --no-tags --no-hot-list --scrollbar --cr-wrap --ok-label "Install" --cancel-label "Back" --extra-button --extra-label "Details" --help-button --help-label "Sort" --help-tags --hline "Up/Down Navigate   Enter Install   F1 Details   F2 Sort   Esc Back" --menu "$header_text" "$dialog_height" "$dialog_width" "$menu_height" "${items[@]}")"; status="${result%%|*}"; output="${result#*|}"
    case "$status" in
      0)
        id="$output"; row="$(tui_model_row_by_id "$data" "$id")"
        if [[ -n "$row" ]]; then selected_model="${row%%$'\t'*}"; if tui_confirm "Install model" "Install $selected_model?"; then tui_run_terminal "Install model: $selected_model" install_model "$selected_model"; if ((TUI_LAST_COMMAND_STATUS==0)); then selected_model=""; fi; refresh_needed=1; fi; fi
        ;;
      3)
        id="$output"; row="$(tui_model_row_by_id "$data" "$id")"; if [[ -n "$row" ]]; then selected_model="${row%%$'\t'*}"; tui_show_model_details "$row"; fi
        ;;
      2)
        id="$(tui_dialog_help_tag "$output")"; row="$(tui_model_row_by_id "$data" "$id")"; [[ -z "$row" ]]||selected_model="${row%%$'\t'*}"
        if sort_result="$(tui_model_sort_menu "$order")"; then order="$sort_result"; sorted_rows="$(mktemp -t ai-tui-install-sorted.XXXXXX)"; sort_model_rows "$rows" "$sorted_rows" "$order" per-field&&mv "$sorted_rows" "$rows"||rm -f "$sorted_rows"; layout_needed=1; dialog --clear >/dev/null 2>&1 || true; fi
        ;;
      1|255|-1) rm -f "$rows" "$data" "$header" "$rc"; return 0 ;;
    esac
  done
}

tui_draw_things_models_view() {
  local order="rating:desc|filter:asc|size:asc|model:asc|category:asc" selected_model="" rows data header rc result status output id row sort_result sorted_rows
  local screen_cols screen_rows dialog_width dialog_height menu_height content_width default_id header_text refresh_needed=1 layout_needed=1 last_content_width=0 description model_name
  local -a items
  ensure_draw_things_cli >/dev/null
  rc="$(tui_model_dialog_rc)"; rows="$(mktemp -t ai-dt-tui-rows.XXXXXX)"; data="$(mktemp -t ai-dt-tui-data.XXXXXX)"; header="$(mktemp -t ai-dt-tui-header.XXXXXX)"
  while true; do
    screen_cols="$(terminal_columns)"; screen_rows="$(terminal_lines)"; dialog_width=$((screen_cols-4)); dialog_height=$((screen_rows-4)); ((dialog_width>=76))||dialog_width=76; ((dialog_height>=16))||dialog_height=16; menu_height=$((dialog_height-8)); ((menu_height>=6))||menu_height=6; content_width=$((dialog_width-10))
    if ((refresh_needed==1)); then tui_dialog --title "Install Draw Things Models" --infobox "Loading Draw Things online catalog..." 5 66||true; :>"$rows"; collect_draw_things_model_rows "$rows" "$order" per-field 1; if [[ ! -s "$rows" ]]; then rm -f "$rows" "$data" "$header" "$rc"; tui_show_message "Install Draw Things Models" "No installable Draw Things models could be loaded."; return 0; fi; refresh_needed=0; layout_needed=1; fi
    if ((layout_needed==1 || last_content_width!=content_width)); then :>"$data"; :>"$header"; tui_prepare_draw_things_model_menu_data "$rows" "$data" "$header" "$content_width"; last_content_width=$content_width; layout_needed=0; fi
    header_text="$(cat "$header")"; items=(); default_id=""
    while IFS=$'\t' read -r id model st sz rt cx cat desc filter display; do [[ -n "$id" ]]||continue; items+=( "$id" "$display" ); [[ -n "$selected_model" && "$model" == "$selected_model" ]]&&default_id="$id"; done < "$data"
    [[ -n "$default_id" ]]||default_id=000001
    result="$(tui_model_dialog_capture "$rc" --title "Install Draw Things Models" --default-item "$default_id" --no-tags --no-hot-list --scrollbar --cr-wrap --ok-label "Install" --cancel-label "Back" --extra-button --extra-label "Details" --help-button --help-label "Sort" --help-tags --hline "Up/Down Navigate   Enter Install   F1 Details   F2 Sort   Esc Back" --menu "$header_text" "$dialog_height" "$dialog_width" "$menu_height" "${items[@]}")"; status="${result%%|*}"; output="${result#*|}"
    case "$status" in
      0)
        id="$output"; row="$(tui_draw_things_row_by_id "$data" "$id")"
        if [[ -n "$row" ]]; then selected_model="${row%%$'\t'*}"; description="$(printf '%s' "$row"|awk -F'\t' '{print $7}')"; model_name="${description%% \[*}"; if tui_confirm "Install Draw Things model" "Install $model_name?\n\nModel file: $selected_model"; then tui_run_terminal "Install Draw Things model" install_draw_things_model "$selected_model" "$model_name"; if ((TUI_LAST_COMMAND_STATUS==0)); then selected_model=""; fi; refresh_needed=1; fi; fi
        ;;
      3)
        id="$output"; row="$(tui_draw_things_row_by_id "$data" "$id")"; if [[ -n "$row" ]]; then selected_model="${row%%$'\t'*}"; tui_show_draw_things_model_details "$row"; fi
        ;;
      2)
        id="$(tui_dialog_help_tag "$output")"; row="$(tui_draw_things_row_by_id "$data" "$id")"; [[ -z "$row" ]]||selected_model="${row%%$'\t'*}"
        if sort_result="$(tui_model_sort_menu "$order")"; then order="$sort_result"; sorted_rows="$(mktemp -t ai-dt-sorted.XXXXXX)"; sort_model_rows "$rows" "$sorted_rows" "$order" per-field&&mv "$sorted_rows" "$rows"||rm -f "$sorted_rows"; layout_needed=1; fi
        ;;
      1|255|-1) rm -f "$rows" "$data" "$header" "$rc"; return 0 ;;
    esac
  done
}

tui_local_models_view() {
  local order="status:desc|backend:asc|type:asc|rating:desc|size:asc|model:asc|codex:desc|category:asc" selected_key="" rows data header rc result status output id row sort_result action_status sorted_rows base_model row_key
  local screen_cols screen_rows dialog_width dialog_height menu_height content_width default_id header_text storage_summary=""
  local refresh_needed=1 layout_needed=1 last_content_width=0
  local -a items
  rc="$(tui_local_model_dialog_rc)"; rows="$(mktemp -t ai-local-rows.XXXXXX)"; data="$(mktemp -t ai-local-data.XXXXXX)"; header="$(mktemp -t ai-local-header.XXXXXX)"
  while true; do
    screen_cols="$(terminal_columns)"; screen_rows="$(terminal_lines)"; dialog_width=$((screen_cols-4)); dialog_height=$((screen_rows-4)); ((dialog_width>=90))||dialog_width=90; ((dialog_height>=16))||dialog_height=16; menu_height=$((dialog_height-8)); ((menu_height>=6))||menu_height=6; content_width=$((dialog_width-10))
    if ((refresh_needed==1)); then :>"$rows"; collect_combined_local_model_rows "$rows" "$order"; if [[ ! -s "$rows" ]]; then rm -f "$rows" "$data" "$header" "$rc"; tui_show_message "Local Models" "No local models or Draw Things assets are installed."; return 0; fi; base_model="$(get_base_model)"; storage_summary="$(local_models_storage_summary)"; refresh_needed=0; layout_needed=1; fi
    if ((layout_needed==1 || last_content_width!=content_width)); then :>"$data"; :>"$header"; prepare_local_combined_menu_data "$rows" "$data" "$header" "$content_width" "$base_model"; last_content_width=$content_width; layout_needed=0; fi
    header_text="Disk usage: $storage_summary\n\n$(cat "$header")"; items=(); default_id=""
    while IFS=$'\t' read -r id model st sz rt cx cat desc backend asset_type display; do
      [[ -n "$id" ]]||continue; items+=( "$id" "$display" ); row_key="$backend|$asset_type|$model"; [[ -n "$selected_key" && "$row_key" == "$selected_key" ]]&&default_id="$id"
    done < "$data"
    items+=( "__STOP_ALL__" "< Stop All Ollama Models >" )
    [[ "$selected_key" == "__STOP_ALL__" ]]&&default_id="__STOP_ALL__"
    [[ -n "$default_id" ]]||default_id=000001
    result="$(tui_model_dialog_capture "$rc" --title "Local Models" --default-item "$default_id" --no-tags --no-hot-list --scrollbar --cr-wrap --ok-label "Options" --cancel-label "Back" --extra-button --extra-label "Details" --help-button --help-label "Sort" --help-tags --hline "Up/Down Navigate   Enter Options   F1 Details   F2 Sort   Esc Back" --menu "$header_text" "$dialog_height" "$dialog_width" "$menu_height" "${items[@]}")"; status="${result%%|*}"; output="${result#*|}"
    case "$status" in
      0)
        id="$output"
        if [[ "$id" == __STOP_ALL__ ]]; then selected_key="__STOP_ALL__"; tui_confirm "Stop all models" "Stop every Ollama model?"&&tui_run_captured "Stop all models" stop_all_models; refresh_needed=1; continue; fi
        row="$(tui_local_combined_row_by_id "$data" "$id")"
        if [[ -n "$row" ]]; then
          selected_key="$(tui_local_row_selection_key "$row")"
          if tui_local_model_options "$row"; then action_status=0; else action_status=$?; fi
          if (( action_status == 10 )); then selected_key=""; fi
          refresh_needed=1
        fi
        ;;
      3)
        id="$output"; [[ "$id" == __STOP_ALL__ ]]&&{ selected_key="__STOP_ALL__"; continue; }
        row="$(tui_local_combined_row_by_id "$data" "$id")"; if [[ -n "$row" ]]; then selected_key="$(tui_local_row_selection_key "$row")"; tui_show_model_details "$row"; fi
        ;;
      2)
        id="$(tui_dialog_help_tag "$output")"
        if [[ "$id" == __STOP_ALL__ ]]; then selected_key="__STOP_ALL__"; else row="$(tui_local_combined_row_by_id "$data" "$id")"; [[ -z "$row" ]]||selected_key="$(tui_local_row_selection_key "$row")"; fi
        if sort_result="$(tui_model_sort_menu "$order")"; then order="$sort_result"; sorted_rows="$(mktemp -t ai-local-sorted.XXXXXX)"; sort_model_rows "$rows" "$sorted_rows" "$order" per-field&&mv "$sorted_rows" "$rows"||rm -f "$sorted_rows"; layout_needed=1; fi
        ;;
      1|255|-1) rm -f "$rows" "$data" "$header" "$rc"; return 0 ;;
    esac
  done
}

main "$@"
