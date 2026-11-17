# convertToFlac 🎵➡️🎶

`convertToFlac.py` converts every `.mp3`, `.wav` and `.m4a` file in an input folder into **FLAC** and writes the
results to an output folder, using **FFmpeg**. The input format is determined **only by the file extension**.

---

## 📦 Requirements

- **Anaconda / Miniconda**
- **Python 3.8+**
- **FFmpeg** (installed with conda; it cannot be installed with pip)

## 🐍 Environment

```sh
conda create -n convertToFlac -c conda-forge --strict-channel-priority python=3.10 ffmpeg
conda activate convertToFlac
ffmpeg -version        # verify the installation
```

The script only uses the standard library, so there is nothing else to install.

---

## ▶️ Usage

```sh
python convertToFlac.py <input_folder> <output_folder>
python convertToFlac.py input output
```

- Only the files directly inside `<input_folder>` are converted (subfolders are ignored).
- `<output_folder>` is created if it does not exist.
- Each file keeps its name with the `.flac` extension: `song.mp3` → `song.flac`.
- An existing `.flac` with the same name is **overwritten** (`ffmpeg -y`).
- If a file fails, it prints a warning and continues with the next one.

### BAT script (Windows)

`run_convertToFlac.bat` activates the `convertToFlac` environment (from `%USERPROFILE%\anaconda3`), moves to
`Z:\dev\py\python-labs\audio-to-flac` and runs:

```bat
python convertToFlac.py audios flac
```

> The `.bat` uses the `audios` and `flac` folders, while the repository includes `input/` and `output/`
> (both git-ignored). Create those folders, or change the arguments in the `.bat` to `input output`.

---

## 📁 Structure

```text
audio-to-flac/
├── convertToFlac.py
├── run_convertToFlac.bat
├── input/        # audio files to convert (git-ignored)
└── output/       # generated .flac files (git-ignored)
```
