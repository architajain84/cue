# Cue: Movies and Music Explorer 🎬🎧

**For the love of movies and music.** In film, a *cue* is the music that plays under a scene, and in everyday life it's the hint for what comes next. Cue does both.

 One place for your movies and music. Cue learns from both and suggests what to watch and play next, matched to your mood, not just your history.

B.Tech CSE major project by **Archita Jain**, Medicaps University · Guide: **Prof. Kriti Joshi**

## What it does

| Feature | How it works |
|---|---|
| **Movie picks** | Content-based filtering: TF-IDF on genre, director, cast, country and plot of 8,807 Netflix titles, ranked by cosine similarity |
| **Music picks** | Audio features (energy, valence, tempo, danceability…) of 81,000+ Spotify tracks, compared with cosine similarity |
| **Vibe engine** | Songs also get *meaning* tags from their lyrics. A song is recommended only when sound **and** meaning match, so a playful tease (PS5) isn't followed by a devoted promise (End of Time) |
| **Your vibe right now** | Moods of the last few songs played, with recent ones weighted more |
| **Trace to screen** | A song links back to its movie or show: hand-checked links first, then automatic matching of soundtrack albums to Netflix titles |
| **Open Library** | Public-domain films and Creative Commons music from Wikimedia Commons that play in full, filterable by mood |
| **Mood Bridge** | One shared mood vocabulary for movies and songs: pick a mood, get something to watch and something to play |
| **Forgiving search** | Ignores capitals, spaces, punctuation and small typos ("love aajkal" finds *Love Aaj Kal*); songs show the film they come from |
| **Browse by genre** | Bollywood, K-pop, EDM, R&B, Hip-hop and more |
| **Built-in help** | A pop-up for each page on the first visit, and an ⓘ button beside every feature |

## Data

- **Netflix Movies and TV Shows** (Kaggle, `data/netflix_titles.csv`)
- **Spotify Tracks Dataset** (Kaggle, 114k tracks across 114 genres; de-duplicated to `data/spotify_tracks.csv`)
- `data/song_vibes.csv`: lyric themes and summaries (only the analysis is stored, never the lyrics)
- `data/song_screens.csv`: hand-checked song → movie/show links
- `data/extra_songs.csv`: songs missing from the Spotify dataset
- `data/open_library.csv`: public-domain films and Creative Commons recordings (with licence and credit) streamed from Wikimedia Commons

## Run it on Windows

1. Install **Python 3.13** from python.org.
2. In this folder, open a terminal and run:
   ```
   py -3.13 -m venv .venv
   .venv\Scripts\python -m pip install -r requirements.txt
   ```
3. Double-click **Start Cue.bat** (or run `.venv\Scripts\python -m streamlit run app.py`).
4. Your browser opens Cue at `http://localhost:8501`.

**Posters (optional):** create `.streamlit/secrets.toml` containing
```
OMDB_API_KEY = "your free key from omdbapi.com"
```
Without a key, Cue shows styled title cards instead.

**Check the engine:** `python tests/check_engine.py`

## Results (`python tests/evaluate.py`)

| Measure | Cue | Baseline |
|---|---|---|
| Movies: genre-precision@10 | 96.1% | 24.3% (random) |
| Music: genre-precision@10 | 85.3% | 2.1% (random) |
| Vibe engine: meaning-match@5 | 100% | 40% (sound only) |
| Songs traced to a film | 521 (298 on Netflix) | – |

## Credits

Netflix Movies and TV Shows dataset by Shivam Bansal (Kaggle) · Spotify Tracks Dataset by Maharshi Pandya (Kaggle) · posters from the OMDb API · Open Library media from Wikimedia Commons (licences shown in the app)

## Project structure

```
app.py              the web app (Streamlit)
engine/data.py      loads and joins all data
engine/movies.py    movie recommender
engine/music.py     sound + meaning music recommender
engine/moods.py     shared mood vocabulary (the Mood Bridge)
engine/trace.py     song → movie/show tracing
engine/bridge.py    movies for a mood
engine/posters.py   OMDb posters
tests/evaluate.py   offline evaluation
```
