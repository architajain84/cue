"""Song -> movie/show tracing.

1. Hand-checked links (data/song_screens.csv) always win.
2. Otherwise, a song whose album is a film/series soundtrack is matched to a Netflix title by name.
"""
import re

import pandas as pd

from .data import norm_title

SOUNDTRACK_HINT = re.compile(r"soundtrack|motion picture|\bost\b|from the netflix|music from|from \"", re.I)
FILM_GENRES = {"pop-film", "indian", "disney", "show-tunes"}
FROM_FILM = re.compile(r'[(\[]\s*from\s+(?:the\s+)?["“]([^"”]+)["”]', re.I)  # e.g. Shayad (From "Love Aaj Kal")


class Tracer:
    def __init__(self, movies: pd.DataFrame, songs: pd.DataFrame):
        self.m, self.s = movies, songs
        self.by_key = {}
        for i, k in zip(movies.index, movies.key):
            if len(k) > 3:
                self.by_key.setdefault(k, []).append(i)

    def netflix_match(self, title: str, year: int | None = None):
        """Index of the Netflix title with this name (closest year if several), or None."""
        hits = self.by_key.get(norm_title(title), [])
        if not hits:
            return None
        if year:
            hits = sorted(hits, key=lambda i: abs(int(self.m.at[i, "release_year"]) - int(year)))
            if abs(int(self.m.at[hits[0], "release_year"]) - int(year)) > 1:
                return None  # same name, different film
        return hits[0]

    def trace(self, song_idx: int) -> dict | None:
        s = self.s.loc[song_idx]
        if s.screen_title:
            return {"title": s.screen_title, "year": int(s.screen_year), "type": s.screen_type,
                    "source": "verified", "note": s.screen_note,
                    "netflix_idx": self.netflix_match(s.screen_title, s.screen_year)}
        named = FROM_FILM.search(str(s.track_name)) or FROM_FILM.search(str(s.album_name))
        if named:
            title = named.group(1).strip()
            i = self.netflix_match(title)
            if i is not None:
                r = self.m.loc[i]
                return {"title": r.title, "year": int(r.release_year), "type": r.type,
                        "source": "auto (film named in the song title)", "note": "", "netflix_idx": i}
            return {"title": title, "year": None, "type": "Film", "source": "auto (film named in the song title)",
                    "note": "", "netflix_idx": None}
        album = str(s.album_name)
        film_ish = SOUNDTRACK_HINT.search(album) or (set(str(s.genres).split(";")) & FILM_GENRES)
        if film_ish:
            i = self.netflix_match(album)
            if i is not None:
                r = self.m.loc[i]
                return {"title": r.title, "year": int(r.release_year), "type": r.type,
                        "source": "auto (soundtrack album)", "note": "", "netflix_idx": i}
        return None

    def songs_for(self, movie_idx: int) -> pd.DataFrame:
        """Songs traced to a given Netflix title."""
        key = self.m.at[movie_idx, "key"]
        year = int(self.m.at[movie_idx, "release_year"])
        verified = self.s[(self.s.screen_title.map(norm_title) == key) & ((self.s.screen_year - year).abs() <= 1)]
        album = self.s[self.s.album_name.map(norm_title) == key]
        album = album[album.album_name.str.contains(SOUNDTRACK_HINT, na=False) |
                      album.genres.map(lambda g: bool(set(str(g).split(";")) & FILM_GENRES))]
        named = self.s[self.s.track_name.str.extract(FROM_FILM, expand=False).fillna("").map(norm_title) == key]
        out = pd.concat([verified, named, album])
        out = out[~out.index.duplicated()]
        # a hand-checked link to a different year means a different film with the same name
        wrong_year = (out.screen_title.astype(str).str.len() > 0) & ((out.screen_year - year).abs() > 1)
        return out[~wrong_year].sort_values("popularity", ascending=False)

    def all_traced(self) -> pd.DataFrame:
        """Every hand-checked song -> screen link, for the 'Songs from screens' row."""
        return self.s[self.s.screen_title.astype(str).str.len() > 0]
