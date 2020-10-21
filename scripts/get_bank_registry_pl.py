import json

import requests


URL = "https://ewib.nbp.pl/plewibnra?dokNazwa=plewibnra.txt"


def process():
    registry = []
    with requests.get(URL, stream=True) as fp:
        for row in fp.iter_lines():
            cells = [cell.strip() for cell in row.decode("CP852").split("\t")]
            if len(cells) != 32:
                continue
            registry.append(
                {
                    "country_code": "PL",
                    "primary": True,
                    "bic": cells[19].upper(),
                    "bank_code": cells[4],
                    "name": cells[1],
                    "short_name": cells[1],
                }
            )
    return registry


if __name__ == "__main__":
    with open("schwifty/bank_registry/generated_pl.json", "w") as fp:
        json.dump(process(), fp, indent=2)
