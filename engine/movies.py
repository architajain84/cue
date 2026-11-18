"""Content-based movie recommender: TF-IDF on genres, people, country and plot + cosine similarity."""
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


def _tags(m: pd.DataFrame) -> pd.Series:
    def squash(names):  # "Shah Rukh Khan, Kajol" -> "shahrukhkhan kajol"
        return " ".join(n.replace(" ", "").lower() for n in str(names).split(",") if n.strip())
    genres = m.listed_in.map(squash)
    return (genres + " " + genres + " " + m.director.map(squash) + " "
            + m.cast.map(lambda c: squash(",".join(str(c).split(",")[:5]))) + " "
            + m.country.map(squash) + " " + m.description.str.lower())


class MovieRecommender:
    def __init__(self, movies: pd.DataFrame):
        self.m = movies
        self.vec = TfidfVectorizer(stop_words="english", min_df=2, max_features=30000)
        self.X = self.vec.fit_transform(_tags(movies))

    def similar(self, idx: int, k: int = 10) -> pd.DataFrame:
        sims = linear_kernel(self.X[idx], self.X).ravel()
        sims[idx] = -1
        top = np.argsort(-sims)[:k]
        out = self.m.iloc[top].copy()
        out["score"] = sims[top]
        return out

    def for_history(self, idxs: list[int], k: int = 10) -> pd.DataFrame:
        """'Because you watched…' for several titles, recent ones weighted more."""
        if not idxs:
            return self.m.iloc[0:0]
        weights = np.linspace(0.5, 1.0, len(idxs))
        sims = sum(w * linear_kernel(self.X[i], self.X).ravel() for w, i in zip(weights, idxs))
        sims[idxs] = -1
        top = np.argsort(-sims)[:k]
        return self.m.iloc[top]
