"""Offline evaluation of Cue's recommenders.  Run:  python tests/evaluate.py

Metric: genre-precision@10 = share of the top-10 recommendations that share at least one
genre with the item the user picked, compared against 10 random items (baseline).
Vibe engine: share of the top-5 that share a meaning (lyric theme) with the chosen song.
"""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.data import load_movies, load_songs
from engine.moods import jaccard
from engine.movies import MovieRecommender
from engine.music import MusicRecommender
from engine.trace import Tracer

m, s = load_movies(), load_songs()
mr, sr, tr = MovieRecommender(m), MusicRecommender(s), Tracer(m, s)
rng, K = np.random.default_rng(42), 10

g = m.listed_in.map(lambda x: {a.strip() for a in x.split(",")})
idx = rng.choice(len(m), 500, replace=False)
gp = lambda i, recs: np.mean([len(g[i] & g[j]) > 0 for j in recs])
print(f"Movies  genre-precision@10: {np.mean([gp(i, mr.similar(i, K).index) for i in idx]):.1%}"
      f"  (random: {np.mean([gp(i, rng.choice(len(m), K, replace=False)) for i in idx]):.1%})")

sg = s.genres.fillna("").str.split(";").map(set)
pop = s[s.popularity >= 40].index.to_numpy()
sidx = rng.choice(pop, 300, replace=False)
sgp = lambda i, recs: np.mean([len(sg[i] & sg[j]) > 0 for j in recs])
print(f"Music   genre-precision@10: {np.mean([sgp(i, sr.sounds_like(i, K).index) for i in sidx]):.1%}"
      f"  (random: {np.mean([sgp(i, rng.choice(pop, K, replace=False)) for i in sidx]):.1%})")

cur = s[s.curated & (s.track_id.astype(str).str.len() > 0)].index
both, sound_only = [], []
for i in cur:
    a, _ = sr.vibe_match(i, 0.6, 5)
    both.append(np.mean([jaccard(s.at[i, "themes"], t) > 0 for t in a.themes]) if len(a) else 0)
    others = s[s.curated].drop(i)
    top = others.index[np.argsort(-sr.sound_sim(i)[others.index])[:5]]
    sound_only.append(np.mean([jaccard(s.at[i, "themes"], s.at[j, "themes"]) > 0 for j in top]))
print(f"Vibe    meaning-match@5: sound+meaning {np.mean(both):.0%}  vs  sound only {np.mean(sound_only):.0%}  ({len(cur)} songs)")

film = s[s.genres.str.contains("pop-film|indian", na=False)].index
t = [tr.trace(j) for j in film]
print(f"Trace   {sum(1 for x in t if x)} of {len(film)} film/Indian songs linked to a title, "
      f"{sum(1 for x in t if x and x['netflix_idx'] is not None)} of them on Netflix")

t0 = time.time(); [mr.similar(i, 10) for i in idx[:100]]
t1 = time.time(); [sr.sounds_like(i, 8) for i in sidx[:100]]
print(f"Speed   movie picks {1000 * (t1 - t0) / 100:.1f} ms, music picks {1000 * (time.time() - t1) / 100:.1f} ms per request")
