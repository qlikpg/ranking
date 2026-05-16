import re
import sys
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from io import StringIO

BASE_URL = "https://www.pzlow.pl"
TERMINARZ_URL = "https://www.pzlow.pl/strzelectwo/terminarze-centralny/"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
}


def configure_utf8_output():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


configure_utf8_output()


def clean_text(text):
    return " ".join(str(text).replace("\xa0", " ").split()).strip()


def fetch_html(url):
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def get_url_from_cell(cell):
    a = cell.find("a", href=True)
    if a:
        return urljoin(BASE_URL, a["href"])

    text = clean_text(cell.get_text(" ", strip=True))
    match = re.search(r"https?://\S+", text)
    if match:
        return match.group(0)

    return ""


def flatten_columns(df):
    """
    Zamienia wielopoziomowe nagłówki pandas na proste nazwy kolumn.
    """
    if isinstance(df.columns, pd.MultiIndex):
        new_cols = []
        for col in df.columns:
            parts = [clean_text(x) for x in col if str(x) != "nan"]
            new_cols.append(parts[-1] if parts else "")
        df.columns = new_cols
    else:
        df.columns = [clean_text(c) for c in df.columns]

    return df


def normalize_result_table(df):
    df = df.copy()
    df = flatten_columns(df)

    rename_map = {
        "LP": "lp",
        "L.P.": "lp",
        "Lp": "lp",
        "Nazwisko Imię": "zawodnik",
        "Nazwisko i Imię": "zawodnik",
        "Nazwisko i imię": "zawodnik",
        "Kl": "klasa",
        "Kl.": "klasa",
        "Okręg": "okreg",
        "Okreg": "okreg",
        "Krąg": "krag",
        "Krag": "krag",
        "Oś": "os",
        "Os": "os",
        "MOP": "mop",
        "Śrut": "srut",
        "Srut": "srut",
        "Dzik": "dzik",
        "Rogacz": "rogacz",
        "Kula": "kula",
        "Razem": "razem",
    }

    df = df.rename(columns=rename_map)

    needed = ["zawodnik", "okreg", "razem"]
    if not all(col in df.columns for col in needed):
        return pd.DataFrame()

    df = df[df["zawodnik"].notna()].copy()
    df["zawodnik"] = df["zawodnik"].apply(clean_text)
    df = df[df["zawodnik"].str.lower() != "nazwisko imię"].copy()
    df = df[df["zawodnik"].str.lower() != "nazwisko i imię"].copy()
    df = df[df["zawodnik"] != ""].copy()

    for col in ["lp", "krag", "os", "mop", "srut", "dzik", "rogacz", "kula", "razem"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[df["razem"].notna()].copy()

    for col in ["klasa", "okreg"]:
        if col in df.columns:
            df[col] = df[col].apply(clean_text)
        else:
            df[col] = ""

    return df


def pobierz_zawody_z_wynikami():
    soup = BeautifulSoup(fetch_html(TERMINARZ_URL), "html.parser")

    wyniki = []
    tables = soup.find_all("table")

    print("Liczba tabel terminarza:", len(tables))

    for table_no, table in enumerate(tables, start=1):
        rows = table.find_all("tr")

        if not rows:
            continue

        header_cells = rows[0].find_all(["th", "td"])
        headers_table = [clean_text(cell.get_text(" ", strip=True)) for cell in header_cells]

        required_cols = ["Lp", "Nazwa zawodów", "ZO PZŁ", "Strzelnica", "Data zawodów", "Wyniki"]

        if not all(col in headers_table for col in required_cols):
            continue

        idx_lp = headers_table.index("Lp")
        idx_nazwa = headers_table.index("Nazwa zawodów")
        idx_zo = headers_table.index("ZO PZŁ")
        idx_strzelnica = headers_table.index("Strzelnica")
        idx_data = headers_table.index("Data zawodów")
        idx_wyniki = headers_table.index("Wyniki")

        for row in rows[1:]:
            cells = row.find_all("td")

            if len(cells) <= idx_wyniki:
                continue

            url_wynikow = get_url_from_cell(cells[idx_wyniki])

            if not url_wynikow:
                continue

            if str(url_wynikow).lower().startswith("brak"):
                continue

            data_zawodow = clean_text(cells[idx_data].get_text(" ", strip=True))

            rok_match = re.search(r"(20\d{2})", data_zawodow)
            rok = rok_match.group(1) if rok_match else ""

            wyniki.append({
                "rok": rok,
                "nr_tabeli_terminarza": table_no,
                "lp_zawodow": clean_text(cells[idx_lp].get_text(" ", strip=True)),
                "nazwa_zawodow": clean_text(cells[idx_nazwa].get_text(" ", strip=True)),
                "zo_pzl_zawody": clean_text(cells[idx_zo].get_text(" ", strip=True)),
                "strzelnica": clean_text(cells[idx_strzelnica].get_text(" ", strip=True)),
                "data_zawodow": data_zawodow,
                "url_wynikow": url_wynikow,
            })

    df = pd.DataFrame(wyniki)

    if not df.empty:
        df = df.drop_duplicates(subset=["url_wynikow"]).copy()
        df = df.sort_values(
            ["rok", "data_zawodow", "nazwa_zawodow"],
            ascending=[False, True, True]
        )

    return df


def pobierz_wyniki_zawodow(zawody_row):
    url = zawody_row["url_wynikow"]

    try:
        tables = pd.read_html(StringIO(fetch_html(url)))
    except ValueError:
        return pd.DataFrame()

    all_results = []

    for i, table in enumerate(tables, start=1):
        df = normalize_result_table(table)

        if df.empty:
            continue

        df["nr_tabeli"] = i
        df["rok"] = zawody_row.get("rok", "")
        df["nazwa_zawodow"] = zawody_row["nazwa_zawodow"]
        df["data_zawodow"] = zawody_row["data_zawodow"]
        df["strzelnica"] = zawody_row["strzelnica"]
        df["url_wynikow"] = zawody_row["url_wynikow"]

        all_results.append(df)

    if not all_results:
        return pd.DataFrame()

    return pd.concat(all_results, ignore_index=True)


def build_average_ranking(results: pd.DataFrame) -> pd.DataFrame:
    """
    Ranking zawodników według średniej wyniku ze wszystkich startów.
    Bez względu na klasę.
    """
    df = results.copy()
    df = df[df["razem"].notna()].copy()

    ranking = (
        df
        .groupby(["zawodnik", "okreg"], dropna=False)
        .agg(
            srednia_wynikow=("razem", "mean"),
            suma_punktow=("razem", "sum"),
            liczba_startow=("razem", "count"),
            najlepszy_wynik=("razem", "max"),
            najgorszy_wynik=("razem", "min"),
        )
        .reset_index()
    )

    ranking["srednia_wynikow"] = ranking["srednia_wynikow"].round(2)

    ranking = ranking.sort_values(
        ["srednia_wynikow", "najlepszy_wynik", "liczba_startow", "suma_punktow"],
        ascending=[False, False, False, False]
    )

    ranking.insert(0, "miejsce", range(1, len(ranking) + 1))

    return ranking


def assign_wawrzyn(points: float, plec: str = "M") -> str:
    """
    Progi Wawrzynu:
    Kobiety:
    1260-1305 brąz
    1306-1350 srebro
    1351-1410 złoto
    >=1411 złoto z diamentem

    Mężczyźni:
    1320-1364 brąz
    1365-1409 srebro
    1410-1454 złoto
    >=1455 złoto z diamentem
    """
    if pd.isna(points):
        return ""

    plec = str(plec).upper().strip()

    if plec == "K":
        if points >= 1411:
            return "złoty Wawrzyn Strzelecki z diamentem"
        elif points >= 1351:
            return "złoty Wawrzyn Strzelecki"
        elif points >= 1306:
            return "srebrny Wawrzyn Strzelecki"
        elif points >= 1260:
            return "brązowy Wawrzyn Strzelecki"
        else:
            return ""
    else:
        if points >= 1455:
            return "złoty Wawrzyn Strzelecki z diamentem"
        elif points >= 1410:
            return "złoty Wawrzyn Strzelecki"
        elif points >= 1365:
            return "srebrny Wawrzyn Strzelecki"
        elif points >= 1320:
            return "brązowy Wawrzyn Strzelecki"
        else:
            return ""


def build_wawrzyn_ranking(results: pd.DataFrame) -> pd.DataFrame:
    """
    Ranking Wawrzynu:
    suma 3 najlepszych wyników zawodnika.
    """
    df = results.copy()
    df = df[df["razem"].notna()].copy()

    df["plec"] = df["nr_tabeli"].apply(lambda x: "K" if int(x) == 1 else "M")

    df = df.sort_values(
        ["zawodnik", "okreg", "plec", "razem"],
        ascending=[True, True, True, False]
    )

    df["nr_wyniku_zawodnika"] = df.groupby(
        ["zawodnik", "okreg", "plec"]
    ).cumcount() + 1

    top3 = df[df["nr_wyniku_zawodnika"] <= 3].copy()

    ranking = (
        top3
        .groupby(["zawodnik", "okreg", "plec"], dropna=False)
        .agg(
            suma_3_najlepszych=("razem", "sum"),
            liczba_wynikow_do_rankingu=("razem", "count"),
            najlepszy_wynik=("razem", "max"),
            drugi_wynik=("razem", lambda x: sorted(x, reverse=True)[1] if len(x) >= 2 else None),
            trzeci_wynik=("razem", lambda x: sorted(x, reverse=True)[2] if len(x) >= 3 else None),
            zawody_wliczone=("nazwa_zawodow", lambda x: " | ".join(map(str, x))),
        )
        .reset_index()
    )

    ranking["wawrzyn"] = ranking.apply(
        lambda row: assign_wawrzyn(row["suma_3_najlepszych"], row["plec"]),
        axis=1
    )

    ranking = ranking.sort_values(
        ["suma_3_najlepszych", "najlepszy_wynik", "liczba_wynikow_do_rankingu"],
        ascending=[False, False, False]
    )

    ranking.insert(0, "miejsce", range(1, len(ranking) + 1))

    return ranking


def build_team_ranking(results: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Klasyfikacja drużynowa:
    średnia 6 najlepszych zawodników z danego okręgu.
    """
    df = results.copy()
    df = df[df["razem"].notna()].copy()

    players = (
        df
        .groupby(["okreg", "zawodnik"], dropna=False)
        .agg(
            srednia_zawodnika=("razem", "mean"),
            liczba_startow=("razem", "count"),
            najlepszy_wynik=("razem", "max"),
            suma_punktow=("razem", "sum"),
        )
        .reset_index()
    )

    players["srednia_zawodnika"] = players["srednia_zawodnika"].round(2)

    players = players.sort_values(
        ["okreg", "srednia_zawodnika", "najlepszy_wynik", "liczba_startow", "suma_punktow"],
        ascending=[True, False, False, False, False]
    )

    players["nr_w_okregu"] = players.groupby("okreg").cumcount() + 1

    top6 = players[players["nr_w_okregu"] <= 6].copy()

    team_ranking = (
        top6
        .groupby("okreg", dropna=False)
        .agg(
            srednia_6_najlepszych=("srednia_zawodnika", "mean"),
            liczba_zawodnikow_w_rankingu=("zawodnik", "count"),
            suma_srednich_6_najlepszych=("srednia_zawodnika", "sum"),
        )
        .reset_index()
    )

    team_ranking["srednia_6_najlepszych"] = team_ranking["srednia_6_najlepszych"].round(2)
    team_ranking["suma_srednich_6_najlepszych"] = team_ranking["suma_srednich_6_najlepszych"].round(2)

    sklad = (
        top6
        .pivot(index="okreg", columns="nr_w_okregu", values="zawodnik")
        .reset_index()
    )

    sklad.columns = [
        "okreg" if col == "okreg" else f"zawodnik_{int(col)}"
        for col in sklad.columns
    ]

    team_ranking = team_ranking.merge(sklad, on="okreg", how="left")

    team_ranking = team_ranking.sort_values(
        ["srednia_6_najlepszych", "liczba_zawodnikow_w_rankingu", "suma_srednich_6_najlepszych"],
        ascending=[False, False, False]
    )

    team_ranking.insert(0, "miejsce", range(1, len(team_ranking) + 1))

    return team_ranking, top6


def main():
    df_zawody = pobierz_zawody_z_wynikami()
    print("Zawody z linkiem do wyników:", len(df_zawody))

    wszystkie_wyniki = []

    for idx, zawody_row in df_zawody.iterrows():
        print(f"Pobieram {idx + 1}/{len(df_zawody)}: {zawody_row['nazwa_zawodow']}")

        try:
            df = pobierz_wyniki_zawodow(zawody_row)

            if not df.empty:
                print("  Wyników:", len(df))
                wszystkie_wyniki.append(df)
            else:
                print("  Brak rozpoznanych tabel wyników")

        except Exception as e:
            print("  BŁĄD:", e)

        time.sleep(0.5)

    if not wszystkie_wyniki:
        print("Nie pobrano żadnych wyników.")
        return

    results = pd.concat(wszystkie_wyniki, ignore_index=True)

    average_ranking = build_average_ranking(results)
    wawrzyn_ranking = build_wawrzyn_ranking(results)
    team_ranking, team_top6 = build_team_ranking(results)

    output_file = "ranking_pzlow_lata_ubiegle.xlsx"

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        results.to_excel(writer, sheet_name="Wszystkie wyniki", index=False)
        average_ranking.to_excel(writer, sheet_name="Średnia wyników", index=False)
        wawrzyn_ranking.to_excel(writer, sheet_name="Wawrzyn", index=False)
        team_ranking.to_excel(writer, sheet_name="Drużynowa", index=False)
        team_top6.to_excel(writer, sheet_name="Drużynowa top 6", index=False)

    print()
    print("Łącznie wyników:", len(results))
    print("Zapisano plik:", output_file)


if __name__ == "__main__":
    main()
