# MKV Audio Track Manager

Manage audio tracks from `.mkv` files: select a single track to keep, or remove a specific track while keeping the rest — along with the original video and subtitles.

---

## Requirements

### 1. Conda Environment

```bash
conda create -n mkv-audio python=3.12
conda activate mkv-audio
```

### 2. MKVToolNix

Download and install [MKVToolNix](https://mkvtoolnix.download/downloads.html) and make sure `mkvmerge` is available in the system PATH.

Verify the installation:

```bash
mkvmerge --version
```

---

## Modes

| Mode | Description |
|---|---|
| **select** | Keep one audio track, discard the rest |
| **remove** | Remove one audio track, keep the rest |

---

## Usage

### Interactive mode (menu)

```bash
python clean-mkv-audio.py "file.mkv"
```

Shows a menu to choose the operation, then lists tracks to pick from:

```
Selecciona una operación:
  [1] Seleccionar pista de audio (conservar una)
  [2] Eliminar pista de audio (conservar el resto)

Pistas de audio disponibles:
  [0] Audio - spa - AAC  (track id: 2)
  [1] Audio - jpn - AC3  (track id: 3)
  [2] Audio - ara - DTS  (track id: 4)
```

After processing, prompts whether to replace the original file.

### Interactive remove mode

```bash
python clean-mkv-audio.py "file.mkv" --remove
```

Skips the menu and goes directly to remove mode. Lists tracks and prompts which one to eliminate.

### Non-interactive mode

```bash
# Keep only track 0
python clean-mkv-audio.py "file.mkv" --track 0

# Remove track 2, keep the rest
python clean-mkv-audio.py "file.mkv" --remove --track 2

# Remove track 2 and replace the original file
python clean-mkv-audio.py "file.mkv" --remove --track 2 --replace
```

### Options

| Option | Description |
|---|---|
| `--remove` | Switch to remove mode |
| `--track N` | Track index (non-interactive, skips prompt) |
| `--replace` | Replace the original file with the result (no prompt) |

---

## BAT Script (Windows)

Drag and drop the MKV file onto `run_clean_mkv_audio.bat`, or run from the terminal:

```bat
run_clean_mkv_audio.bat "file.mkv"
run_clean_mkv_audio.bat "file.mkv" --remove
run_clean_mkv_audio.bat "file.mkv" --remove --track 2
run_clean_mkv_audio.bat "file.mkv" --remove --track 2 --replace
run_clean_mkv_audio.bat "file.mkv" --track 0 --replace
```

---

## Output Files

| Mode | Naming pattern |
|---|---|
| select | `<name>_audio_<language>_<codec>.mkv` |
| remove | `<name>_removed_<language>_<codec>.mkv` |

**Examples:**
- Select spa: `movie_audio_spa_AAC.mkv`
- Remove ara: `movie_removed_ara_DTS.mkv`
