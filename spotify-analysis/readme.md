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
|pandas|Data manipulation and tabular analysis|
|numpy|Numerical computing and support for arrays|
|matplotlib|Basic visualizations for genre/artist distribution|

## ⚙️ Setup

### 1. Create a Spotify Developer App

Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/) and:

- Create a new app
- Save the **Client ID** and **Client Secret**
- Add this **Redirect URI**:  
  `http://127.0.0.1:8888/callback`

### 2. Clone the Repository

```bash
git clone https://github.com/your-username/python-labs.git
cd python-labs/spotify-analysis
```

### 3. Setup dependencies, and environment

#### Create Environment with Conda

```bash
conda env create -f ../envs/spotify-env.yml
conda activate spotify-env
```

#### Install dependencies with the requirements file

```bash
pip install -r requirements.txt
```

### 4. Configure Your .env File

Create a .env file based on .env.example and fill in your Spotify app credentials:

```bash
SPOTIPY_CLIENT_ID=your_client_id
SPOTIPY_CLIENT_SECRET=your_client_secret
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback
```

### 5. ▶️ Run the Script

```bash
python main.py
```


