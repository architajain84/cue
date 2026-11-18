"""Mood Bridge: find movies/shows for a set of moods (songs use MusicRecommender.for_vibe)."""
import pandas as pd

from .moods import jaccard


def movies_for_moods(movies: pd.DataFrame, moods: list[str], exclude=(), k: int = 10) -> pd.DataFrame:
    score = movies.moods.map(lambda m: jaccard(moods, m))
    recency = (movies.release_year.clip(1990, 2021) - 1990) / 300  # tiny nudge towards newer titles
    out = movies.assign(score=score + recency)
    out = out[(score > 0) & ~out.index.isin(exclude)]
    return out.sort_values("score", ascending=False).head(k)
