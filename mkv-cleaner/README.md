# MKV Audio Track Selector

Select an audio track from an `.mkv` file and generate a new file keeping only that track, along with the original video and subtitles.

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

## Usage

### Interactive mode

```bash
python clean-mkv-audio.py "file.mkv"
```

The script will list the available audio tracks and prompt you to choose one:

```
Available audio tracks:
  [0] Audio - spa - AAC  (track id: 2)
  [1] Audio - eng - AC3  (track id: 3)
  [2] Audio - jpn - DTS  (track id: 4)

Choose track number [0-2]:
```

### Non-interactive mode

```bash
python clean-mkv-audio.py "file.mkv" --track 1
```

Keeps track index `1` directly without prompting.

---

## BAT Script (Windows)

Drag and drop the MKV file onto `run_clean_mkv_audio.bat`, or run it from the terminal:

```bat
run_clean_mkv_audio.bat "file.mkv"
run_clean_mkv_audio.bat "file.mkv" 1
```

The second argument is optional and specifies the track index (non-interactive mode).

---

## Output File

The generated file is saved in the same folder as the original with the following naming pattern:

```
<original_name>_audio_<language>_<codec>.mkv
```

**Example:** `movie_audio_spa_AAC.mkv`
