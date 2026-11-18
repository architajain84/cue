"""Music recommender that looks at sound (audio features) AND meaning (lyric themes)."""
import numpy as np
import pandas as pd

from .moods import jaccard

SOUND = ["danceability", "energy", "valence", "tempo", "acousticness", "instrumentalness", "speechiness", "loudness"]


class MusicRecommender:
    def __init__(self, songs: pd.DataFrame):
        self.s = songs
        X = songs[SOUND].astype(float)
        X = (X - X.mean()) / X.std()
        X = X.fillna(0).to_numpy()
        self.X = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)
        self.has_sound = songs.track_id.astype(str).str.len().gt(0).to_numpy()
        self.genres = songs.genres.fillna("").str.split(";")

    def sound_sim(self, idx: int) -> np.ndarray:
        sims = self.X @ self.X[idx]
        if not self.has_sound[idx]:
            sims[:] = 0
        g = set(self.genres[idx])
        bonus = np.array([0.1 if g & set(x) else 0.0 for x in self.genres])
        return np.clip(sims * 0.9 + bonus, -1, 1)

    def sounds_like(self, idx: int, k: int = 8) -> pd.DataFrame:
        sims = self.sound_sim(idx)
        sims[idx] = -2
        pool = np.argsort(-sims)[:300]
        out = self.s.iloc[pool].copy()
        out["sound"] = sims[pool]
        out = out[out.popularity >= 30]
        # drop other versions of the same song (remixes, "with …" editions)
        base = str(self.s.at[idx, "track_name"]).lower().split(" (")[0].split(" - ")[0].strip()
        out = out[~out.track_name.str.lower().str.startswith(base)]
        return out.head(k)

    def vibe_match(self, idx: int, meaning_weight: float = 0.6, k: int = 8):
        """Rank songs we understand the lyrics of by sound + meaning.
        Returns (matches, filtered_out) — filtered_out are songs that SOUND alike but MEAN something different."""
        seed_themes = self.s.at[idx, "themes"]
        sims = self.sound_sim(idx)
        cur = self.s[self.s.curated].copy()
        cur = cur[cur.index != idx]
        cur["sound"] = sims[cur.index]
        cur["meaning"] = [jaccard(seed_themes, t) for t in cur.themes]
        if not seed_themes:  # we don't know this song's lyrics yet: fall back to sound
            cur["score"] = cur.sound
            return cur.sort_values("score", ascending=False).head(k), cur.iloc[0:0]
        cur["score"] = (1 - meaning_weight) * cur.sound.clip(0, 1) + meaning_weight * cur.meaning
        filtered = cur[(cur.meaning == 0) & (cur.sound >= 0.5)].sort_values("sound", ascending=False)
        matches = cur[cur.meaning > 0].sort_values("score", ascending=False)
        return matches.head(k), filtered.head(3)

    def current_vibe(self, history: list[int]) -> dict:
        """Weighted mood counts of recently played songs (most recent counts most)."""
        counts = {}
        for w, i in zip(np.linspace(0.5, 1.0, len(history)), history[-8:]):
            for mood in self.s.at[i, "moods"]:
                counts[mood] = counts.get(mood, 0) + w
        return dict(sorted(counts.items(), key=lambda kv: -kv[1]))

    def for_vibe(self, moods: list[str], exclude=(), k: int = 8, history=()) -> pd.DataFrame:
        """Songs for a set of moods.
        With a listening history, candidates must also sound like and share a style with what was played,
        because a mood guessed from audio alone is often wrong; songs with lyric tags are trusted most."""
        cand = self.s[(self.s.popularity >= 50) | self.s.curated]
        cand = cand[~cand.index.isin(exclude)]
        mood = cand.moods.map(lambda m: jaccard(moods, m))
        trust = np.where(cand.curated, 1.0, 0.5)  # lyric tags are reliable, audio guesses less so
        score = mood * trust + cand.curated * 0.15 + cand.popularity / 1000
        history = [i for i in history if self.has_sound[i]][-8:]
        if history:
            weights = np.linspace(0.5, 1.0, len(history))[:, None]
            centre = (self.X[history] * weights).sum(0)
            centre /= np.linalg.norm(centre) + 1e-9
            sound = np.clip(self.X[cand.index] @ centre, 0, 1)
            styles = set().union(*(set(self.genres[i]) for i in history))
            style = cand.genres.fillna("").str.split(";").map(lambda g: 1.0 if styles & set(g) else 0.0)
            score = 0.5 * score + 0.3 * sound + 0.2 * style
        cand = cand.assign(score=score)
        cand = cand[(mood > 0) & (cand.score > 0.15)].sort_values("score", ascending=False)
        base = cand.track_name.str.lower().str.split(" (", regex=False).str[0].str.split(" - ", regex=False).str[0].str.strip()
        return cand[~base.duplicated()].head(k)  # one version of each song
