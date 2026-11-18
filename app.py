"""Cue: Movies and Music Explorer — for the love of movies and music.

Run on your laptop with:   streamlit run app.py
"""
import difflib
import html
import inspect
import re

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from engine.bridge import movies_for_moods
from engine.data import DATA, load_movies, load_songs
from engine.moods import MOODS
from engine.movies import MovieRecommender
from engine.music import MusicRecommender
from engine.posters import get_keys, poster_url
from engine.trace import Tracer

st.set_page_config(page_title="Cue: Movies and Music Explorer", page_icon="🎬", layout="wide")

# ---------- look and feel ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=DM+Sans:wght@400;500;700&display=swap');
html, body, [class*="css"], .stMarkdown, p, li, label { font-family: 'DM Sans', sans-serif; }
h1, h2, h3, .mv-logo { font-family: 'Space Grotesk', sans-serif !important; letter-spacing: -0.5px; }
.block-container { padding-top: 1.2rem; max-width: 1280px; }
.mv-logo { font-size: 30px; font-weight: 700; color: #14161C; }
.mv-logo span.r { color: #B3262E; } .mv-logo span.g { color: #1E8A52; }
.mv-hero { background: #14161C; color: #F7F3EA; border-radius: 20px; padding: 36px 40px; margin: 8px 0 24px; }
.mv-hero h1 { color: #F7F3EA; font-size: 44px; margin: 0 0 6px; }
.mv-hero p { color: #CFCAC0; font-size: 18px; margin: 0; }
.mv-card { aspect-ratio: 2/3; border-radius: 14px; padding: 14px; display: flex; flex-direction: column;
           justify-content: flex-end; color: #F7F3EA; font-weight: 700; font-size: 15px; line-height: 1.25; }
.mv-card small { font-weight: 400; color: #E8E2D6; font-size: 12px; margin-top: 4px; }
.mv-movie { background: #7A1A21; } .mv-show { background: #3B2A5A; } .mv-song { background: #124A2E; aspect-ratio: 1/1; }
.mv-chip { display: inline-block; padding: 3px 12px; margin: 2px 4px 2px 0; border-radius: 999px; font-size: 13px;
           background: #EFE9DD; color: #4A4843; border: 1px solid #E4DDCF; }
.mv-chip.red { background: #F6E1E1; color: #8A1C23; border-color: #ECC6C6; }
.mv-chip.green { background: #DFF0E6; color: #145C37; border-color: #BFE0CC; }
.mv-box { background: #FFFDF8; border: 1px solid #E4DDCF; border-radius: 16px; padding: 18px 20px; margin-bottom: 14px; }
.mv-muted { color: #6B6862; font-size: 14px; }
.mv-out { border: 1px dashed #BDB6A8; border-radius: 12px; padding: 10px 14px; color: #4A4843; margin-bottom: 8px; font-size: 14px; }
.mv-bar { height: 8px; border-radius: 4px; background: #EFE9DD; margin: 4px 0 10px; }
.mv-bar div { height: 8px; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)


# ---------- data + models (built once, then cached) ----------
@st.cache_resource(show_spinner="Warming up the projector…")
def engine():
    movies, songs = load_movies(), load_songs()
    return movies, songs, MovieRecommender(movies), MusicRecommender(songs), Tracer(movies, songs)


movies, songs, movie_rec, music_rec, tracer = engine()


@st.cache_data
def open_library():
    lib = pd.read_csv(DATA / "open_library.csv")
    lib["moods"] = lib.moods.str.split(";")
    return lib

try:
    KEYS = get_keys(dict(st.secrets))
except Exception:  # no secrets file yet
    KEYS = get_keys()


@st.cache_data(show_spinner=False, ttl=86400)
def cached_poster(title, year, is_show, keys_present):
    return poster_url(title, year, is_show, KEYS)


ss = st.session_state
ss.setdefault("page", "Home")
ss.setdefault("movie", int(movies.index[movies.title == "Love Aaj Kal"][0]))
ss.setdefault("song", int(songs.index[songs.track_name == "PS5"][0]))
ss.setdefault("watched", [])
ss.setdefault("played", [])


ss.setdefault("movie_pick", ss.movie)
ss.setdefault("song_pick", ss.song)


def go(page, movie=None, song=None):
    """Button callback: open a movie or song and switch page."""
    if movie is not None:
        movie = int(movie)
        ss.movie = ss.movie_pick = movie
        ss.watched = [i for i in ss.watched if i != movie][-7:] + [movie]
    if song is not None:
        song = int(song)
        ss.song = ss.song_pick = song
        ss.played = [i for i in ss.played if i != song][-7:] + [song]
    ss.page = page


def on_movie_pick():
    go("Movies", movie=ss.movie_pick)


def on_song_pick():
    go("Music", song=ss.song_pick)


def wide_image(url):
    """Full-width image on both newer (width="stretch") and older Streamlit versions."""
    try:
        st.image(url, width="stretch")
    except Exception:
        st.image(url, use_container_width=True)


def wide_button(label, **kw):
    try:
        return st.button(label, width="stretch", **kw)
    except TypeError:
        return st.button(label, use_container_width=True, **kw)


MUSIC_GENRES = {"Bollywood": "pop-film", "Indian": "indian", "Pop": "pop", "K-pop": "k-pop", "J-pop": "j-pop",
                "EDM": "edm", "Electronic": "electronic", "Dance": "dance", "R&B": "r-n-b", "Hip-hop": "hip-hop",
                "Rock": "rock", "Indie": "indie", "Latin": "latin", "Romance": "romance", "Sad": "sad",
                "Party": "party", "Chill": "chill", "Acoustic": "acoustic", "Jazz": "jazz", "Classical": "classical"}


@st.cache_data(show_spinner=False)
def movie_genres():
    counts = movies.listed_in.str.split(", ").explode().value_counts()
    return [g for g in counts.index if g][:30]


def genre_browser(kind):
    """'Browse by genre' section for the Music or Movies page."""
    section("Browse by genre", "genre")
    if kind == "music":
        label = st.selectbox("Genre", ["Choose a genre…", *MUSIC_GENRES], key="music_genre", label_visibility="collapsed")
        if label in MUSIC_GENRES:
            tag = MUSIC_GENRES[label]
            picks = songs[songs.genres.fillna("").str.split(";").map(lambda g: tag in g)]
            picks = picks.sort_values(["curated", "popularity"], ascending=False)
            base = picks.track_name.str.lower().str.split(" (", regex=False).str[0] + "|" + picks.artists
            idx = picks[~base.duplicated()].index[:12]  # one version of each song
            song_row(idx[:6], f"g1-{tag}")
            song_row(idx[6:12], f"g2-{tag}")
    else:
        label = st.selectbox("Genre", ["Choose a genre…", *movie_genres()], key="movie_genre", label_visibility="collapsed")
        if label != "Choose a genre…":
            picks = movies[movies.listed_in.str.split(", ").map(lambda g: label in g)]
            idx = picks.sort_values("release_year", ascending=False).index[:12]
            movie_row(idx[:6], f"mg1-{label}")
            movie_row(idx[6:12], f"mg2-{label}")


def screen_name(t):
    """'Love Aaj Kal (2020)', or just the title when the year isn't known."""
    return f"{t['title']} ({t['year']})" if t.get("year") else t["title"]


def _squash(text):
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


@st.cache_data(show_spinner=False)
def _keys(kind):
    col = movies.title if kind == "movies" else songs.track_name
    return col.map(_squash)


def search(kind, q, limit):
    """Forgiving search: ignores case, spaces and punctuation, and allows small typos."""
    df = movies if kind == "movies" else songs
    key, keys = _squash(q), _keys(kind)
    if not key:
        return df.index[:0]
    hits = df[keys.str.contains(key, regex=False)]
    if len(hits) == 0:  # nothing exact: fall back to close spellings
        close = difflib.get_close_matches(key, keys.unique().tolist(), n=limit, cutoff=0.75)
        hits = df[keys.isin(close)]
    if "popularity" in hits:  # songs we've analysed first, then the most popular
        hits = hits.sort_values(["curated", "popularity"], ascending=False)
    return hits.index[:limit]


def chips(moods, color=""):
    return "".join(f'<span class="mv-chip {color}">{html.escape(m)}</span>' for m in moods)


# ---------- cards ----------
def movie_card(i, key):
    r = movies.loc[i]
    url = cached_poster(r.title, int(r.release_year), r.type == "TV Show", bool(KEYS["tmdb"] or KEYS["omdb"]))
    if url:
        wide_image(url)
    else:
        kind = "mv-show" if r.type == "TV Show" else "mv-movie"
        st.markdown(f'<div class="mv-card {kind}">{html.escape(r.title)}<small>{r.type} · {r.release_year}</small></div>',
                    unsafe_allow_html=True)
    wide_button("Open", key=key, on_click=go, args=("Movies", i))


def song_card(i, key, caption=""):
    r = songs.loc[i]
    st.markdown(f'<div class="mv-card mv-song">{html.escape(r.track_name[:48])}'
                f'<small>{html.escape(r.artists.replace(";", ", ")[:40])}</small></div>', unsafe_allow_html=True)
    if caption:
        st.markdown(f'<div class="mv-muted">{html.escape(caption)}</div>', unsafe_allow_html=True)
    wide_button("Play", key=key, on_click=go, args=("Music", None, i))


def movie_row(idxs, prefix, n=6):
    idxs = list(idxs)[:n]
    if not idxs:
        st.markdown('<div class="mv-muted">Nothing here yet.</div>', unsafe_allow_html=True)
        return
    for col, i in zip(st.columns(n), idxs):
        with col:
            movie_card(i, f"{prefix}-{i}")


def song_row(idxs, prefix, n=6, captions=None):
    idxs = list(idxs)[:n]
    if not idxs:
        st.markdown('<div class="mv-muted">Nothing here yet.</div>', unsafe_allow_html=True)
        return
    for k, (col, i) in enumerate(zip(st.columns(n), idxs)):
        with col:
            song_card(i, f"{prefix}-{i}", captions[k] if captions else "")


# ---------- top bar ----------
left, right = st.columns([1, 3])
with left:
    st.markdown('<div class="mv-logo"><span class="r">C</span>u<span class="g">e</span><div class="mv-muted" style="font-size:14px;font-weight:500;letter-spacing:0">Movies and Music Explorer</div></div>', unsafe_allow_html=True)
with right:
    st.radio("Go to", ["Home", "Movies", "Music", "Mood Bridge", "Open Library"], key="page", horizontal=True,
             label_visibility="collapsed")


# ---------- built-in help ----------
INFO = {
    "vibe_now": "Cue looks at the last few songs you opened (newest count most) and works out your mood right now. "
                "The songs and movies below match that mood and the sound of what you’ve been playing.",
    "because": "Titles similar to the ones you opened, based on genre, cast, director, country and plot.",
    "screens": "Songs linked to the film or show they come from. Press Play to see the film, and whether it’s on Netflix.",
    "understand": "Songs whose lyrics have been analysed for meaning (for example playful, devoted, heartbreak), "
                  "not just sound. These give the most accurate vibe matches.",
    "romance": "A starting point: Netflix titles in a romantic mood. Open a few titles and this becomes "
               "“Because you watched”.",
    "search": "Search ignores capitals, spaces and small spelling mistakes. Songs show the film they come from.",
    "similar": "Titles most like this one, found by comparing genre, cast, director, country and plot (TF-IDF + cosine similarity).",
    "ost": "Songs from this title’s soundtrack, found from hand-checked links and song or album names.",
    "same_mood": "Songs in the same mood as this title, through the Mood Bridge’s 12 shared moods.",
    "genre": "Pick a genre to see its most popular songs or titles. Songs Cue understands are shown first.",
    "vibe_card": "What the song is about (from its lyrics), its mood tags, and its sound: energy, happiness (valence) "
                 "and danceability. Songs without analysed lyrics get moods guessed from their sound.",
    "trace": "The film or show this song comes from, and whether it’s on Netflix. “Verified” links were checked by hand; "
             "“auto” links come from the song or album name.",
    "slider": "Move left to match songs mostly by how they sound, right to match mostly by what they mean.",
    "up_next": "Songs that match this one in sound and meaning. The % shows how close the match is.",
    "filtered": "Songs that sound similar but mean something different, so Cue doesn’t recommend them.",
    "sounds_like": "Songs with the closest sound (energy, tempo, happiness and more), whatever their meaning.",
    "watch_mood": "Movies and shows in the same mood as this song, through the Mood Bridge.",
}

PAGE_INTRO = {
    "Home": "Welcome to Cue, where movies and music meet. Search anything, see your current vibe, and find songs linked "
            "to their films. Use the menu at the top to explore. Look for the ⓘ buttons to learn what each part does.",
    "Movies": "Pick a movie or show to see similar titles, songs from it and songs in the same mood. "
              "Browse Netflix categories at the bottom.",
    "Music": "Pick a song to play it and see its vibe card. Cue matches songs by sound and meaning; use the slider "
             "to choose which matters more. Trace to screen shows the film it comes from.",
    "Mood Bridge": "Choose one or more moods and Cue gives you something to watch and something to play for it.",
    "Open Library": "Free, legal films and music that play in full: public-domain classics and Creative Commons recordings.",
}


_INFO_COUNT = [0]  # gives every ⓘ button on a page its own stable key


if hasattr(st, "dialog"):
    @st.dialog("ⓘ What is this?")
    def info_popup(title, key):
        st.markdown(f"### {title}")
        st.markdown(INFO[key])
        if st.button("Got it", type="primary", key="info-got-it"):
            st.rerun()
else:
    info_popup = None


def info(key, title):
    """A small ⓘ button that opens a pop-up explaining one feature; 'Got it' closes it."""
    _INFO_COUNT[0] += 1
    if st.button("ⓘ", key=f"info-{key}-{_INFO_COUNT[0]}", help=f"What is {title}?"):
        if info_popup:
            info_popup(title, key)
        else:
            st.caption(INFO[key])


def section(title, key, small=False):
    """A heading with an ⓘ button beside it."""
    left, right = st.columns([14, 1], vertical_alignment="center") if VALIGN else st.columns([14, 1])
    with left:
        st.markdown(f"**{title}**") if small else st.subheader(title)
    with right:
        info(key, title)


VALIGN = "vertical_alignment" in inspect.signature(st.columns).parameters  # newer Streamlit only


if hasattr(st, "dialog"):
    @st.dialog("ⓘ About this page")
    def intro_popup(page):
        st.markdown(f"### {page}")
        st.markdown(PAGE_INTRO[page])
        if st.button("Got it", type="primary"):
            st.rerun()
else:
    intro_popup = None


def page_intro(page):
    """Explain each page once, the first time it is opened."""
    seen = ss.setdefault("seen_pages", set())
    if page in seen:
        return
    seen.add(page)
    if intro_popup:
        intro_popup(page)
    else:
        st.info(PAGE_INTRO[page])


def tip(text):
    st.markdown(f'<div class="mv-muted" style="margin-bottom:8px">💡 {text}</div>', unsafe_allow_html=True)


# ---------- pages ----------
def home():
    st.markdown('<div class="mv-hero"><h1>For the love of movies and music.</h1>'
                '<p>One place that learns from what you watch <i>and</i> what you play.</p></div>',
                unsafe_allow_html=True)
    page_intro("Home")

    q = st.text_input("Search", placeholder="Search a movie, show or song…", label_visibility="collapsed")
    if q:
        mm = list(search("movies", q, 6))
        sm = list(search("songs", q, 6))
        traces = [tracer.trace(i) for i in sm]
        # a song's film or show belongs in the movie results too
        for t in traces:
            if t and t["netflix_idx"] is not None and t["netflix_idx"] not in mm:
                mm.append(int(t["netflix_idx"]))
        section("Movies and shows", "search")
        if mm:
            movie_row(mm, "srch-m")
        else:
            off = [f"{songs.at[i, 'track_name']} is from {screen_name(t)}" for i, t in zip(sm, traces) if t]
            msg = ("; ".join(off) + ", which isn’t in the Netflix catalogue.") if off else "No matching titles."
            st.markdown(f'<div class="mv-muted">{html.escape(msg)}</div>', unsafe_allow_html=True)
        st.subheader("Songs")
        song_row(sm, "srch-s", captions=[f"From {screen_name(t)}" if t else "" for t in traces])
        return

    vibe = music_rec.current_vibe(ss.played)
    section("Your vibe right now", "vibe_now")
    if not vibe:
        st.markdown('<div class="mv-muted">Open a few songs with <b>Play</b> (or pick them on the Music page) and '
                    'Cue will learn the mood you’re in right now.</div>', unsafe_allow_html=True)
    else:
        top = list(vibe)[:3]
        recent = ", ".join(songs.at[i, "track_name"] for i in ss.played[-3:][::-1])
        st.markdown(chips(top, "green") + f'<div class="mv-muted">Based on {html.escape(recent)}</div>',
                    unsafe_allow_html=True)
        song_row(music_rec.for_vibe(top, exclude=ss.played, history=ss.played).index, "vibe-s")
        section("Watch this mood", "watch_mood", small=True)
        movie_row(movies_for_moods(movies, top, exclude=ss.watched).index, "vibe-m")

    if ss.watched:
        last = ss.watched[-1]
        section(f"Because you watched {movies.at[last, 'title']}", "because")
        movie_row(movie_rec.for_history(ss.watched).index, "byw")

    section("Songs from screens", "screens")
    traced = tracer.all_traced().sort_values("popularity", ascending=False)
    song_row(traced.index, "screens", captions=[f"From {t}" for t in traced.screen_title])

    section("Songs we understand", "understand")
    st.markdown('<div class="mv-muted">Lyrics analysed for meaning, not just sound.</div>', unsafe_allow_html=True)
    cur = songs[songs.curated].sort_values("popularity", ascending=False)
    song_row(cur.index, "cur")

    if not ss.watched:
        section("Romance on Netflix", "romance")
        movie_row(movies_for_moods(movies, ["romantic"]).index, "rom")


def movie_page():
    page_intro("Movies")
    tip("Search or pick a title. Below it: similar titles, songs from it and songs in the same mood. "
        "Browse Netflix categories at the bottom.")
    q = st.text_input("Find a movie or show", placeholder="Try Love Aaj Kal, Kota Factory, Stranger Things…")
    options = list(search("movies", q, 40)) if q else movies.index.tolist()
    if ss.movie not in options:
        options = [ss.movie] + options
    ss.movie_pick = ss.movie
    pick = st.selectbox("Title", options, key="movie_pick", on_change=on_movie_pick, label_visibility="collapsed",
                        format_func=lambda i: f"{movies.at[i, 'title']} ({movies.at[i, 'release_year']})")
    r = movies.loc[pick]

    c1, c2 = st.columns([1, 3])
    with c1:
        url = cached_poster(r.title, int(r.release_year), r.type == "TV Show", bool(KEYS["tmdb"] or KEYS["omdb"]))
        if url:
            wide_image(url)
        else:
            st.markdown(f'<div class="mv-card {"mv-show" if r.type == "TV Show" else "mv-movie"}">'
                        f'{html.escape(r.title)}<small>{r.type} · {r.release_year}</small></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f"## {r.title}")
        st.markdown(f'<div class="mv-muted">{r.type} · {r.release_year} · {r.rating} · {r.duration} · {html.escape(r.listed_in)}</div>',
                    unsafe_allow_html=True)
        st.write(r.description)
        if r.cast:
            st.markdown(f'<div class="mv-muted">With {html.escape(", ".join(r.cast.split(", ")[:5]))}</div>', unsafe_allow_html=True)
        st.markdown(chips(r.moods, "red"), unsafe_allow_html=True)

    section("Because you watched this", "similar")
    movie_row(movie_rec.similar(pick, 6).index, "sim")

    sound = tracer.songs_for(pick)
    if len(sound):
        section("Songs from this title", "ost")
        song_row(sound.index, "ost")

    if r.moods:
        section("Songs in the same mood", "same_mood")
        song_row(music_rec.for_vibe(r.moods).index, "moodsongs")

    genre_browser("movies")


def music_page():
    page_intro("Music")
    tip("Search or pick a song. The slider decides whether matches follow the sound or the meaning; "
        "“Filtered out” shows songs that sound alike but mean something else. Genres are at the bottom.")
    q = st.text_input("Find a song", placeholder="Try PS5, Kesariya, Night Changes…")
    if q:
        pool = list(search("songs", q, 40))
    else:
        pool = songs[songs.curated].sort_values("popularity", ascending=False).index[:40].tolist()
    if ss.song not in pool:
        pool = [ss.song] + pool
    ss.song_pick = ss.song
    pick = st.selectbox("Song", pool, key="song_pick", on_change=on_song_pick,
                        format_func=lambda i: songs.at[i, "label"], label_visibility="collapsed")
    r = songs.loc[pick]

    left, right = st.columns([1.1, 1])
    with left:
        st.markdown(f"## {r.track_name}")
        st.markdown(f'<div class="mv-muted">{html.escape(r.artists.replace(";", ", "))} · {html.escape(str(r.album_name))}</div>',
                    unsafe_allow_html=True)
        if r.track_id:
            components.iframe(f"https://open.spotify.com/embed/track/{r.track_id}", height=152)

        box = '<div class="mv-box"><b>Vibe card</b><br>'
        if r.summary:
            box += f'<div style="margin:6px 0 8px">{html.escape(r.summary)}</div>'
        else:
            box += '<div class="mv-muted" style="margin:6px 0 8px">Lyrics not analysed yet, so this mood is guessed from the sound.</div>'
        box += chips(r.moods, "green")
        if r.track_id:
            for name, val, col in [("Energy", r.energy, "#B3262E"), ("Happiness (valence)", r.valence, "#1E8A52"),
                                   ("Danceability", r.danceability, "#14161C")]:
                box += (f'<div class="mv-muted" style="margin-top:8px">{name}</div>'
                        f'<div class="mv-bar"><div style="width:{int(val * 100)}%;background:{col}"></div></div>')
        st.markdown(box + "</div>", unsafe_allow_html=True)
        info("vibe_card", "Vibe card")

        t = tracer.trace(pick)
        if t:
            on_nf = t["netflix_idx"] is not None
            msg = (f'<div class="mv-box"><b>Trace to screen</b><br>From <b>{html.escape(t["title"])}</b> '
                   + (f'({t["year"]}, {t["type"]}). ' if t["year"] else f'({t["type"]}). ')
                   + ("Available on Netflix." if on_nf else "Not in the Netflix catalogue.")
                   + (f'<div class="mv-muted">{html.escape(t["note"])}</div>' if t["note"] else "")
                   + f'<div class="mv-muted">Link: {t["source"]}</div></div>')
            st.markdown(msg, unsafe_allow_html=True)
            info("trace", "Trace to screen")
            if on_nf:
                st.button(f"Watch {t['title']}", on_click=go, args=("Movies", t["netflix_idx"]))

    with right:
        w = st.slider("Match by: sound ← → meaning", 0, 100, 60, step=5, help=INFO["slider"]) / 100
        match, filtered = music_rec.vibe_match(pick, meaning_weight=w)
        section("Up next, same vibe", "up_next", small=True)
        for i, row in match.head(5).iterrows():
            c1, c2 = st.columns([4, 1])
            c1.markdown(f'{html.escape(row.track_name)} <span class="mv-muted">· {html.escape(row.artists.split(";")[0])} · '
                        f'{int(row.score * 100)}% match</span>', unsafe_allow_html=True)
            c2.button("Play", key=f"up-{i}", on_click=go, args=("Music", None, i))
        if len(filtered):
            section("Filtered out", "filtered", small=True)
            for _, row in filtered.iterrows():
                st.markdown(f'<div class="mv-out">{html.escape(row.track_name)}: similar sound, but it’s about '
                            f'{", ".join(row.themes)}, not {", ".join(r.themes)}.</div>', unsafe_allow_html=True)

    section("Sounds like", "sounds_like")
    song_row(music_rec.sounds_like(pick, 6).index, "sl")
    section("Watch this mood", "watch_mood")
    movie_row(movies_for_moods(movies, r.moods).index, "song-mood")
    genre_browser("music")


def bridge_page():
    page_intro("Mood Bridge")
    st.markdown("## Mood Bridge")
    st.markdown('<div class="mv-muted">Pick a mood. Get something to watch and something to play.</div>',
                unsafe_allow_html=True)
    default = list(music_rec.current_vibe(ss.played))[:2] or ["romantic"]
    moods = st.multiselect("Moods", MOODS, default=default, label_visibility="collapsed")
    if not moods:
        return
    st.subheader("Watch")
    movie_row(movies_for_moods(movies, moods, exclude=ss.watched).index, "br-m")
    st.subheader("Play")
    song_row(music_rec.for_vibe(moods, exclude=ss.played, history=ss.played).index, "br-s")


COMMONS = "https://commons.wikimedia.org/wiki/Special:FilePath/"


def open_library_page():
    page_intro("Open Library")
    st.markdown("## Open Library")
    st.markdown('<div class="mv-muted">Free, legal films and music that play in full: public-domain classics and '
                'Creative Commons recordings from Wikimedia Commons.</div>', unsafe_allow_html=True)
    lib = open_library()
    moods = st.multiselect("Filter by mood", MOODS, label_visibility="collapsed", placeholder="Filter by mood…")
    if moods:
        lib = lib[lib.moods.map(lambda m: bool(set(m) & set(moods)))]
    if lib.empty:
        st.markdown('<div class="mv-muted">Nothing in that mood yet.</div>', unsafe_allow_html=True)
    for kind, label in [("Movie", "Watch"), ("Song", "Listen")]:
        part = lib[lib.kind == kind]
        if part.empty:
            continue
        st.subheader(label)
        for r in part.itertuples():
            st.markdown(f'<div class="mv-box"><b>{html.escape(r.title)}</b> '
                        f'<span class="mv-muted">· {html.escape(r.creator)} · {r.year}</span><br>'
                        f'{html.escape(r.description)}<br>{chips(r.moods, "red" if kind == "Movie" else "green")}'
                        f'<div class="mv-muted">{html.escape(r.license)} · {html.escape(r.credit)}</div></div>',
                        unsafe_allow_html=True)
            url = COMMONS + r.file
            if kind == "Movie":
                st.video(url)
            else:
                st.audio(url)


{"Home": home, "Movies": movie_page, "Music": music_page, "Mood Bridge": bridge_page,
 "Open Library": open_library_page}[ss.page]()
