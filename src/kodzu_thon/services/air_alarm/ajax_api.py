import requests

STATE_LIBRARY = {
    "Khmelnytskyi Oblast": "Хмельницька область",
    "Vinnytsia Oblast": "Вінницька область",
    "Rivne Oblast": "Рівненська область",
    "Volyn Oblast": "Волинська область",
    "Dnipropetrovsk Oblast": "Дніпропетровська область",
    "Zhytomyr Oblast": "Житомирська область",
    "Zakarpattia Oblast": "Закарпатська область",
    "Zaporizhia Oblast": "Запорізька область",
    "Ivano-Frankivsk Oblast": "Івано-Франківська область",
    "Kiev Oblast": "Київська область",
    "Kirovohrad Oblast": "Кіровоградська область",
    "Luhansk Oblast": "Луганська область",
    "Mykolaiv Oblast": "Миколаївська область",
    "Odessa Oblast": "Одеська область",
    "Poltava Oblast": "Полтавська область",
    "Sumy Oblast": "Сумська область",
    "Ternopil Oblast": "Тернопільська область",
    "Kharkiv Oblast": "Харківська область",
    "Kherson Oblast": "Херсонська область",
    "Cherkasy Oblast": "Черкаська область",
    "Chernihiv Oblast": "Чернігівська область",
    "Chernivtsi Oblast": "Чернівецька область",
    "Lviv Oblast": "Львівська область",
    "Donetsk Oblast": "Донецька область",
}

_URL = "https://air-save.ops.ajax.systems/api/mobile/regions"


def fetch_alarm_states() -> dict[str, bool]:
    resp = requests.get(_URL)
    regions = [r for r in resp.json()["regions"] if r["regionType"] == "STATE"]
    inv = {v: k for k, v in STATE_LIBRARY.items()}
    return {r["name"]: len(r["alarmsInRegion"]) > 0 for r in regions if r["name"] in inv}
