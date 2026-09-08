# AI Model Manager

[English](README.md) | **Polski**

AI Model Manager to konsolowa aplikacja do zarządzania lokalnymi modelami AI,
rozmowami, agentami programistycznymi i generowaniem obrazów. Obsługuje zarówno
klasyczne polecenia CLI, jak i interfejs terminalowy oparty na `dialog`.

Aktualna wersja: **2.0.0**  
Autor: **Copyright (c) Kamil Karpiński**

## Możliwości

- uruchamianie rozmów z lokalnymi modelami Ollama;
- uruchamianie Codex CLI jako lokalnego agenta;
- trwałe sesje Chat i Agent z możliwością wznowienia kontekstu;
- generowanie i modyfikowanie obrazów przez Draw Things;
- przeglądanie modeli lokalnych oraz katalogów modeli;
- instalowanie, aktualizowanie i usuwanie modeli;
- obsługa modeli, LoRA, zależności i plików metadanych Draw Things;
- instalowanie, aktualizowanie i usuwanie komponentów aplikacji;
- interfejs TUI uruchamiany bez argumentów;
- sortowanie, filtrowanie i wyświetlanie szczegółów modeli;
- kolorowy output oraz diagnostyka `--verbose`.

## Wymagania

Do uruchomienia aplikacji wymagane są:

- macOS lub Linux;
- Python 3.10 lub nowszy;
- powłoka zgodna z POSIX `sh`.

Projekt korzysta obecnie wyłącznie ze standardowej biblioteki Pythona i nie
wymaga dodatkowych pakietów instalowanych przez `pip`. Jeżeli w przyszłości w
katalogu projektu pojawi się `requirements.txt`, launcher automatycznie sprawdzi
obecność wymienionych w nim pakietów i wypisze brakujące elementy.

Pozostałe komponenty są potrzebne tylko dla odpowiadających im funkcji:

| Komponent | Zastosowanie |
| --- | --- |
| Ollama | modele tekstowe, Chat, Agent i zarządzanie modelami Ollama |
| Codex CLI | tryb `--agent` |
| Draw Things CLI | generowanie obrazów i modele Draw Things |
| `dialog` | terminalowy interfejs użytkownika |
| ImageMagick | łączenie wielu obrazów wejściowych |
| npm | instalacja i aktualizacja Codex CLI |

Brakujące komponenty można zainstalować poleceniem `--setup`.

## Uruchomienie

Nadaj launcherowi prawo wykonywania, jeśli nie zostało zachowane po pobraniu:

```sh
chmod +x ai
```

Następnie uruchom aplikację w katalogu projektu:

```sh
./ai
```

Bez argumentów otwierany jest interfejs TUI. Polecenia CLI można wykonywać na
przykład tak:

```sh
./ai --help
./ai --version
./ai --models
```

Nazwa katalogu głównego projektu jest dowolna. Launcher korzysta z
`_bootstrap.py`, który rejestruje katalog aplikacji pod jej stabilną, wewnętrzną
nazwą `ai_models_manager`.

### Dodanie polecenia `ai` do PATH

Najprościej dodać katalog projektu do zmiennej `PATH`. Przykład dla `zsh`:

```sh
echo 'export PATH="/pełna/ścieżka/do/Local_AI_Model_Manager:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Od tej chwili aplikację można uruchamiać z dowolnego katalogu:

```sh
ai --version
```

Launcher przed każdym startem sprawdza wersję Pythona oraz wymagania aplikacji.
Po zakończeniu — również po błędzie lub `Ctrl+C` — usuwa należące do projektu
katalogi `__pycache__` i skompilowane pliki `.pyc`/`.pyo`.

## Podstawowe użycie

### TUI

```sh
ai
```

Główne menu udostępnia Agent, Chat, Image Generation, Models, Help, System oraz
Version. Operacje uruchamiające zewnętrzne programy tymczasowo opuszczają
`dialog`, pokazują standardowy output terminala, a po zakończeniu wracają do TUI.

### Chat

```sh
ai --chat [MODEL]
ai --chat [MODEL] --session|-s [NAME]
ai --chat [MODEL] --input-file|-i [FILE]
ai --chat [MODEL] --context-length|-l [VALUE]
```

Przykłady:

```sh
ai --chat qwen3:4b
ai --chat qwen3:4b --session projekt
ai --chat qwen3:4b -s projekt -i README.md -l 16K
```

Sesja podana przez `--session` jest tworzona, jeżeli jeszcze nie istnieje.
Historia wiadomości i załączniki są zapisywane po każdej udanej odpowiedzi.
Bez `--session` rozmowa jest tymczasowa i po zamknięciu traci kontekst.

### Agent

```sh
ai --agent [MODEL] [--directory|-d [DIR]] [--session|-s [NAME]]
                  [--input-file|-i [FILE]]...
                  [--context-length|-l [VALUE]]
                  [--exec [ask|auto|no-ask]]
```

Przykład:

```sh
ai --agent qwen3.5:4b -d ~/Projects/example -s refactor --exec ask
```

Agent korzysta z Codex CLI połączonego z lokalnym endpointem Ollama. Nazwana
sesja zachowuje metadane, załączniki i natywny rollout Codex.

### Generowanie obrazów

```sh
ai --image [MODEL] --prompt|-p [PROMPT]
                   [--width|-w [PX]] [--height|-h [PX]]
                   [--output-dir|-o [DIR]] [--file-name|-n [NAME]]
                   [--input-file|-i [FILE]]... [--strength [0..1]]
```

Przykłady:

```sh
ai --image model.ckpt -p "Cat on a fence at sunset" -w 1024 -h 768
ai --image model.ckpt -p "Black formal outfit, preserve the face" \
   -i input.png --strength 0.35 -o ~/Pictures
```

Domyślny rozmiar to `800x600`. Dla Draw Things wymiary są automatycznie
dopasowywane do wielokrotności 64.

## Zarządzanie modelami

### Lista modeli

```sh
ai --models [local|ollama|ollama-experimental|draw-things]
            [--order|-o [FIELD[,FIELD...]]] [--asc|--desc]
            [--dependencies|-d]
```

Przykłady:

```sh
ai --models
ai --models draw-things
ai --models local --dependencies
ai --models -o 'backend<,type<,rating<,size>'
```

`--dependencies` pokazuje również zależności i metadane Draw Things, domyślnie
ukryte na listach. Znacznik `<` oznacza sortowanie malejące, a `>` rosnące.
Wartość zawierającą te znaki należy ująć w apostrofy, aby powłoka nie uznała ich
za przekierowanie.

### Szczegóły i odświeżanie katalogów

```sh
ai --details [MODEL]
ai --models-refresh
```

Odświeżanie pobiera aktualne katalogi Ollama, Ollama Experimental i Draw Things.
Jeżeli źródło jest niedostępne, aplikacja zachowuje ostatnie poprawne dane cache.

### Instalowanie modeli

```sh
ai --install [MODEL] [--backend|-b [auto|ollama|draw-things]]
ai --install --source|-s [SOURCE]
             [--backend|-b [auto|ollama|draw-things]]
             [--type|-t [auto|model|lora]]
```

Przykłady:

```sh
ai --install qwen3.5:4b
ai --install realvisxl_v4.0_q6p_q8p.ckpt
ai --install -s ~/Downloads/style.safetensors -b draw-things -t lora
ai --install -s https://example.com/model.gguf
```

### Aktualizowanie i usuwanie modeli

```sh
ai --update-model [MODEL]
ai --uninstall [MODEL] [--dependencies|-d [keep|unused|all]]
```

Tryby usuwania zależności Draw Things:

- `keep` — usuwa model, pozostawiając wszystkie zależności;
- `unused` — usuwa model i nieużywane zależności; jest to tryb domyślny;
- `all` — usuwa model i wszystkie znane zależności, również współdzielone.

Operacje instalacji, aktualizacji i usuwania wymagają potwierdzenia.

### Model bazowy i stan Ollama

```sh
ai --set-base [MODEL]
ai --run [MODEL] [--context-length|-l [VALUE]]
ai --stop [MODEL]
ai --stop-all
```

`--run` ładuje model do pamięci bez otwierania rozmowy. Domyślna długość
kontekstu wynosi `16K`.

## Sesje i narzędzia

```sh
ai --session
ai --session [SESSION] --delete|-d
ai --session [SESSION] --rename|-r [NEW_NAME]
ai --tools
ai --tool [TOOL] --enable|-e|--disable|-d
```

`ai --session` bez nazwy wyświetla zapisane sesje Chat i Agent.

## Administracja

```sh
ai --setup [ollama|npm|codex|dialog|draw-things-cli|imagemagick]
ai --update [ollama|npm|codex|dialog|draw-things-cli|imagemagick]
ai --purge [COMPONENT]
ai --clear-cache
```

`--setup` instaluje brakujące komponenty, a `--update` aktualizuje już
zainstalowane. Bez wskazania komponentu aplikacja pozwala wybrać lub przetwarza
cały obsługiwany zestaw zależnie od użytego interfejsu.

`--purge` jest operacją destrukcyjną i wymaga potwierdzenia `y`. Obsługiwane
wartości to:

- `ollama`;
- `models` lub `ollama-models`;
- `npm`;
- `codex`;
- `dialog`;
- `draw-things-cli`;
- `draw-things-models`;
- `'*'` — cały zarządzany toolchain i dane modeli.

Gwiazdka musi być ujęta w apostrofy. Zmienna `AI_PURGE_FORCE=1` pomija
potwierdzenie i powinna być używana wyłącznie świadomie w automatyzacji.

## Diagnostyka

Globalną opcję `--verbose` można umieścić przed lub po nazwie polecenia:

```sh
ai --verbose --models
ai --models --verbose
```

Diagnostyka trafia do `stderr` i obejmuje między innymi:

- oczyszczone z sekretów polecenia zewnętrzne;
- katalog roboczy i timeout;
- decyzje dotyczące cache;
- kod zakończenia i czas wykonywania procesu;
- przechwycony `stderr`.

`--verbose` nie zmienia właściwego rezultatu polecenia.

## Pliki aplikacji

| Dane | Lokalizacja |
| --- | --- |
| Ustawienia | `~/.config/ai/settings.json` |
| Ustawienia narzędzi | `~/.config/ai/tools.json` |
| Sesje | `~/.config/ai/sessions/` |
| Cache | `${XDG_CACHE_HOME:-~/.cache}/ai/` |

Pliki ustawień i sesji są zapisywane atomowo w formacie JSON. `--clear-cache`
usuwa wyłącznie dane możliwe do ponownego pobrania — nie usuwa ustawień, sesji
ani zainstalowanych modeli.

## Zmienne środowiskowe

| Zmienna | Znaczenie |
| --- | --- |
| `AI_OLLAMA_URL` | adres lokalnego API Ollama |
| `OLLAMA_MODELS` | własny katalog modeli Ollama |
| `AI_LIBRARY_CACHE_TTL` | czas ważności katalogu Ollama w sekundach |
| `AI_DRAW_THINGS_CACHE_TTL` | czas ważności katalogu Draw Things |
| `DRAWTHINGS_MODELS_DIR` | własny katalog Models Draw Things |
| `AI_HW_OS`, `AI_HW_ARCH` | nadpisanie wykrytego systemu i architektury |
| `AI_HW_CHIP`, `AI_HW_MODEL` | nadpisanie CPU/SoC i modelu urządzenia |
| `AI_HW_RAM_GB` | nadpisanie ilości pamięci w GB |
| `AI_PURGE_FORCE=1` | pominięcie potwierdzenia purge |
| `NO_COLOR` | wyłączenie kolorów ANSI |

## Struktura projektu

```text
.
├── ai                     # launcher POSIX shell
├── _bootstrap.py          # niezależne od nazwy katalogu ładowanie pakietu
├── ai.py                  # główny punkt wejścia aplikacji
├── config.py              # stałe aplikacji
├── console/
│   ├── commands/          # modele poleceń CLI
│   ├── handlers/          # wykonanie poszczególnych poleceń
│   └── models/            # modele warstwy konsolowej
├── core/                  # logika domenowa i integracje backendów
│   ├── agent/
│   ├── chat/
│   ├── draw_things/
│   ├── ollama/
│   ├── session/
│   └── storage/
├── enums/                 # współdzielone enumeracje
├── exceptions/            # kontrolowane błędy aplikacji
├── models/                # główne modele danych
└── views/
    ├── dtos/              # DTO wejścia i rezultatu widoków
    └── models/            # modele wspólne widoków dialog
```

Przepływ polecenia CLI:

```text
launcher → bootstrap → CLIParser → CLICommand → CommandHandler → service/backend
```

Widoki TUI budują konfigurację `dialog` przez wspólną warstwę widoków i DTO,
natomiast wykonanie operacji nadal przechodzi przez te same handlery co CLI.

## Bezpieczeństwo

- polecenia destrukcyjne wymagają jawnego potwierdzenia;
- usuwane ścieżki są sprawdzane przed wykonaniem operacji;
- chronione są między innymi katalog główny systemu, katalog domowy, workspace
  aplikacji, punkty montowania i niebezpieczne dowiązania symboliczne;
- sekrety w diagnostyce poleceń zewnętrznych są maskowane;
- trwałe pliki JSON otrzymują uprawnienia ograniczone do użytkownika.

Pełną, zawsze aktualną listę argumentów można wyświetlić poleceniem:

```sh
ai --help
```
