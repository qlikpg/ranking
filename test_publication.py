import unittest
from unittest.mock import patch

import pandas as pd

import bialystok_polfinal as ranking
import ranking_pzlow_lata as source


class PublicationTests(unittest.TestCase):
    def test_iso_dates_and_qualification_boundaries(self):
        events = pd.DataFrame({
            "data_zawodow": ["2026-05-15", "2026-05-16", "2026-08-01", "2026-09-09", "2026-09-10"],
            "nazwa_zawodow": ["A", "B", "C", "D", "E"],
        })
        selected = ranking.filter_events_for_period(
            events, ranking.DATA_OD_MISTRZOSTWA, ranking.DATA_DO_FINAL
        )
        self.assertEqual(selected["nazwa_zawodow"].tolist(), ["B", "C", "D", "E"])

    def test_season_top_three_sum(self):
        rows = []
        for player, scores in [("A", [100, 200, 300, 400]), ("B", [450])]:
            for i, score in enumerate(scores):
                rows.append(dict(zawodnik=player, okreg="Białystok", razem=score,
                    nazwa_zawodow=f"Zawody {i}", data_zawodow=["2026-02-01", "2026-06-01", "2026-08-10", "2026-09-19"][i],
                    klasa="M", strzelnica="", url_wynikow=f"event:{i}"))
        rows.append(dict(rows[0], razem=500, nazwa_zawodow="Poprzedni sezon", data_zawodow="2025-12-31"))
        result, starts = ranking.build_bialystok_polfinal_ranking(pd.DataFrame(rows))
        self.assertEqual(result["zawodnik"].tolist(), ["A", "B"])
        self.assertEqual(result["suma_3_najlepszych"].tolist(), [900, 450])
        self.assertEqual(result["liczba_startow"].tolist(), [4, 1])
        self.assertEqual(len(starts), 5)
        from bialystok_polfinal_site import build_html, dataframe_to_records
        html = build_html(dataframe_to_records(result), dataframe_to_records(starts), [])
        self.assertIn('data-ranking-sort="suma_3_najlepszych">Suma 3', html)
        self.assertNotIn('Kwalifikacja mistrzostwa', html)
        self.assertNotIn('badge.textContent = "Finał"', html)

    @patch("bialystok_polfinal_site.write_site_from_dataframes")
    @patch.object(ranking, "pobierz_zawody_z_wynikami", return_value=pd.DataFrame())
    def test_empty_calendar_aborts_before_writing(self, fetch, write):
        with self.assertRaisesRegex(RuntimeError, "Brak zawodów"):
            ranking.main()
        self.assertEqual(fetch.call_count, 2)
        fetch.assert_called_with(refresh=True)
        write.assert_not_called()

    @patch("bialystok_polfinal_site.write_site_from_dataframes")
    @patch.object(ranking.time, "sleep")
    @patch.object(ranking, "pobierz_wyniki_zawodow", return_value=pd.DataFrame())
    def test_empty_results_abort_before_writing(self, results, sleep, write):
        events = pd.DataFrame([{"data_zawodow": "2026-08-08", "nazwa_zawodow": "Test"}])
        with patch.object(ranking, "pobierz_zawody_z_wynikami", return_value=events):
            with self.assertRaisesRegex(RuntimeError, "Puste dane"):
                ranking.main()
        write.assert_not_called()

    @patch.object(source, "fetch_html", return_value="<html></html>")
    def test_refresh_uses_distinct_calendar_url(self, fetch):
        source.pobierz_zawody_z_wynikami(refresh=True)
        self.assertTrue(fetch.call_args.args[0].startswith(source.TERMINARZ_URL + "?ranking_refresh="))


if __name__ == "__main__":
    unittest.main()
