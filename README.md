import re
import time
from datetime import date

import pandas as pd

from ranking_pzlow_lata import pobierz_wyniki_zawodow, pobierz_zawody_z_wynikami


DATA_OD = date(2026, 5, 16)
DATA_DO = date(2026, 8, 1)
OKREG = "białystok"
OUTPUT_FILE = "bialystok_polfinal.xlsx"
EXPORT_EXCEL = False


def clean_text(text):
    return " ".join(str(text).replace("\xa0", " ").split()).strip()


def parse_event_dates(text: str) -> list[date]:
    """
    Wyciąga daty z zapisów typu:
    16.05.2026, 16-17.05.2026, 31.07-01.08.2026, 31.07.2026-01.08.2026.
    """
    text = clean_text(text)
    parsed = []

    def add_date(year, month, day):
        try:
            value = date(int(year), int(month), int(day))
        except ValueError:
            return
        if value not in parsed:
            parsed.append(value)

    for year, month, day in re.findall(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", text):
        add_date(year, month, day)

    for day1, day2, month, year in re.findall(
        r"(?<![.\-/])\b(\d{1,2})\s*[-–]\s*(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})\b",
        text,
    ):
        add_date(year, month, day1)
        add_date(year, month, day2)

    for day1, month1, day2, month2, year in re.findall(
        r"\b(\d{1,2})[.\-/](\d{1,2})\s*[-–]\s*(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})\b",
        text,
    ):
        add_date(year, month1, day1)
        add_date(year, month2, day2)

    for day, month, year in re.findall(r"\b(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})\b", text):
        add_date(year, month, day)

    return parsed


def event_in_date_range(data_zawodow: str) -> bool:
    dates = parse_event_dates(data_zawodow)
    return any(DATA_OD <= event_date <= DATA_DO for event_date in dates)


def filter_events_for_period(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events

    events = events.copy()
    events["daty_rozpoznane"] = events["data_zawodow"].apply(
        lambda value: ", ".join(d.isoformat() for d in parse_event_dates(value))
    )
    events = events[events["data_zawodow"].apply(event_in_date_range)].copy()
    events = events.sort_values(["data_zawodow", "nazwa_zawodow"]).reset_index(drop=True)
    return events


def build_bialystok_polfinal_ranking(results: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if results.empty:
        return pd.DataFrame(), pd.DataFrame()

    df = results.copy()
    df = df[df["razem"].notna()].copy()
    df = df[df["okreg"].str.lower().str.strip() == OKREG].copy()

    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Jeżeli zawodnik ma kilka wpisów w jednych zawodach, bierzemy najlepszy wynik.
    starts = (
        df
        .groupby(["zawodnik", "okreg", "nazwa_zawodow"], dropna=False)
        .agg(
            wynik=("razem", "max"),
            klasa=("klasa", "first"),
            data_zawodow=("data_zawodow", "first"),
            strzelnica=("strzelnica", "first"),
            url_wynikow=("url_wynikow", "first"),
        )
        .reset_index()
    )

    starts = starts.sort_values(
        ["zawodnik", "wynik", "data_zawodow"],
        ascending=[True, False, True],
    )
    starts["nr_wyniku_zawodnika"] = starts.groupby(["zawodnik", "okreg"]).cumcount() + 1

    top3 = starts[starts["nr_wyniku_zawodnika"] <= 3].copy()

    ranking = (
        top3
        .groupby(["zawodnik", "okreg"], dropna=False)
        .agg(
            suma_3_najlepszych=("wynik", "sum"),
            liczba_wynikow_do_rankingu=("wynik", "count"),
            najlepszy_1=("wynik", lambda x: sorted(x, reverse=True)[0] if len(x) >= 1 else None),
            najlepszy_2=("wynik", lambda x: sorted(x, reverse=True)[1] if len(x) >= 2 else None),
            najlepszy_3=("wynik", lambda x: sorted(x, reverse=True)[2] if len(x) >= 3 else None),
            zawody_wliczone=("nazwa_zawodow", lambda x: " | ".join(map(str, x))),
        )
        .reset_index()
    )

    all_starts = (
        starts
        .groupby(["zawodnik", "okreg"], dropna=False)
        .agg(
            liczba_startow=("wynik", "count"),
            wszystkie_starty=("nazwa_zawodow", lambda x: " | ".join(map(str, x))),
        )
        .reset_index()
    )

    ranking = ranking.merge(all_starts, on=["zawodnik", "okreg"], how="left")
    ranking["srednia_3_najlepszych"] = (
        ranking["suma_3_najlepszych"] / ranking["liczba_wynikow_do_rankingu"]
    ).round(2)

    top5 = starts[starts["nr_wyniku_zawodnika"] <= 5].copy()
    championship = (
        top5
        .groupby(["zawodnik", "okreg"], dropna=False)
        .agg(
            suma_5_najlepszych=("wynik", "sum"),
            liczba_wynikow_mistrzostwa=("wynik", "count"),
            najlepszy_wynik_mistrzostwa=("wynik", "max"),
        )
        .reset_index()
    )
    championship["srednia_5_najlepszych"] = (
        championship["suma_5_najlepszych"] / championship["liczba_wynikow_mistrzostwa"]
    ).round(2)
    championship = championship.sort_values(
        ["suma_5_najlepszych", "najlepszy_wynik_mistrzostwa", "liczba_wynikow_mistrzostwa"],
        ascending=[False, False, False],
    )
    championship["miejsce_mistrzostwa"] = range(1, len(championship) + 1)

    ranking = ranking.merge(
        championship[
            [
                "zawodnik",
                "okreg",
                "miejsce_mistrzostwa",
                "suma_5_najlepszych",
                "srednia_5_najlepszych",
                "liczba_wynikow_mistrzostwa",
            ]
        ],
        on=["zawodnik", "okreg"],
        how="left",
    )

    ranking = ranking.sort_values(
        ["suma_3_najlepszych", "najlepszy_1", "liczba_startow"],
        ascending=[False, False, False],
    )
    ranking.insert(0, "miejsce", range(1, len(ranking) + 1))

    ranking = ranking[
        [
            "miejsce",
            "zawodnik",
            "okreg",
            "suma_3_najlepszych",
            "srednia_3_najlepszych",
            "liczba_wynikow_do_rankingu",
            "liczba_startow",
            "najlepszy_1",
            "najlepszy_2",
            "najlepszy_3",
            "miejsce_mistrzostwa",
            "suma_5_najlepszych",
            "srednia_5_najlepszych",
            "liczba_wynikow_mistrzostwa",
            "zawody_wliczone",
            "wszystkie_starty",
        ]
    ]

    starts = starts.sort_values(["zawodnik", "wynik"], ascending=[True, False])
    return ranking, starts


def filter_events_with_bialystok_starts(events: pd.DataFrame, starts: pd.DataFrame) -> pd.DataFrame:
    if events.empty or starts.empty:
        return events.iloc[0:0].copy()

    event_urls = set(starts["url_wynikow"].dropna())
    return events[events["url_wynikow"].isin(event_urls)].copy().reset_index(drop=True)


def main():
    events = pobierz_zawody_z_wynikami()
    print("Zawody z linkiem do wyników:", len(events))

    events_in_period = filter_events_for_period(events)
    print(
        "Zawody w okresie",
        DATA_OD.strftime("%d.%m.%Y"),
        "-",
        DATA_DO.strftime("%d.%m.%Y") + ":",
        len(events_in_period),
    )

    all_results = []

    for idx, event_row in events_in_period.iterrows():
        print(f"Pobieram {idx + 1}/{len(events_in_period)}: {event_row['nazwa_zawodow']}")

        try:
            df = pobierz_wyniki_zawodow(event_row)

            if not df.empty:
                print("  Wyników:", len(df))
                all_results.append(df)
            else:
                print("  Brak rozpoznanych tabel wyników")

        except Exception as error:
            print("  BŁĄD:", error)

        time.sleep(0.5)

    if all_results:
        results = pd.concat(all_results, ignore_index=True)
    else:
        results = pd.DataFrame()

    ranking, starts = build_bialystok_polfinal_ranking(results)
    events_with_bialystok = filter_events_with_bialystok_starts(events_in_period, starts)

    print()
    print("Wyników z okręgu białostockiego:", len(starts))
    print("Zawodników w rankingu:", len(ranking))
    print("Zawody z zawodnikami z Białegostoku:", len(events_with_bialystok))

    try:
        from bialystok_polfinal_site import write_site_from_dataframes

        write_site_from_dataframes(ranking, starts, events_with_bialystok)
    except Exception as error:
        print("Nie udało się zbudować strony:", error)

    if EXPORT_EXCEL:
        with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
            ranking.to_excel(writer, sheet_name="Ranking półfinał", index=False)
            starts.to_excel(writer, sheet_name="Wyniki Białystok", index=False)
            events_with_bialystok.to_excel(writer, sheet_name="Zawody w okresie", index=False)

        print("Zapisano plik:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
