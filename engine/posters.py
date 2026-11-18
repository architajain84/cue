"""Posters from TMDB (preferred) or OMDb (backup). Without a key the app shows styled title cards."""
import os

import requests


def get_keys(secrets=None) -> dict:
    secrets = secrets or {}
    return {
        "tmdb": secrets.get("TMDB_API_KEY") or os.getenv("TMDB_API_KEY", ""),
        "omdb": secrets.get("OMDB_API_KEY") or os.getenv("OMDB_API_KEY", ""),
    }


def poster_url(title: str, year: int, is_show: bool, keys: dict) -> str | None:
    try:
        if keys.get("tmdb"):
            kind = "tv" if is_show else "movie"
            year_param = "first_air_date_year" if is_show else "year"
            r = requests.get(f"https://api.themoviedb.org/3/search/{kind}",
                             params={"api_key": keys["tmdb"], "query": title, year_param: year}, timeout=6)
            res = r.json().get("results", [])
            if res and res[0].get("poster_path"):
                return "https://image.tmdb.org/t/p/w342" + res[0]["poster_path"]
        if keys.get("omdb"):
            kind = "series" if is_show else "movie"
            for params in ({"t": title, "y": year, "type": kind}, {"t": title, "type": kind}):
                r = requests.get("https://www.omdbapi.com/", params={"apikey": keys["omdb"], **params}, timeout=6)
                p = r.json().get("Poster")
                if p and p != "N/A":
                    return p
    except requests.RequestException:
        return None
    return None
