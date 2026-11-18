"""Quick checks for the recommendation engine. Run:  python tests/check_engine.py"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.data import load_movies, load_songs
from engine.movies import MovieRecommender
from engine.music import MusicRecommender
from engine.trace import Tracer

t = time.time()
movies, songs = load_movies(), load_songs()
mr, sr, tr = MovieRecommender(movies), MusicRecommender(songs), Tracer(movies, songs)
print(f"loaded {len(movies)} titles, {len(songs)} songs, {songs.curated.sum()} with lyric vibes in {time.time()-t:.1f}s")

i = movies.index[movies.title == "Love Aaj Kal"][0]
print("\nBecause you watched Love Aaj Kal:", mr.similar(i, 5).title.tolist())

ps5 = songs.index[songs.track_name == "PS5"][0]
end = songs.index[songs.track_name == "End of Time"][0]
print("\nPS5 vs End of Time  sound similarity:", round(float(sr.sound_sim(ps5)[end]), 2))
match, filtered = sr.vibe_match(ps5)
print("PS5 vibe matches:", match.track_name.tolist())
print("PS5 filtered out (sounds alike, means something else):", filtered.track_name.tolist())

for name in ["Shayad", "Ajj Din Chadheya", "Kajra Re", "Dola Re Dola", "Kabira"]:
    j = songs.index[songs.track_name == name][0]
    tr_ = tr.trace(j)
    nf = movies.at[tr_["netflix_idx"], "title"] if tr_ and tr_["netflix_idx"] is not None else "not on Netflix"
    print(f"trace {name:18s} -> {tr_['title']} ({tr_['year']})  Netflix: {nf}")

auto = [tr.trace(j) for j in songs.index[songs.genres.str.contains("pop-film|indian", na=False)][:3000]]
print("\nauto-traced film songs (sample of 3000):", sum(1 for a in auto if a))
