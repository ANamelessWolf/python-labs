# Python Labs

A collection of small Python projects and experiments. Each subfolder is an isolated lab with its own README,
dependencies and configuration.

## Labs

| Lab | What it does | Language |
|---|---|---|
| [`tmdb-updates`](tmdb-updates/README.md) | Checks a local TV library against The Movie Database: complete seasons, missing episodes and what is about to air. CLI `TMDB` | ES |
| [`nyaa-scrapper`](nyaa-scrapper/README.md) | Searches every episode of a series on nyaa.si and saves the chosen magnet links (optional language filter). CLI `NYAA` | ES |
| [`pbay-scrapper`](pbay-scrapper/README.md) | Same as `nyaa-scrapper`, for a Pirate Bay mirror. CLI `PBAY` | ES |
| [`setlist-fm-scrapper`](setlist-fm-scrapper/README.md) | Finds a concert setlist on setlist.fm (official API) by band and date, lists a band's concerts in a year (or range), or finds the concerts where a song was played; album of each song via iTunes; exports `yt-music-playlist` JSON. CLI `SETLISTFM` | ES |
| [`yt-music-playlist`](yt-music-playlist/README.md) | Syncs playlists defined in JSON with a YouTube Music account (ytmusicapi) | ES |
| [`spotify-analysis`](spotify-analysis/readme.md) | Pulls your Spotify playlists and runs a genre and artist analysis | EN |
| [`img-scraper`](img-scraper/README.md) | Configurable image scraper: downloads images by type/size and follows a "next page" action | EN |
| [`audio-to-flac`](audio-to-flac/README.md) | Converts `.mp3`, `.wav` and `.m4a` files to FLAC with FFmpeg | EN |
| [`mkv-cleaner`](mkv-cleaner/README.md) | Keeps or removes audio tracks in `.mkv` files with MKVToolNix, and merges two MKV files with FFmpeg | EN |
| [`utils`](utils/README.md) | Loose scripts to rename episodes (`SxxEyy`) and move movies into `Title (Year)` folders | ES |

## Command-line tools

`TMDB`, `NYAA`, `PBAY` and `SETLISTFM` share the same layout:

```
<lab>/
    <NAME>.bat        wrapper with absolute paths: activates the conda env and runs <name>.py (copy it to Z:\bin)
    <name>.py         entry point, only calls <name>_app.cli.main
    <name>_app/
        cli.py        options, commands (cmd_*) and main
        report.py     console report (rich)
        export.py     the same data as JSON, for --json
        ...
    config/settings.example.json   copy it to settings.json (settings.json is git-ignored)
```

### JSON output (`--json`)

All of them accept `--json` to print their result as a single JSON object on stdout instead of the console report.
They are used this way by the Node Board nodes.

```powershell
TMDB updates --json
NYAA -q "[ToonsHub] Thousand-Year Blood War S01E01" --json
PBAY -c config\other.json --json
SETLISTFM -b "Gorillaz" -d "11/20/2026" --json
```

- stdout only carries the JSON; progress, warnings and errors go to stderr.
- A fatal error (bad configuration, series not found…) exits with code 1 and prints no JSON.
- Dates are ISO, numbers are numbers (`sizeBytes` next to the readable `size`), states are constants
  (`NOT_FOUND`) and keys are always present (`null` when there is no value).
- `NYAA` / `PBAY`: `--json` implies `--auto` (first result) and cannot be combined with `-w`.
- Without `--json` everything works as before.

Each lab's README has a "Salida en JSON" section with the fields of every command.

## Environments

Each lab uses its own conda environment. Some are created from the lab's `environment.yml`; the others are created
by hand as described in their README.

| Environment | Labs | How |
|---|---|---|
| `tmdb` | `tmdb-updates` | `tmdb-updates/environment.yml` |
| `WebScrapper` | `nyaa-scrapper`, `pbay-scrapper`, `setlist-fm-scrapper` | `nyaa-scrapper/environment.yml` |
| `ytMusic` | `yt-music-playlist` | `yt-music-playlist/environment.yml` |
| `img-scraper` | `img-scraper` | `img-scraper/environment.yml` |
| `spotify-env` | `spotify-analysis` | `conda create` + `requirements.txt` |
| `convertToFlac` | `audio-to-flac` | `conda create` with `ffmpeg` |
| `mkv-audio` | `mkv-cleaner` | `conda create` + MKVToolNix (and FFmpeg for merging) |

`utils` only needs Python 3.10+.

Secrets and local settings (`config/settings.json`, `.env`, `config.json`, `browser.json`, tokens) and generated
output are git-ignored; each lab ships an example file to copy.
