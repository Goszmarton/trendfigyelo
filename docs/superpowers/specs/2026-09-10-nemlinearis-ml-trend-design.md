# Nemlineáris (ML) trend a kulcsszó-chartokon — design

**Állapot:** jóváhagyott terv, implementáció előtt (Phase 4).
**Dátum:** 2026-09-10.

## 1. Cél

Minden kulcsszóhoz a meglévő **lineáris** regressziós trend (piros szaggatott egyenes)
MELLÉ egy **nemlineáris** trend, ami sokkal jobban megragadja a szó keresettségének
mozgását — DE bizonyíthatóan **nem túltanult**. A lineáris MINDIG látszik; a nemlineáris
egy **kapcsolóval** be/ki (alapból KI). A számítás megőrzi a főbb statisztikai metrikákat
(értelmezéshez).

## 2. Az adat (MÉRT — ez indokolja a modellválasztást)

Per szó, egyváltozós idősor (0–100 relatív keresési szint), felbontásonként:

| Felbontás | Minta N | Lineáris R² | Reziduum ACF(1) |
|---|---|---|---|
| Órás (1 hó) | 191–1003 | 0.00–0.09 | +0.68…+0.88 |
| Heti (1 év) | 52 | 0.03–0.33 | +0.18…+0.57 |
| Napi (3 hó) | 92 | 0.03–0.08 | +0.05…+0.29 |

- A lineáris R² **nagyon alacsony** → az egyenes szinte semmit nem magyaráz.
- A reziduum **erősen autokorrelált** → van **strukturált, sima** jel (nem fehér zaj).
- **DE a minta kicsi** (52 heti / 92 napi) → túltanulás a fő kockázat.

## 3. A modell — LOESS + CV + túltanulás-őr (kereszt-validált döntés)

**5-fold out-of-sample R² a valós sorokon** (a döntést ez alapozza meg):

| Sorozat | N | LIN | poly3 | LOESS.3 | LOESS.5 |
|---|---|---|---|---|---|
| akciós újság het | 52 | 0.22 | 0.38 | 0.37 | **0.43** |
| állás het | 52 | -0.01 | 0.07 | **0.24** | 0.10 |
| kórház het | 52 | -0.04 | -0.03 | -0.28 | -0.18 |
| kölcsön nap | 92 | 0.05 | **0.12** | 0.05 | 0.07 |
| hitel nap | 92 | -0.01 | -0.01 | -0.09 | -0.03 |
| benzin óra | 400 | -0.02 | 0.01 | **0.12** | 0.02 |
| infláció óra | 191 | 0.08 | 0.20 | **0.41** | 0.32 |

**Tanulság:** a korábbi in-sample „simító R²=0,5–0,64" túltanulás volt. Out-of-sample a
nemlineáris **egyeseken sokat segít** (akciós újság, állás, infláció), **másokon ROMLIK**
(kórház, hitel — gyakorlatilag zaj). Ezért az **őr** kötelező.

**Választott modell: LOESS** (lokális súlyozott lineáris regresszió, tricube kernel, 1
robusztus iteráció). Indoklás:
- **NULLA új függőség** — tiszta numpy (scipy/statsmodels/sklearn/torch mind elkerülve → a
  CI-pipeline érintetlen).
- **Determinista** (nincs seed/véletlen; az XGBoost/RF ezt sértené — kizárva).
- **A legjobb/holtversenyes out-of-sample** a strukturált sorokon; a széleken stabilabb, mint
  a polinom.
- **Robusztus** az órás kiugrásokra.

**Elvetve:** RNN/LSTM (52 ponton katasztrofális túltanulás, torch ~800 MB CI-ellenséges);
XGBoost/Random Forest (szakaszosan konstans kimenet a sima jelre a legrosszabb, véletlen a
determinizmus ellen).

**Span-választás:** determinista **k-fold CV** (`i % k` particionálás, NINCS véletlen);
span-jelöltek `{0.3, 0.5, 0.7}`; a legjobb out-of-sample R² nyer.

**Túltanulás-őr:** a nemlineáris `van_struktura=True` CSAK ha `cv_r2 >= lin_cv_r2 + MARGO`
(MARGO ≈ 0.05). Különben nem rajzolunk görbét, a kártya jelzi „nincs érdemi nemlineáris
szerkezet" — a [[naming-discipline]] elve: zajos szónál (kórház/hitel) NE hazudjunk trendet.

## 4. Architektúra

### 4.1 Backend — új modul `trendfigyelo/ml_trend.py`
- Bemenet: ugyanaz a lezárt pont-sorozat, mint a lineáris regresszió (per szó × intervallum).
- Fő függvények: `loess(x, y, span, robusztus_iter)`, `cv_span_valaszt(x, y, spanok, k)`,
  `nemlin_trend(pontok, lin_cv_r2)` → a kimeneti blokk.
- **Determinizmus:** nincs argless random / `datetime.now()`; a fold-particionálás `i % k`.

### 4.2 Adat-séma (ágyazva a meglévő regresszió-fájlokba)
Minden ÉRVÉNYES intervallum-objektum (`kulcsszo_regresszio.json` +
`kulcsszo_masodlagos_regresszio.json`) kap egy `nemlin` blokkot:
```json
"nemlin": {
  "van_struktura": true,
  "gorbe": [{"idopont_utc": "...", "ertek": 41.2}, ...],   // ~40 pont a sima vonalhoz
  "cv_r2": 0.41, "lin_cv_r2": 0.08, "eff_df": 6.3, "span": 0.3,
  "irany": "novekszik", "fordulopontok": 2, "rezidualis_szoras": 12.1
}
```
`van_struktura=false` esetén a `gorbe` üres/elhagyva, a metrikák megmaradnak (átláthatóság).

### 4.3 Frontend (`docs/js/app.js` + `docs/css/app.css`)
- **Gomb** (az adatforrás-marker mintájára): „Nemlineáris trend (ML)" be/ki,
  `#kulcsszo-blokk[data-mltrend]`, **alapból KI**; alatta kék-vonalas info-callout.
- **Bekapcsolva:** a chartra folytonos **lila (`#8e44ad`)** görbe (a `nemlin.gorbe`-ből) —
  elüt a kék adattól / piros lineáristól / narancs szinttől / szürke markertől. Csak ahol
  `van_struktura`.
- `van_struktura=false` → nincs görbe; a kártya jelzi „nincs érdemi nemlineáris szerkezet".

### 4.4 Értelmezés (metrikák a kártyán, ha BE)
A mérőszám-szöveg bővül: „nemlineáris illeszkedés R²=0,41 (lineáris 0,08 helyett) · 2
fordulópont · a görbe emelkedő".

### 4.5 Pipeline
A napi futásban, a regresszió-ág UTÁN (vagy abba integrálva), **nulla Google-hívás**,
determinista. A pótolhatatlan órás lánc + a lineáris regresszió VÁLTOZATLAN.

## 5. Tesztelés (TDD)
- **Backend:** LOESS-reprodukálhatóság; CV span-választás (fabrikált görbén a jó span nyer);
  **őr** (fabrikált fehér zaj → van_struktura=False; fabrikált nemlineáris görbe → True);
  determinizmus (kétszeri futás bájt-azonos).
- **Frontend (e2e):** gomb default-KI (nincs lila görbe); toggle → görbe rajzol
  (van_struktura fixture); van_struktura=false → nincs görbe + jelzés.

## 6. Hatókörön KÍVÜL (későbbi kör)
- A napi **AI-elemzés** nemlineáris-összefoglalója (a payloadba a metrikák) — külön kör,
  hogy ez ne legyen egyszerre túl nagy.
- Bizonytalansági sáv (GP-jellegű) — nincs; a LOESS pont-becslés elég.

## 7. Kockázatok / megjegyzések
- **Számítási költség:** ~28 szó × ~5 intervallum × (k-fold × 3 span) LOESS numpy-ban —
  gyors (< pár mp), de mérni kell a napi futás idejét.
- **Az órás sorok hosszúak** (N~1000): a LOESS O(N·k) per query pont; a görbe ~40 query pont
  → olcsó. A CV a teljes N-en fut, de numpy-vektorizáltan kezelhető.
- **Determinizmus-kapu:** semmilyen véletlen a tesztelt logikában (fold = `i % k`).
