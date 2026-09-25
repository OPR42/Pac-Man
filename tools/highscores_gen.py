import json

from pathlib import Path

import hashlib
import hmac


CHECKSUM_LEN = 16
CHECKSUM_KEY = b"Pac-Man-42-Hall-of-Fame"

scores = [
    ("V", 125000),
    ("SOLE SURVR", 98420),
    ("Furiosa42", 87310),
    ("Chuck NRS", 76900),
    ("xxxxxxxxx", 65540),
    ("x CJOST x", 54200),
    ("x  was  x", 43800),
    ("x  here x", 32100),
    ("xxxxxxxxx", 24750),
    ("AmstradCPC", 18000),
    ("HOMER SMPS", 9500),
    ("NotSoBad", 7200),
    ("Dr DOOM", 5000),
    ("LoRdOfKaOs", 4200),
    ("thatsuxxx", 3000),
    ("PrestonG", 2100),
    ("Nick Name", 1200),
    ("MrBeanLoL", 500),
    ("N00B", 100),
    ("AFK", 0),
]


def checksum(name: str, score: int) -> str:
    payload = f"{name}|{score}|0".encode("utf-8")

    return hmac.new(
        CHECKSUM_KEY,
        payload,
        hashlib.sha256,
    ).hexdigest()[:CHECKSUM_LEN]


entries = [
    {
        "name": name,
        "score": score,
        "corrupted": False,
    }
    for name, score in scores
]

signature = "".join(
    checksum(name, score)
    for name, score in scores
)

data = {
    "scores": entries,
    "signature": signature,
}

Path("hall_of_fame.json").write_text(
    json.dumps(data, indent=4) + "\n",
    encoding="utf-8",
)
