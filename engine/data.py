"""Loads and prepares Cue's data. No Streamlit here, so it can be tested on its own."""
from pathlib import Path
import re

import pandas as pd

from .moods import audio_moods, movie_moods

DATA = Path(__file__).resolve().parent.parent / "data"


def norm_title(x: str) -> str:
    """Lower-case a title and strip soundtrack words, brackets and punctuation."""
    x = str(x).lower()
    x = re.sub(r"\(.*?\)|\[.*?\]", " ", x)
    x = re.sub(r"original motion picture soundtrack|motion picture soundtrack|soundtrack"
               r"|music from the netflix.*|from the netflix.*|\bost\b", " ", x)
    x = re.sub(r"[^a-z0-9 ]", " ", x)
    return re.sub(r"\s+", " ", x).strip()


def load_movies() -> pd.DataFrame:
    m = pd.read_csv(DATA / "netflix_titles.csv")
    m = m.fillna({"director": "", "cast": "", "country": "", "listed_in": "", "description": "", "rating": "", "duration": ""})
    m["moods"] = [movie_moods(g, d) for g, d in zip(m.listed_in, m.description)]
    m["key"] = m.title.map(norm_title)
    return m.reset_index(drop=True)


def _match(df: pd.DataFrame, name: str, artist_hint: str):
    hit = df[(df.track_name.str.lower() == name.lower()) &
             (df.artists.str.contains(re.escape(artist_hint), case=False, na=False))]
    return hit.index[0] if len(hit) else None


def load_songs() -> pd.DataFrame:
    s = pd.read_csv(DATA / "spotify_tracks.csv")
    s["themes"] = [[] for _ in range(len(s))]
    s["summary"] = ""
    s["screen_title"], s["screen_year"], s["screen_type"], s["screen_note"] = "", 0, "", ""
    s["curated"] = False

    # extra songs that are not in the Spotify dataset (e.g. Dola Re Dola)
    extra = pd.read_csv(DATA / "extra_songs.csv").fillna("")
    rows = []
    for e in extra.itertuples():
        rows.append({"track_id": "", "track_name": e.track_name, "artists": e.artists, "album_name": e.screen_title,
                     "popularity": 60, "genres": "indian", "themes": e.themes.split(";"), "summary": e.summary,
                     "screen_title": e.screen_title, "screen_year": int(e.screen_year), "screen_type": e.screen_type,
                     "screen_note": "", "curated": True})
    if rows:
        s = pd.concat([s, pd.DataFrame(rows)], ignore_index=True)

    # lyric-based vibes (from tools/build_vibes.py or written by hand)
    for v in pd.read_csv(DATA / "song_vibes.csv").fillna("").itertuples():
        i = _match(s, v.track_name, v.artist_hint)
        if i is not None:
            s.at[i, "themes"] = v.themes.split(";")
            s.at[i, "summary"] = v.summary
            s.at[i, "curated"] = True

    # hand-checked song -> movie/show links
    for t in pd.read_csv(DATA / "song_screens.csv").fillna("").itertuples():
        i = _match(s, t.track_name, t.artist_hint)
        if i is not None:
            s.at[i, "screen_title"], s.at[i, "screen_year"] = t.screen_title, int(t.screen_year)
            s.at[i, "screen_type"], s.at[i, "screen_note"] = t.screen_type, t.note

    num = ["danceability", "energy", "valence", "tempo", "acousticness", "instrumentalness", "speechiness", "loudness"]
    s[num] = s[num].astype(float)
    s["moods"] = [list(t) if len(t) else audio_moods(v, e, d) if pd.notna(v) else []
                  for t, v, e, d in zip(s.themes, s.valence, s.energy, s.danceability)]
    s["label"] = s.track_name + " · " + s.artists.str.replace(";", ", ")
    return s.reset_index(drop=True)
