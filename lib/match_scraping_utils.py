import time
import pandas as pd
from mwrogue.auth_credentials import AuthCredentials
from mwrogue.esports_client import EsportsClient

BOT_USER = "Notvivi4@MujScraper"
BOT_PASSWORD = "53oeb2enp0pa7q88pkciasineq2gogd9"

def cargo_query_safe(site, tables, fields, where, join_on=None, limit=500, ratelimit_wait=60, request_delay=1.0):
    all_rows = []
    offset = 0

    while True:
        for attempt in range(5):
            try:
                kwargs = dict(
                    tables=tables,
                    fields=fields,
                    where=where,
                    limit=limit,
                    offset=offset,
                )
                if join_on:
                    kwargs["join_on"] = join_on
                response = site.cargo_client.query(**kwargs)
                time.sleep(request_delay)
                break
            except Exception as e:
                err = str(e)
                if "ratelimited" in err:
                    time.sleep(ratelimit_wait)
                else:
                    time.sleep(5)
        else:
            break

        if not response:
            break

        rows = [r.get("title", r) for r in response]
        all_rows.extend(rows)
        offset += limit

        if len(rows) < limit:
            break

    return pd.DataFrame(all_rows) if all_rows else pd.DataFrame()

def safe_numeric(df, col):
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    else:
        df[col] = pd.NA
    return df

def get_all_leagues_dataset(leagues, year, limit=500, ratelimit_wait=60, request_delay=1.0):
    credentials = AuthCredentials(username=BOT_USER, password=BOT_PASSWORD)
    site = EsportsClient("lol", credentials=credentials)

    all_dfs = []

    for league_name, config in leagues.items():
        df = get_league_dataset(site, league_name, config, limit, ratelimit_wait, request_delay)
        if not df.empty:
            all_dfs.append(df)

    if not all_dfs:
        return

    combined = pd.concat(all_dfs, ignore_index=True)

    output_cols = [
        "League",
        "GameId", "MatchId",
        "WinTeam", "LossTeam",
        "BestOf", "SeriesScore",
        "Gamelength",
        "Team1Gold", "Team2Gold",
        "Team1Kills", "Team2Kills",
    ]
    output_cols = [c for c in output_cols if c in combined.columns]
    dataset = combined[output_cols].copy()

    output_file = f"all_leagues_test_{year}_dataset.csv"
    dataset.to_csv(output_file, index=False)

def get_league_dataset(site, league_name, config, limit, ratelimit_wait, request_delay):
    tournament_filter = f"Tournament LIKE '{config['tournament_like']}'"

    games_df = cargo_query_safe(
        site,
        tables="ScoreboardGames",
        fields=(
            "GameId, MatchId, "
            "Team1, Team2, "
            "WinTeam, LossTeam, "
            "Team1Gold, Team2Gold, "
            "Team1Kills, Team2Kills, "
            "Gamelength"
        ),
        where=tournament_filter,
        limit=limit,
        ratelimit_wait=ratelimit_wait,
        request_delay=request_delay
    )

    if games_df.empty:
        return pd.DataFrame()

    if "Tournament" in games_df.columns:
        print(f"Tournament hodnoty: {games_df['Tournament'].unique().tolist()}")

    for col in ["Team1Gold", "Team2Gold", "Team1Kills", "Team2Kills"]:
        games_df = safe_numeric(games_df, col)

    games_df["League"] = league_name

    pages_in = ", ".join(f"'{p}'" for p in config["overview_pages"])
    schedule_where = f"OverviewPage IN ({pages_in})"

    schedule_df = cargo_query_safe(
        site,
        tables="MatchSchedule",
        fields="MatchId, BestOf, Team1Score, Team2Score, OverviewPage",
        where=schedule_where,
        limit=limit,
        ratelimit_wait=ratelimit_wait,
        request_delay=request_delay
    )

    if not schedule_df.empty:
        for col in ["BestOf", "Team1Score", "Team2Score"]:
            schedule_df = safe_numeric(schedule_df, col)

        schedule_df["SeriesScore"] = (
            schedule_df["Team1Score"].astype("Int64").astype(str)
            + "-"
            + schedule_df["Team2Score"].astype("Int64").astype(str)
        )

        schedule_dedup = (
            schedule_df[["MatchId", "BestOf", "SeriesScore"]]
            .drop_duplicates("MatchId")
        )

        games_df = games_df.merge(schedule_dedup, on="MatchId", how="left")

        missing_bo = games_df["BestOf"].isna().sum()
        if missing_bo > 0:
            print(f"{missing_bo} is missing BestOf")
    else:
        games_df["BestOf"] = pd.NA
        games_df["SeriesScore"] = pd.NA

    return games_df



