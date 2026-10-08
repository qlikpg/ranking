"""Rebuild the interface from the last published dataset, without refreshing results."""
import json
from pathlib import Path

from bs4 import BeautifulSoup

from bialystok_polfinal_site import write_site


def main():
    soup = BeautifulSoup(Path('site/index.html').read_text(encoding='utf-8'), 'html.parser')
    datasets = []
    for name in ('ranking-data', 'starts-data', 'events-data'):
        node = soup.find('script', id=name)
        if node is None:
            raise RuntimeError(f'Brak zapisanych danych: {name}')
        records = json.loads(node.string)
        if not isinstance(records, list) or not records:
            raise RuntimeError(f'Nieprawidłowe lub puste dane: {name}')
        datasets.append(records)
    averages_file = Path('data/event_averages.json')
    if averages_file.exists():
        averages = {
            (row['nazwa_zawodow'], row['data_zawodow']): row['srednie_zawodow']
            for row in json.loads(averages_file.read_text(encoding='utf-8'))
        }
        for row in datasets[1]:
            if not row.get('srednie_zawodow'):
                row['srednie_zawodow'] = averages.get(
                    (row.get('nazwa_zawodow'), row.get('data_zawodow')), {}
                )
    write_site(*datasets)


if __name__ == '__main__':
    main()
