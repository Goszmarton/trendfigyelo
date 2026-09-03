"""Reggeli másodlagos gyűjtés VÁRHATÓ dátuma a még-be-nem-gyűlt szavakhoz.

A rotáció determinisztikus (lásd futtato.masodlagos_szavak_ma): a soha-nem-gyűlt
cellák `inf` elavultsággal a sor elejére kerülnek, config-sorrendben; futásonként
MAX_MASODLAGOS_REGGELI cella gyűl be, napi 1 reggeli futással. Ezért egy `r` rangú
(0-alapú, a soha-nem-gyűlt reggeli szavak config-sorrendjében) váró szó a
floor(r / cap) + 1 -edik jövőbeli reggeli futáson gyűl be → a következő reggeli
naptól számítva floor(r / cap) nappal később.

Tiszta függvény: nincs I/O és nincs órajel-olvasás — a `most`-ot a hívó adja.
"""
from datetime import timedelta

from . import nyers_kimenet, seged
from .config import masodlagos_timeframek

MAX_MASODLAGOS_REGGELI = 8   # tükrözi futtato.MAX_MASODLAGOS_REGGELI (a hívó a sajátját adja át)


def varhato_gyujtes_datumok(config, masodlagos_nyers, most, cap=MAX_MASODLAGOS_REGGELI):
    """szó -> 'YYYY-MM-DD' (Budapest) a soha-nem-gyűlt reggeli nem-órás szavakhoz."""
    masodlagos_nyers = masodlagos_nyers or {}
    reggeli = [t for t in config.osszes_kulcsszo()
               if t.racs != "ora" and t.futas == "reggel"]
    varok = [t for t in reggeli if not _van_rekord(masodlagos_nyers, t)]
    kov_reggeli = most.astimezone(seged.BUDAPEST).date() + timedelta(days=1)
    return {t.kifejezes: (kov_reggeli + timedelta(days=r // cap)).isoformat()
            for r, t in enumerate(varok)}


def _van_rekord(masodlagos_nyers, tetel):
    """Igaz, ha a szónak van érvényes lekerdezes_utc-jű másodlagos rekordja A SAJÁT
    (reggeli) timeframe-ében — a schedulerrel (futtato.masodlagos_szavak_ma) azonos
    cella-szintű szűrés, hogy a két predikátum config-churn alatt se csússzon szét."""
    tfs = set(masodlagos_timeframek(tetel))
    rekordok = masodlagos_nyers.get(tetel.kifejezes) or []
    return any(nyers_kimenet._aware_dt(r.get("lekerdezes_utc")) is not None
               for r in rekordok if r.get("timeframe") in tfs)
