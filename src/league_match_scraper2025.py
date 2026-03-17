from lib import match_scraping_utils as utils

YEAR = 2025
LIMIT = 500

REQUEST_DELAY = 3.0
RATELIMIT_WAIT = 60.0

LEAGUES = {
    "LPL": {
        "tournament_like": "LPL 2025%",
        "overview_pages": [
            "LPL/2025 Season/Split 1",
            "LPL/2025 Season/Split 1 Playoffs",
            "LPL/2025 Season/Split 2 Placements",
            "LPL/2025 Season/Split 2",
            "LPL/2025 Season/Split 2 Playoffs",
            "LPL/2025 Season/Split 3",
            "LPL/2025 Season/Grand Finals",
            "LPL/2025 Season/Regional Finals",
        ],
    },
    "LEC": {
        "tournament_like": "LEC 2025%",
        "overview_pages": [
            "LEC/2025 Season/Winter Season",
            "LEC/2025 Season/Winter Playoffs",
            "LEC/2025 Season/Spring Season",
            "LEC/2025 Season/Spring Playoffs",
            "LEC/2025 Season/Summer Season",
            "LEC/2025 Season/Summer Playoffs",
        ],
    },
    "LTA_North": {
        "tournament_like": "LTA North 2025%",
        "overview_pages": [
            "LTA North/2025 Season/Split 1",
            "LTA North/2025 Season/Split 2",
            "LTA North/2025 Season/Split 2 Playoffs",
            "LTA/2025 Season/Split 1 Playoffs",
            "LTA/2025 Season/Regional Championship",
        ],
    },
    "LCK": {
        "tournament_like": "LCK%2025%",
        "overview_pages": [
            "LCK/2025 Season/Cup",
            "LCK/2025 Season/Rounds 1-2",
            "LCK/2025 Season/Road to MSI",
            "LCK/2025 Season/Rounds 3-5",
            "LCK/2025 Season/Season Play-In",
            "LCK/2025 Season/Season Playoffs",
        ],
    },
    "Worlds": {
        "tournament_like": "Worlds 2025%",
        "overview_pages": [
            "2025 Season World Championship/Play-In",
            "2025 Season World Championship/Main Event",
        ],
    },
}

utils.get_all_leagues_dataset(LEAGUES, YEAR, limit=LIMIT, ratelimit_wait=RATELIMIT_WAIT, request_delay=REQUEST_DELAY)