# Spotify Playlist Analysis 🎧

This script connects to your Spotify account, fetches tracks from your playlists, extracts artist information, and performs a basic genre analysis using the Spotify Web API.


## Tech Stack & Libraries
This project uses the following technologies and libraries:

### 📦 Core Stack

|Tool/Library|Purpose|
|--|--|
|Python 3.10|Primary language|
|Conda|Environment and dependency management|

### 🧰 Python Libraries

|Library|Description|
|--|--|
|spotipy|Python wrapper for the Spotify Web API|
|python-dotenv|Loads secrets from .env files safely|
|pandas|Data manipulation and tabular analysis (in `requirements.txt`, not used by the code yet)|
|numpy|Numerical computing and support for arrays (in `requirements.txt`, not used by the code yet)|
|matplotlib|Visualizations for genre/artist distribution (in `requirements.txt`, not used by the code yet)|

## ⚙️ Setup

### 1. Create a Spotify Developer App

Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/) and:

- Create a new app
- Save the **Client ID** and **Client Secret**
- Add this **Redirect URI**:  
  `http://127.0.0.1:8888/callback`

### 2. Clone the Repository

```bash
git clone https://github.com/ANamelessWolf/python-labs.git
cd python-labs/spotify-analysis
```

### 3. Setup dependencies, and environment

#### Create Environment with Conda

```bash
conda create -n spotify-env python=3.10
conda activate spotify-env
```

`envs/spotify-env.yml` is git-ignored (it may hold local settings), so it is not in the repository. If you have
your own copy you can use `conda env create -f envs/spotify-env.yml` instead.

#### Install dependencies with the requirements file

```bash
pip install -r requirements.txt
```

### 4. Configure Your .env File

Copy `.env.example` to `.env` and fill in your Spotify app credentials. The redirect URI must match the one you
registered in the dashboard:

```bash
SPOTIPY_CLIENT_ID=your_client_id
SPOTIPY_CLIENT_SECRET=your_client_secret
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

### 5. ▶️ Run the Script

```bash
python main.py
```

The first run opens the browser to log in to Spotify; the token is saved in `spotify_token_cache.json`
(git-ignored), so later runs don't ask again.

## 📊 Reports

The report is chosen by editing the variables at the top of `main.py`:

```python
limit = 50                              # top artists/tracks to fetch (1-50)
auth_type = AuthType.USER               # USER (login with scopes) or CLIENT (client credentials, no user data)
timeRange = TimeRange.LONG_TERM         # SHORT_TERM (~4 weeks), MEDIUM_TERM (~6 months), LONG_TERM (~1 year)
report_type = ReportType.USER_LIBRARY   # which report to generate
```

| `report_type` | Output | Contents |
|---|---|---|
| `TOP_HISTORY` | `reports/listening_report.json` | Your top artists and the genre distribution for `timeRange` |
| `USER_LIBRARY` | `reports/user_library_report.json` | Liked songs and playlist tracks, top songs, artist and genre distribution, followed artists |
| `RECENTLY_PLAYED` | — | Not implemented yet |

Artist genres are cached in `cache/` to avoid repeating API calls. Reports and cache files are git-ignored.

## 📁 Structure

```text
spotify-analysis/
├── main.py                 # configuration and report selection
├── requirements.txt
├── .env.example
├── core/
│   ├── auth_helper.py      # Spotify authentication (USER / CLIENT)
│   ├── enums.py            # AuthType, TimeRange, ReportType
│   ├── services/           # report generation (listening history, user library, playlists)
│   ├── models/             # report dataclasses (songs, artists, genres)
│   └── helpers/            # cache, logging, library fetching, report writing
├── cache/                  # artist genre cache (git-ignored)
└── reports/                # generated JSON reports (git-ignored)
```


