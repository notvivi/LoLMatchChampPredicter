from lib import match_scraping_utils as utils

YEAR = 2026
LIMIT = 500

REQUEST_DELAY = 3.0
RATELIMIT_WAIT = 60.0

LEAGUES = {
    "LPL": {
        "tournament_like": "LPL 2026%",
        "overview_pages": [
            "LPL/2026 Season/Split 1",
            "LPL/2026 Season/Split 1 Playoffs",
        ],
    },
    "LEC": {
        "tournament_like": "LEC 2026%",
        "overview_pages": [
            "LEC/2026 Season/Versus Season",
            "LEC/2026 Season/Versus Playoffs",
        ],
    },
    "LCS": {
        "tournament_like": "LCS 2026%",
        "overview_pages": [
            "LCS/2026 Season/Lock-In",
            "LCS/2026 Season/Spring Season",
            "LCS/2026 Season/Spring Playoffs",
        ],
    },
    "LCK": {
        "tournament_like": "LCK%2026%",
        "overview_pages": [
            "LCK/2026 Season/Cup",
            "LCK/2026 Season/Rounds 1-2",
            "LCK/2026 Season/Road to MSI",
            "LCK/2026 Season/Rounds 3-4",
            "LCK/2026 Season/Season Play-In",
            "LCK/2026 Season/Season Playoffs",
        ],
    },
}

utils.get_all_leagues_dataset(LEAGUES, YEAR, limit=LIMIT, ratelimit_wait=RATELIMIT_WAIT, request_delay=REQUEST_DELAY)