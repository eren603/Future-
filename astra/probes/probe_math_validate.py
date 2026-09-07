"""Ölçüm sondası: exact_math kenar durumları, owner kapısı, validate/bounded_json davranışı."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1] / "bundle_v1_3"
sys.path.insert(0, str(ROOT))
from astra_reference import exact_math, MathRejected, Rejected, validate, bounded_json, string

for s in ["1_000", "0x10", "1.", ".5", "1e", "2**-1", "1e-400", "10**20**1", "(1/3)*3", "1e100", "1e308*10", "0.1+0.2"]:
    try:
        print(repr(s), "->", exact_math(s)["exact"][:40])
    except MathRejected as e:
        print(repr(s), "-> MathRejected", e)

for owner in ["n/a", "-", "TBD", "operator", "?", "N/A", "unknown ", "Bilinmiyor"]:
    print("owner", repr(owner), "->", "GEÇER" if owner.strip().lower() not in {"unknown", "bilinmiyor"} else "RED")

try:
    validate(None, string(nullable=True, values=["a"])); print("validate None+enum: GEÇTİ (None enum'da yok)")
except Rejected as e:
    print("validate None+enum ->", e)
try:
    validate("", string(minimum=0)); print("validate '' min=0: GEÇTİ")
except Rejected as e:
    print("validate '' ->", e)
try:
    bounded_json(b'{"a":{"peer_results":1}}'); print("iç içe FORBIDDEN: GEÇTİ")
except Rejected as e:
    print("iç içe FORBIDDEN ->", e)
try:
    bounded_json(b'{"statement":"peer_results"}'); print("değer olarak peer_results: GEÇTİ (beklenen)")
except Rejected as e:
    print("değer olarak ->", e)
