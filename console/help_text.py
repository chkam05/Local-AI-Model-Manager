from ai_models_manager.config import APP_NAME, DEFAULT_CONTEXT_LENGTH


def build_help_text() -> str:
    """Return the complete help for the argument-driven console interface."""
    return f"""USAGE:

  Global options:
    {APP_NAME} [--verbose] COMMAND [ARGUMENTS]

  General purpose:
    {APP_NAME} --agent [MODEL] [--directory|-d [DIR]] [--session|-s [NAME]]
             [--input-file|-i [FILE]]... [--context-length|-l [VALUE]]
             [--exec [ask|auto|no-ask]]
    {APP_NAME} --chat [MODEL] [--session|-s [NAME]] [--input-file|-i [FILE]]...
             [--context-length|-l [VALUE]]
    {APP_NAME} --image [MODEL] --prompt|-p [PROMPT] [--width|-w [PX]]
             [--height|-h [PX]] [--output-dir|-o [DIR]] [--file-name|-n [NAME]]
             [--input-file|-i [FILE]]... [--strength [0..1]]
    {APP_NAME} --run [MODEL] [--context-length|-l [VALUE]]
    {APP_NAME} --stop [MODEL]
    {APP_NAME} --stop-all
    {APP_NAME} --help
    {APP_NAME} --version

  Sessions and tools:
    {APP_NAME} --session [SESSION] [--delete|-d]
    {APP_NAME} --session [SESSION] --rename|-r [NEW_NAME]
    {APP_NAME} --tools
    {APP_NAME} --tool [TOOL] --enable|-e|--disable|-d

  Model management:
    {APP_NAME} --details [MODEL]
    {APP_NAME} --install [MODEL] [--backend|-b [auto|ollama|draw-things]]
    {APP_NAME} --install --source|-s [SOURCE]
             [--backend|-b [auto|ollama|draw-things]]
             [--type|-t [auto|model|lora]]
    {APP_NAME} --models [local|ollama|ollama-experimental|draw-things]
             [--order|-o [FIELD[,FIELD...]]] [--asc|--desc]
             [--dependencies|-d]
    {APP_NAME} --models-refresh
    {APP_NAME} --set-base [MODEL]
    {APP_NAME} --uninstall [MODEL] [--dependencies|-d [keep|unused|all]]
    {APP_NAME} --update-model [MODEL]

  Administration:
    {APP_NAME} --setup [ollama|npm|codex|dialog|draw-things-cli|imagemagick]
    {APP_NAME} --update [ollama|npm|codex|dialog|draw-things-cli|imagemagick]
    {APP_NAME} --purge [ollama|models|ollama-models|npm|codex|dialog|
                       draw-things-cli|draw-things-models|'*']
    {APP_NAME} --clear-cache

COMMANDS:

Global options:
  --verbose
      Writes diagnostic information to stderr: sanitized external commands,
      working directories, timeouts, cache decisions, process exit codes,
      execution times and captured stderr. It does not change command results.
      The option may be placed before or after the command name.

General purpose:
  --agent [MODEL]
      Starts Codex CLI as a local coding agent using an installed Ollama model.
      When MODEL is omitted, the configured base model is used.

      Options:
        --directory, -d [DIR]
            Codex workspace. A missing directory is created. Without this option,
            a temporary workspace is used and removed after an unnamed session.
        --session, -s [NAME]
            Resumes the named Agent session or creates it when it does not exist.
            Session metadata, attachments and the native Codex rollout are stored
            below ~/.config/ai/sessions. Without this option the session is temporary.
        --input-file, -i [FILE]
            Adds a bootstrap attachment. Repeat for multiple files.
        --context-length, -l [VALUE]
            Context used when the model must be loaded. Default: {DEFAULT_CONTEXT_LENGTH}.
        --exec [ask|auto|no-ask]
            Controls Codex approval requests. It does not widen the sandbox.

      Examples:
        {APP_NAME} --agent qwen3.5:4b -d ~/Projects/site -l 16K
        {APP_NAME} --agent -s site-refactor --exec ask

  --chat [MODEL]
      Opens an interactive Ollama chat. Type /bye or press Ctrl+D to exit.
      A named session restores its complete saved message context. It is updated
      after every successful response. Without --session, history and temporary
      attachments are discarded when the chat ends.

      Options:
        --session, -s [NAME]            Resume or create a durable chat session.
        --input-file, -i [FILE]         Attach context or an image; repeatable.
        --context-length, -l [VALUE]    Context length; default: {DEFAULT_CONTEXT_LENGTH}.

  --image [MODEL]
      Generates a PNG with Draw Things or a compatible Ollama image model.
      When MODEL is omitted, a compatible installed model is selected.

      Options:
        --prompt, -p [PROMPT]           Required generation prompt.
        --width, -w [PX]                Width; default: 800.
        --height, -h [PX]               Height; default: 600.
        --output-dir, -o [DIR]          Target directory; default: current directory.
        --file-name, -n [NAME]          Output file name; .png is added if needed.
        --input-file, -i [FILE]         Input/reference image; repeatable.
        --strength [0..1]               Img2img strength; default with input: 0.35.

      Draw Things dimensions are adjusted to multiples of 64 when necessary.

  --run [MODEL]
      Loads an Ollama model and keeps it in memory (keep_alive=-1). This does not
      open a chat. Without MODEL, the base model is used.

      --context-length, -l [VALUE] accepts a token count, K or M suffix.
      Examples: 16384, 16K, 1M. Default: {DEFAULT_CONTEXT_LENGTH}.

  --stop [MODEL]
      Unloads one model. Without MODEL, the configured base model is used.

  --stop-all
      Unloads every model currently returned by ollama ps.

  --version
      Shows component versions, available updates, installed sizes and combined
      Ollama/Draw Things model storage usage.

Sessions and tools:
  --session [SESSION]
      Without SESSION, lists all saved Chat and Agent sessions.
      --delete, -d removes a named session package.
      --rename, -r [NEW_NAME] renames a named session.

  --tools
      Lists Codex tools and their persistent state from ~/.config/ai/tools.json.

  --tool [TOOL] --enable|-e|--disable|-d
      Enables or disables a managed Codex tool. Available tools are shown by
      --tools. Tool selection applies to Agent sessions started by this program.

Model management:
  --details [MODEL]
      Shows complete details for an installed Ollama model or Draw Things file.
      The output includes backend, type, state, size, ratings, category, full
      description and capabilities: tools, vision and image generation.
      Draw Things files also include their full local path. Model details list
      known dependencies; dependency details list installed models using them.

  --install [MODEL]
      Installs a catalog model. .ckpt and .safetensors names are routed to Draw
      Things; other names default to Ollama. --backend overrides auto-detection.

  --install --source|-s [SOURCE]
      Imports an HTTP(S) URL or local file. Ollama accepts Hugging Face repository
      URLs and GGUF files. Draw Things accepts CKPT/SafeTensors models and LoRAs.
      Use --type lora when automatic source classification is insufficient.

      Examples:
        {APP_NAME} --install qwen3.5:4b
        {APP_NAME} --install realvisxl_v4.0_q6p_q8p.ckpt
        {APP_NAME} --install -s https://example.com/model.gguf
        {APP_NAME} --install -s ~/Downloads/style.safetensors -b draw-things -t lora

  --models [TARGET]
      TARGET defaults to local:
        local                 Installed Ollama and Draw Things assets.
        ollama                Published Ollama Library models.
        ollama-experimental   Experimental Ollama models.
        draw-things           Published Draw Things catalog.

      Local State is Running/Stopped only for Ollama. Draw Things uses N/A.
      Draw Things Type can be Model, LoRA, Dependency or Metadata. Filter is
      displayed only for Draw Things. Description is the only trimmed column.

      --dependencies, -d
          Includes Draw Things Dependency and Metadata rows. They are hidden
          by default to keep model lists concise. Models and LoRAs are always
          displayed; this option does not affect Ollama rows.

      --order, -o accepts: model, backend, type, state/status, size, rating,
      codex, filter, category and description. Availability depends on TARGET.
      Multiple fields are comma-separated. Append < for descending order
      (Z -> A, 9 -> 0) or > for ascending order (A -> Z, 0 -> 9). Because the
      shell treats these characters as redirection operators, quote the value:

        {APP_NAME} --models -o 'backend<,type<,rating<,size>'

      A field without a marker follows global --asc or --desc; without either
      global switch, ascending order is used. Explicit field markers take
      precedence over the global switch.

  --models-refresh
      Forces a refresh of the Ollama, Ollama Experimental and Draw Things
      catalogs. When a source is unavailable, its previous cached catalog is
      retained and reported as the fallback.

  --set-base [MODEL]
      Sets an already installed Ollama model as the default for run, stop, chat
      and agent commands.

  --uninstall [MODEL]
      Removes an Ollama model or Draw Things asset. Removing the current base
      Ollama model also clears the base-model setting. Unused registered Draw
      Things dependencies are removed; shared dependencies are preserved by
      the default mode.

      --dependencies, -d keep removes only the model. `unused` (default) also
      removes dependencies without other installed users. `all` removes all
      known dependencies, including shared ones. Passing a dependency itself
      to --uninstall removes that dependency directly.

  --update-model [MODEL]
      Updates one installed model after interactive y/N confirmation. Ollama
      models are refreshed with pull. Draw Things models can be updated when
      they have a matching entry in the model catalog.

Administration:
  --setup [COMPONENT]
      Installs or updates Ollama, npm, Codex CLI, dialog, Draw Things CLI and
      ImageMagick. When COMPONENT is provided, processes only that component.
      Automatic setup supports macOS and Linux; Draw Things CLI installation is
      automatic on macOS only.

  --update [COMPONENT]
      Updates one component, or the complete toolchain when COMPONENT is omitted.
      Components: ollama, npm, codex, dialog, draw-things-cli, imagemagick.

  --purge [COMPONENT]
      Destructive removal requiring interactive confirmation with y.
      AI_PURGE_FORCE=1 permits deliberate non-interactive use.

        no component          Ollama and all Ollama models.
        ollama               Ollama, preserving model data.
        models               All Ollama models; alias: ollama-models.
        npm                  npm CLI, preserving Node.js.
        codex                Codex CLI.
        dialog               dialog.
        draw-things-cli      Draw Things CLI.
        draw-things-models   Draw Things model data.
        '*'                  Complete managed toolchain and model data.

      Quote '*' so that the shell does not expand it.

  --clear-cache
      Deletes disposable Ollama and Draw Things catalog cache files. Settings,
      sessions and installed models are preserved.

CONFIGURATION:
  Settings:       ~/.config/ai/settings.json
  Tool settings:  ~/.config/ai/tools.json
  Sessions:       ~/.config/ai/sessions
  Cache:          ${{XDG_CACHE_HOME:-~/.cache}}/ai

  Environment variables:
    AI_OLLAMA_URL                 Local Ollama API URL.
    OLLAMA_MODELS                 Override the Ollama model storage directory.
    AI_LIBRARY_CACHE_TTL          Ollama catalog cache lifetime in seconds.
    AI_DRAW_THINGS_CACHE_TTL      Draw Things catalog cache lifetime.
    DRAWTHINGS_MODELS_DIR         Override Draw Things Models directory.
    AI_HW_OS / AI_HW_ARCH         Override detected system/architecture.
    AI_HW_CHIP / AI_HW_MODEL      Override detected CPU/SoC and device.
    AI_HW_RAM_GB                  Override detected memory in GB.
    AI_PURGE_FORCE=1              Skip interactive purge confirmation.
    NO_COLOR                      Disable ANSI colors.
"""
