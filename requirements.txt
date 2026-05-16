import json
import sys
from html import escape
from pathlib import Path

import pandas as pd


SOURCE_FILE = Path("bialystok_polfinal.xlsx")
OUTPUT_DIR = Path("site")
OUTPUT_FILE = OUTPUT_DIR / "index.html"


def configure_utf8_output():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


configure_utf8_output()


def clean_value(value):
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def read_sheet(sheet_name):
    df = pd.read_excel(SOURCE_FILE, sheet_name=sheet_name)
    return [
        {column: clean_value(row[column]) for column in df.columns}
        for _, row in df.iterrows()
    ]


def dataframe_to_records(df):
    return [
        {column: clean_value(row[column]) for column in df.columns}
        for _, row in df.iterrows()
    ]


def to_json_script(name, value):
    data = json.dumps(value, ensure_ascii=False)
    data = data.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return f'<script type="application/json" id="{escape(name)}">{data}</script>'


def build_html(ranking, starts, events):
    total_starts = sum(int(row.get("liczba_startow") or 0) for row in ranking)
    team_six = ranking[:6]
    team_six_items = "\n".join(
        f"<li><span>{escape(str(row['zawodnik']))}</span><strong>{escape(str(row['srednia_3_najlepszych']))}</strong></li>"
        for row in team_six
    )
    if not team_six_items:
        team_six_items = "<li><span>Brak zawodników</span><strong>-</strong></li>"

    return f"""<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ranking Białystok - półfinał ligi</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17212b;
      --muted: #5c6975;
      --line: #d9e1e8;
      --surface: #ffffff;
      --soft: #f5f7f9;
      --brand: #0b5c7a;
      --brand-dark: #073d51;
      --green: #1d7a50;
      --gold: #b47716;
      --danger: #a73d31;
      --shadow: 0 12px 28px rgba(23, 33, 43, 0.08);
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: var(--ink);
      background: var(--soft);
      letter-spacing: 0;
    }}

    header {{
      background: #fff;
      border-bottom: 1px solid var(--line);
    }}

    .topbar {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 22px 20px 18px;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 18px;
      align-items: end;
    }}

    h1 {{
      margin: 0 0 6px;
      font-size: clamp(24px, 3vw, 38px);
      line-height: 1.08;
      font-weight: 800;
    }}

    .subhead {{
      margin: 0;
      color: var(--muted);
      font-size: 15px;
    }}

    .mark {{
      width: 76px;
      height: 76px;
      border: 1px solid var(--line);
      border-radius: 8px;
      display: grid;
      place-items: center;
      background:
        linear-gradient(145deg, rgba(11, 92, 122, 0.12), rgba(29, 122, 80, 0.08)),
        #fff;
      box-shadow: var(--shadow);
      position: relative;
      overflow: hidden;
    }}

    .mark::before {{
      content: "";
      width: 34px;
      height: 46px;
      border: 4px solid var(--brand);
      border-top-width: 8px;
      border-radius: 6px 6px 14px 14px;
      transform: translateY(2px);
    }}

    .mark::after {{
      content: "";
      position: absolute;
      width: 42px;
      height: 2px;
      background: var(--gold);
      transform: rotate(-28deg);
    }}

    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 22px 20px 42px;
    }}

    .stats {{
      display: grid;
      grid-template-columns: minmax(320px, 1.4fr) minmax(260px, .8fr);
      gap: 12px;
      margin-bottom: 18px;
    }}

    .stat {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px 16px;
      min-height: 86px;
    }}

    .stat span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }}

    .stat strong {{
      display: block;
      margin-top: 8px;
      font-size: 26px;
      line-height: 1.1;
    }}

    .stat small {{
      display: block;
      margin-top: 6px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.35;
    }}

    .stat.wide {{
      grid-column: auto;
      grid-row: span 1;
    }}

    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-top: 12px;
    }}

    .summary-grid div {{
      padding-right: 10px;
      border-right: 1px solid var(--line);
    }}

    .summary-grid div:last-child {{
      padding-right: 0;
      border-right: 0;
    }}

    .team-list {{
      list-style: none;
      margin: 10px 0 0;
      padding: 0;
      display: grid;
      gap: 5px;
    }}

    .team-list li {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 10px;
      align-items: baseline;
      color: var(--ink);
      font-size: 13px;
      line-height: 1.25;
    }}

    .team-list li span {{
      min-width: 0;
      overflow-wrap: anywhere;
    }}

    .team-list li strong {{
      margin: 0;
      color: var(--green);
      font-size: 14px;
      line-height: 1.25;
    }}

    .toolbar {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      display: grid;
      grid-template-columns: 1fr auto auto auto;
      gap: 10px;
      align-items: center;
      margin-bottom: 14px;
    }}

    input, select, button {{
      font: inherit;
    }}

    .search {{
      min-width: 0;
      height: 40px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 12px;
      background: #fff;
      color: var(--ink);
    }}

    .tabs {{
      display: inline-grid;
      grid-auto-flow: column;
      gap: 4px;
      padding: 4px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--soft);
    }}

    .tab {{
      border: 0;
      border-radius: 6px;
      min-height: 32px;
      padding: 0 12px;
      color: var(--muted);
      background: transparent;
      cursor: pointer;
      white-space: nowrap;
    }}

    .tab[aria-selected="true"] {{
      color: #fff;
      background: var(--brand);
    }}

    .action {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      height: 40px;
      border: 1px solid var(--brand);
      border-radius: 6px;
      padding: 0 12px;
      color: #fff;
      background: var(--brand);
      cursor: pointer;
      white-space: nowrap;
      text-decoration: none;
    }}

    .action.secondary {{
      color: var(--brand);
      background: #fff;
    }}

    .panel {{
      display: none;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      box-shadow: var(--shadow);
    }}

    .panel-tools {{
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      background: #fafcfd;
    }}

    .panel-tools select,
    .panel-tools button {{
      height: 36px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 10px;
      background: #fff;
      color: var(--ink);
    }}

    .panel-tools button {{
      min-width: 96px;
      cursor: pointer;
    }}

    .panel.active {{
      display: block;
    }}

    .table-wrap {{
      overflow: auto;
      max-height: 68vh;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 840px;
    }}

    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }}

    th {{
      position: sticky;
      top: 0;
      z-index: 1;
      background: #eef3f6;
      color: var(--brand-dark);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
      white-space: nowrap;
    }}

    .sort-btn {{
      width: 100%;
      border: 0;
      padding: 0;
      background: transparent;
      color: inherit;
      cursor: pointer;
      font: inherit;
      letter-spacing: inherit;
      text-transform: inherit;
      text-align: left;
    }}

    .sort-btn.number {{
      text-align: right;
    }}

    .sort-btn::after {{
      content: " ↕";
      color: var(--muted);
    }}

    .sort-btn[data-direction="asc"]::after {{
      content: " ↑";
      color: var(--brand);
    }}

    .sort-btn[data-direction="desc"]::after {{
      content: " ↓";
      color: var(--brand);
    }}

    td.number, th.number {{
      text-align: right;
    }}

    tbody tr:hover {{
      background: #f8fbfc;
    }}

    tbody tr.top-six {{
      background: #edf8f1;
    }}

    tbody tr.top-six:hover {{
      background: #ddf1e6;
    }}

    .rank {{
      display: inline-grid;
      place-items: center;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      color: #fff;
      background: var(--brand);
      font-weight: 700;
      font-size: 13px;
    }}

    .rank-wrap {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }}

    .badge {{
      display: inline-flex;
      align-items: center;
      min-height: 22px;
      padding: 0 7px;
      border-radius: 999px;
      color: #0f4b31;
      background: #bfe8d1;
      border: 1px solid #82caa4;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: .04em;
      text-transform: uppercase;
      white-space: nowrap;
    }}

    .badge.championship {{
      color: #4b2c00;
      background: linear-gradient(135deg, #fff2a8 0%, #f1c04b 42%, #b97914 100%);
      border-color: #c99424;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
    }}

    .legend {{
      display: grid;
      gap: 8px;
      padding: 12px;
      border-top: 1px solid var(--line);
      background: #fafcfd;
    }}

    .legend-item {{
      display: flex;
      gap: 10px;
      align-items: center;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.35;
    }}

    .score {{
      font-weight: 800;
      color: var(--green);
    }}

    .empty {{
      padding: 30px;
      color: var(--muted);
      text-align: center;
    }}

    a {{
      color: var(--brand);
      text-decoration: none;
    }}

    a:hover {{
      text-decoration: underline;
    }}

    @media (max-width: 780px) {{
      .topbar {{
        grid-template-columns: 1fr;
        align-items: start;
      }}

      .mark {{
        width: 58px;
        height: 58px;
      }}

      .stats {{
        grid-template-columns: 1fr;
      }}

      .toolbar {{
        grid-template-columns: 1fr;
      }}

      .tabs {{
        grid-auto-flow: row;
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}

      .tab, .action {{
        width: 100%;
      }}
    }}

    @media print {{
      body {{
        background: #fff;
      }}

      .toolbar, .mark {{
        display: none;
      }}

      main, .topbar {{
        max-width: none;
      }}

      .panel {{
        display: block;
        box-shadow: none;
        page-break-after: always;
      }}

      .table-wrap {{
        max-height: none;
        overflow: visible;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="topbar">
      <div>
        <h1>Ranking Białystok - półfinał ligi</h1>
        <p class="subhead">Okręg białostocki, wyniki od 16.05.2026 do 01.08.2026, ranking liczony z 3 najlepszych startów zawodnika.</p>
      </div>
      <div class="mark" aria-hidden="true"></div>
    </div>
  </header>

  <main>
    <section class="stats" aria-label="Podsumowanie">
      <div class="stat wide"><span>Półfinał TOP 6</span><ol class="team-list">{team_six_items}</ol></div>
      <div class="stat">
        <span>Podsumowanie</span>
        <div class="summary-grid">
          <div><span>Zawodnicy</span><strong>{len(ranking)}</strong></div>
          <div><span>Starty</span><strong>{total_starts}</strong></div>
          <div><span>Zawody</span><strong>{len(events)}</strong></div>
        </div>
      </div>
    </section>

    <section class="toolbar" aria-label="Narzędzia tabeli">
      <input class="search" id="search" type="search" placeholder="Szukaj zawodnika, zawodów lub daty" autocomplete="off">
      <div class="tabs" role="tablist" aria-label="Widoki">
        <button class="tab" type="button" data-panel="ranking" aria-selected="true">Ranking</button>
        <button class="tab" type="button" data-panel="starts" aria-selected="false">Wyniki</button>
        <button class="tab" type="button" data-panel="events" aria-selected="false">Zawody</button>
      </div>
      <a class="action secondary" href="zasady.pdf" target="_blank" rel="noreferrer">Zasady</a>
      <button class="action" type="button" id="printBtn">Drukuj</button>
    </section>

    <section class="panel active" id="panel-ranking">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th><button class="sort-btn" type="button" data-ranking-sort="miejsce">Miejsce</button></th>
              <th><button class="sort-btn" type="button" data-ranking-sort="zawodnik">Zawodnik</button></th>
              <th class="number"><button class="sort-btn number" type="button" data-ranking-sort="srednia_3_najlepszych">Średnia</button></th>
              <th class="number"><button class="sort-btn number" type="button" data-ranking-sort="suma_3_najlepszych">Suma 3</button></th>
              <th class="number"><button class="sort-btn number" type="button" data-ranking-sort="suma_5_najlepszych">Suma 5</button></th>
              <th class="number"><button class="sort-btn number" type="button" data-ranking-sort="liczba_startow">Starty</button></th>
              <th class="number">1</th>
              <th class="number">2</th>
              <th class="number">3</th>
              <th class="number"><button class="sort-btn number" type="button" data-ranking-sort="miejsce_mistrzostwa">Mistrz.</button></th>
              <th>Zawody wliczone</th>
            </tr>
          </thead>
          <tbody id="rankingBody"></tbody>
        </table>
      </div>
      <div class="legend" aria-label="Opis etykiet">
        <div class="legend-item"><span class="badge">Półfinał</span><span>TOP 6 rankingu, liczone według sumy 3 najlepszych startów zawodnika w okresie 16.05.2026-01.08.2026.</span></div>
        <div class="legend-item"><span class="badge championship">Mistrzostwa</span><span>TOP 3 kwalifikacji mistrzostw, liczone według sumy 5 najlepszych startów zawodnika w tym samym okresie.</span></div>
      </div>
      <div class="empty" id="rankingEmpty" hidden>Brak wyników dla podanego filtra.</div>
    </section>

    <section class="panel" id="panel-starts">
      <div class="panel-tools" aria-label="Sortowanie wyników">
        <select id="startsSortSelect" aria-label="Sortuj wyniki po">
          <option value="wynik">Wynik</option>
          <option value="zawodnik">Zawodnik</option>
          <option value="nazwa_zawodow">Zawody</option>
          <option value="klasa">Klasa</option>
          <option value="data_zawodow">Data</option>
        </select>
        <button type="button" id="startsDirectionBtn">Malejąco</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th><button class="sort-btn" type="button" data-starts-sort="zawodnik">Zawodnik</button></th>
              <th><button class="sort-btn" type="button" data-starts-sort="nazwa_zawodow">Zawody</button></th>
              <th class="number"><button class="sort-btn number" type="button" data-starts-sort="wynik">Wynik</button></th>
              <th><button class="sort-btn" type="button" data-starts-sort="klasa">Klasa</button></th>
              <th><button class="sort-btn" type="button" data-starts-sort="data_zawodow">Data</button></th>
              <th>Strzelnica</th>
              <th>Link</th>
            </tr>
          </thead>
          <tbody id="startsBody"></tbody>
        </table>
      </div>
      <div class="empty" id="startsEmpty" hidden>Brak wyników dla podanego filtra.</div>
    </section>

    <section class="panel" id="panel-events">
      <div class="panel-tools" aria-label="Sortowanie zawodów">
        <select id="eventsSortSelect" aria-label="Sortuj zawody po">
          <option value="data_zawodow">Data</option>
          <option value="nazwa_zawodow">Zawody</option>
          <option value="zo_pzl_zawody">ZO PZŁ</option>
          <option value="strzelnica">Strzelnica</option>
        </select>
        <button type="button" id="eventsDirectionBtn">Rosnąco</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th><button class="sort-btn" type="button" data-events-sort="data_zawodow">Data</button></th>
              <th><button class="sort-btn" type="button" data-events-sort="nazwa_zawodow">Zawody</button></th>
              <th><button class="sort-btn" type="button" data-events-sort="zo_pzl_zawody">ZO PZŁ</button></th>
              <th><button class="sort-btn" type="button" data-events-sort="strzelnica">Strzelnica</button></th>
              <th>Link</th>
            </tr>
          </thead>
          <tbody id="eventsBody"></tbody>
        </table>
      </div>
      <div class="empty" id="eventsEmpty" hidden>Brak zawodów dla podanego filtra.</div>
    </section>
  </main>

  {to_json_script("ranking-data", ranking)}
  {to_json_script("starts-data", starts)}
  {to_json_script("events-data", events)}
  <script>
    const ranking = JSON.parse(document.getElementById("ranking-data").textContent);
    const starts = JSON.parse(document.getElementById("starts-data").textContent);
    const events = JSON.parse(document.getElementById("events-data").textContent);

    const search = document.getElementById("search");
    const printBtn = document.getElementById("printBtn");
    const tabs = [...document.querySelectorAll(".tab")];
    const rankingSortButtons = [...document.querySelectorAll("[data-ranking-sort]")];
    const startSortButtons = [...document.querySelectorAll("[data-starts-sort]")];
    const eventSortButtons = [...document.querySelectorAll("[data-events-sort]")];
    const startsSortSelect = document.getElementById("startsSortSelect");
    const startsDirectionBtn = document.getElementById("startsDirectionBtn");
    const eventsSortSelect = document.getElementById("eventsSortSelect");
    const eventsDirectionBtn = document.getElementById("eventsDirectionBtn");
    const panels = {{
      ranking: document.getElementById("panel-ranking"),
      starts: document.getElementById("panel-starts"),
      events: document.getElementById("panel-events"),
    }};
    let activePanel = "ranking";
    let rankingSortKey = "miejsce";
    let rankingSortDirection = "asc";
    let startsSortKey = "wynik";
    let startsSortDirection = "desc";
    let eventsSortKey = "data_zawodow";
    let eventsSortDirection = "asc";

    function text(value) {{
      return value === null || value === undefined || value === "" ? "" : String(value);
    }}

    function includesQuery(row, keys, query) {{
      if (!query) return true;
      return keys.some((key) => text(row[key]).toLocaleLowerCase("pl").includes(query));
    }}

    function cell(value, className = "") {{
      const td = document.createElement("td");
      if (className) td.className = className;
      td.textContent = text(value);
      return td;
    }}

    function linkCell(url) {{
      const td = document.createElement("td");
      if (url) {{
        const a = document.createElement("a");
        a.href = url;
        a.target = "_blank";
        a.rel = "noreferrer";
        a.textContent = "wyniki";
        td.appendChild(a);
      }}
      return td;
    }}

    function renderRanking(rows) {{
      const body = document.getElementById("rankingBody");
      const empty = document.getElementById("rankingEmpty");
      body.replaceChildren();
      rows.forEach((row) => {{
        const tr = document.createElement("tr");
        const isTopSix = Number(row.miejsce) <= 6;
        const isChampionship = Number(row.miejsce_mistrzostwa) <= 3;
        if (isTopSix) tr.className = "top-six";
        const rankCell = document.createElement("td");
        const rankWrap = document.createElement("span");
        rankWrap.className = "rank-wrap";
        const rank = document.createElement("span");
        rank.className = "rank";
        rank.textContent = row.miejsce;
        rankWrap.appendChild(rank);
        if (isTopSix) {{
          const badge = document.createElement("span");
          badge.className = "badge";
          badge.textContent = "Półfinał";
          rankWrap.appendChild(badge);
        }}
        if (isChampionship) {{
          const championshipBadge = document.createElement("span");
          championshipBadge.className = "badge championship";
          championshipBadge.textContent = "Mistrzostwa";
          rankWrap.appendChild(championshipBadge);
        }}
        rankCell.appendChild(rankWrap);
        tr.append(
          rankCell,
          cell(row.zawodnik),
          cell(row.srednia_3_najlepszych, "number score"),
          cell(row.suma_3_najlepszych, "number"),
          cell(row.suma_5_najlepszych, "number"),
          cell(row.liczba_startow, "number"),
          cell(row.najlepszy_1, "number"),
          cell(row.najlepszy_2, "number"),
          cell(row.najlepszy_3, "number"),
          cell(row.miejsce_mistrzostwa, "number"),
          cell(row.zawody_wliczone)
        );
        body.appendChild(tr);
      }});
      empty.hidden = rows.length > 0;
    }}

    function renderStarts(rows) {{
      const body = document.getElementById("startsBody");
      const empty = document.getElementById("startsEmpty");
      body.replaceChildren();
      rows.forEach((row) => {{
        const tr = document.createElement("tr");
        tr.append(
          cell(row.zawodnik),
          cell(row.nazwa_zawodow),
          cell(row.wynik, "number score"),
          cell(row.klasa),
          cell(row.data_zawodow),
          cell(row.strzelnica),
          linkCell(row.url_wynikow)
        );
        body.appendChild(tr);
      }});
      empty.hidden = rows.length > 0;
    }}

    function compareValues(a, b) {{
      const leftNumber = Number(a);
      const rightNumber = Number(b);
      if (Number.isFinite(leftNumber) && Number.isFinite(rightNumber)) {{
        return leftNumber - rightNumber;
      }}
      const left = text(a).toLocaleLowerCase("pl");
      const right = text(b).toLocaleLowerCase("pl");
      return left.localeCompare(right, "pl", {{ numeric: true, sensitivity: "base" }});
    }}

    function sortStarts(rows) {{
      const direction = startsSortDirection === "asc" ? 1 : -1;
      return [...rows].sort((a, b) => compareValues(a[startsSortKey], b[startsSortKey]) * direction);
    }}

    function sortRanking(rows) {{
      const direction = rankingSortDirection === "asc" ? 1 : -1;
      return [...rows].sort((a, b) => compareValues(a[rankingSortKey], b[rankingSortKey]) * direction);
    }}

    function updateRankingSortButtons() {{
      rankingSortButtons.forEach((button) => {{
        const active = button.dataset.rankingSort === rankingSortKey;
        button.dataset.direction = active ? rankingSortDirection : "";
        button.setAttribute("aria-sort", active ? (rankingSortDirection === "asc" ? "ascending" : "descending") : "none");
      }});
    }}

    function renderEvents(rows) {{
      const body = document.getElementById("eventsBody");
      const empty = document.getElementById("eventsEmpty");
      body.replaceChildren();
      rows.forEach((row) => {{
        const tr = document.createElement("tr");
        tr.append(
          cell(row.data_zawodow),
          cell(row.nazwa_zawodow),
          cell(row.zo_pzl_zawody),
          cell(row.strzelnica),
          linkCell(row.url_wynikow)
        );
        body.appendChild(tr);
      }});
      empty.hidden = rows.length > 0;
    }}

    function sortEvents(rows) {{
      const direction = eventsSortDirection === "asc" ? 1 : -1;
      return [...rows].sort((a, b) => compareValues(a[eventsSortKey], b[eventsSortKey]) * direction);
    }}

    function updateStartSortButtons() {{
      startSortButtons.forEach((button) => {{
        const active = button.dataset.startsSort === startsSortKey;
        button.dataset.direction = active ? startsSortDirection : "";
        button.setAttribute("aria-sort", active ? (startsSortDirection === "asc" ? "ascending" : "descending") : "none");
      }});
      startsSortSelect.value = startsSortKey;
      startsDirectionBtn.textContent = startsSortDirection === "asc" ? "Rosnąco" : "Malejąco";
    }}

    function updateEventSortButtons() {{
      eventSortButtons.forEach((button) => {{
        const active = button.dataset.eventsSort === eventsSortKey;
        button.dataset.direction = active ? eventsSortDirection : "";
        button.setAttribute("aria-sort", active ? (eventsSortDirection === "asc" ? "ascending" : "descending") : "none");
      }});
      eventsSortSelect.value = eventsSortKey;
      eventsDirectionBtn.textContent = eventsSortDirection === "asc" ? "Rosnąco" : "Malejąco";
    }}

    function render() {{
      const query = search.value.trim().toLocaleLowerCase("pl");
      renderRanking(sortRanking(ranking.filter((row) => includesQuery(row, ["zawodnik", "zawody_wliczone", "wszystkie_starty"], query))));
      renderStarts(sortStarts(starts.filter((row) => includesQuery(row, ["zawodnik", "nazwa_zawodow", "data_zawodow"], query))));
      renderEvents(sortEvents(events.filter((row) => includesQuery(row, ["nazwa_zawodow", "zo_pzl_zawody", "data_zawodow"], query))));
      updateRankingSortButtons();
      updateStartSortButtons();
      updateEventSortButtons();
    }}

    tabs.forEach((tab) => {{
      tab.addEventListener("click", () => {{
        activePanel = tab.dataset.panel;
        tabs.forEach((item) => item.setAttribute("aria-selected", String(item === tab)));
        Object.entries(panels).forEach(([name, panel]) => panel.classList.toggle("active", name === activePanel));
      }});
    }});

    search.addEventListener("input", render);
    printBtn.addEventListener("click", () => window.print());
    rankingSortButtons.forEach((button) => {{
      button.addEventListener("click", () => {{
        const nextKey = button.dataset.rankingSort;
        if (rankingSortKey === nextKey) {{
          rankingSortDirection = rankingSortDirection === "asc" ? "desc" : "asc";
        }} else {{
          rankingSortKey = nextKey;
          rankingSortDirection = ["miejsce", "zawodnik", "miejsce_mistrzostwa"].includes(nextKey) ? "asc" : "desc";
        }}
        render();
      }});
    }});
    eventSortButtons.forEach((button) => {{
      button.addEventListener("click", () => {{
        const nextKey = button.dataset.eventsSort;
        if (eventsSortKey === nextKey) {{
          eventsSortDirection = eventsSortDirection === "asc" ? "desc" : "asc";
        }} else {{
          eventsSortKey = nextKey;
          eventsSortDirection = "asc";
        }}
        render();
      }});
    }});
    startSortButtons.forEach((button) => {{
      button.addEventListener("click", () => {{
        const nextKey = button.dataset.startsSort;
        if (startsSortKey === nextKey) {{
          startsSortDirection = startsSortDirection === "asc" ? "desc" : "asc";
        }} else {{
          startsSortKey = nextKey;
          startsSortDirection = nextKey === "wynik" ? "desc" : "asc";
        }}
        render();
      }});
    }});
    startsSortSelect.addEventListener("change", () => {{
      startsSortKey = startsSortSelect.value;
      startsSortDirection = startsSortKey === "wynik" ? "desc" : "asc";
      render();
    }});
    startsDirectionBtn.addEventListener("click", () => {{
      startsSortDirection = startsSortDirection === "asc" ? "desc" : "asc";
      render();
    }});
    eventsSortSelect.addEventListener("change", () => {{
      eventsSortKey = eventsSortSelect.value;
      eventsSortDirection = "asc";
      render();
    }});
    eventsDirectionBtn.addEventListener("click", () => {{
      eventsSortDirection = eventsSortDirection === "asc" ? "desc" : "asc";
      render();
    }});
    render();
  </script>
</body>
</html>
"""


def write_site(ranking, starts, events):
    OUTPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_FILE.write_text(build_html(ranking, starts, events), encoding="utf-8")
    print("Zapisano stronę:", OUTPUT_FILE)


def write_site_from_dataframes(ranking, starts, events):
    write_site(
        dataframe_to_records(ranking),
        dataframe_to_records(starts),
        dataframe_to_records(events),
    )


def main():
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(f"Brak pliku źródłowego: {SOURCE_FILE}")

    write_site(
        read_sheet("Ranking półfinał"),
        read_sheet("Wyniki Białystok"),
        read_sheet("Zawody w okresie"),
    )


if __name__ == "__main__":
    main()
