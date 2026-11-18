"""The shared mood vocabulary that connects movies and music (the Mood Bridge)."""

MOODS = [
    "playful", "flirty", "romantic", "devoted", "longing", "heartbreak",
    "party", "empowering", "hopeful", "nostalgic", "dark", "calm",
]

MOOD_EMOJI_FREE_LABELS = {m: m.capitalize() for m in MOODS}

# Netflix genre (listed_in) -> moods
GENRE_MOODS = {
    "Comedies": ["playful"],
    "TV Comedies": ["playful"],
    "Stand-Up Comedy": ["playful"],
    "Stand-Up Comedy & Talk Shows": ["playful"],
    "Romantic Movies": ["romantic"],
    "Romantic TV Shows": ["romantic"],
    "Horror Movies": ["dark"],
    "TV Horror": ["dark"],
    "Thrillers": ["dark"],
    "TV Thrillers": ["dark"],
    "Crime TV Shows": ["dark"],
    "TV Mysteries": ["dark"],
    "Music & Musicals": ["party"],
    "Action & Adventure": ["empowering"],
    "TV Action & Adventure": ["empowering"],
    "Sports Movies": ["empowering"],
    "Children & Family Movies": ["hopeful"],
    "Kids' TV": ["hopeful"],
    "Documentaries": ["calm"],
    "Docuseries": ["calm"],
    "Faith & Spirituality": ["calm"],
    "Dramas": ["longing"],
    "TV Dramas": ["longing"],
    "Korean TV Shows": ["romantic"],
}

# words in a description -> moods
KEYWORD_MOODS = {
    "romantic": ["love", "romance", "romantic", "falls for", "fall in love", "crush"],
    "party": ["wedding", "dance", "party", "festival", "celebrat"],
    "heartbreak": ["breakup", "heartbreak", "grief", "loss of", "divorce", "mourning"],
    "nostalgic": ["childhood", "memories", "reunion", "nostalg", "years later"],
    "empowering": ["underdog", "overcome", "fight back", "dream of becoming", "champion"],
    "dark": ["murder", "killer", "serial", "revenge", "haunted", "crime"],
    "hopeful": ["hope", "second chance", "new beginning", "inspir"],
    "playful": ["hilarious", "comedy", "mischief", "prank", "quirky"],
}


def movie_moods(listed_in: str, description: str) -> list[str]:
    found = []
    for g in str(listed_in).split(","):
        found += GENRE_MOODS.get(g.strip(), [])
    text = str(description).lower()
    for mood, words in KEYWORD_MOODS.items():
        if any(w in text for w in words):
            found.append(mood)
    # keep order, drop repeats, max 3
    return list(dict.fromkeys(found))[:3]


def audio_moods(valence: float, energy: float, danceability: float) -> list[str]:
    """Rough mood from sound alone, used for songs whose lyrics we haven't analysed."""
    if valence >= 0.55 and energy >= 0.6:
        return ["party", "playful"] if danceability >= 0.65 else ["hopeful", "playful"]
    if valence >= 0.55:
        return ["calm", "hopeful"]
    if energy >= 0.65:
        return ["dark", "empowering"]
    return ["longing", "heartbreak"] if valence < 0.3 else ["longing", "calm"]


def jaccard(a, b) -> float:
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a and b else 0.0
