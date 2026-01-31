# convertToFlac 🎵➡️🎶

`convertToFlac` is a **Python** script that converts audio files (`.mp3`, `.wav`, `.m4a`) into **FLAC** format using an input folder and an output folder.  
The program runs **only from the command line** and determines the input format **strictly by file extension**.

---

## 📦 Requirements

- **Anaconda / Miniconda**
- **Python 3.8+**
- **FFmpeg**

---

## 📁 Recommended project structure

```text
convertToFlac/
├── convertToFlac.py
├── input/
│   ├── audio1.mp3
│   ├── audio2.wav
│   └── audio3.m4a
└── output/
```

## 🐍 Create the environment with Anaconda

- 1️⃣ Create the environment with ffmpeg

```sh
conda create -n convertToFlac -c conda-forge --strict-channel-priority python=3.10 ffmpeg
```

- 2️⃣ Activate the environment

```sh
conda activate convertToFlac
```

## Verify installation:

```sh
ffmpeg -version
```

▶️ Running the script

With the environment activated:

```sh
python convertToFlac.py <input_folder> <output_folder>

------------------------------------------------------
python convertToFlac.py input output
```


## ⚙️ Important notes

Input format is determined only by the file extension ffmpeg cannot be installed via pip 
No graphical interface (CLI only)
Suitable for automation and batch processing


## ✅ Quick summary

```sh
conda create -n convertToFlac python=3.10
conda activate convertToFlac
pip install -r requirements.txt
conda install -c conda-forge ffmpeg
python convertToFlac.py input output
```