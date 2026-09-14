# Havi NLP-elemzés a felkapott keresőszavakról (magyar, LLM-alapú) — design

**Állapot:** jóváhagyott terv, implementáció előtt (Phase 4).
**Dátum:** 2026-09-14.

## 1. Cél

Havonta egy **mély, megbízható, pontos** NLP-elemzés a hónap **felkapott keresőszavairól**,
**magyar nyelven**: a szavak tokenizálása, lemmatizálása, **NER** (országok / települések / személyek),
**tematikus klaszterezés** és **értelmezés**. Ez NEM felületes összefoglaló, hanem az egész havi
keresési érdeklődés strukturált, auditálható NLP-feldolgozása.

**1. FÁZIS (ez a spec):** egy külön **„Havi elemzés" fül** a honlapon, ahol az eredmény MINDIG elérhető
(kísérletezéshez). A generálást a hónap korpuszából végezzük.
**2. FÁZIS (későbbi kör, HATÓKÖRÖN KÍVÜL):** a „csak a hónap utolsó napján generál/jelenik meg"
ütemezés + jelzés az Elemzések fülön.

## 2. Az adat (a korpusz)

- Forrás: a hónap `docs/data/napok/YYYY-MM-DD.json` fájljai, a **felkapott** (Google napi trend)
  szavak: `reggel`/`este` szegmens → `trendek[]` → `kifejezes` (a keresőszó) + `volumen` +
  `novekedes_pct` + `temak` (Google-topik-címkék) + `hirek` (kapcsolódó hír-címek).
- **Korpusz-építés** (determinista, pure Python): a hónap MINDEN napjának reggel+este szavai
  **egyedivé** téve; szavanként aggregált metaadat: **gyakoriság** (hány külön napon trendelt),
  **max volumen**, **Google-témák halmaza**, **pár reprezentatív hír-cím**. → pár száz magyar
  keresőszó, gazdag kontextussal. Ez a korpusz megy az LLM-hez (nem nyers, hanem aggregált).

## 3. A módszer — LLM (Claude) magyar NLP, strukturált JSON

**Miért LLM és nem klasszikus (huspaCy) vagy fordítás?** A projekt megkötése NULLA nehéz Python-dep
(numpy-only), CI-barát; és MÁR hív Claude Opus-t strukturált JSON-kimenettel (elemzo.py). A huspaCy
(~500 MB spaCy+modell) sértené ezt; a fordítás→angol-NLP→vissza két fordítási hop, gyengébb NER. A
Claude magyar-natív, egy strukturált hívásban tokenizál/lemmatizál/NER-el/klaszterez — ÉS a
minőség/mélység a legmagasabb elérhető modellel (Opus 4.8, adaptive thinking) biztosított.

**Reuse:** az `elemzo._AnthropicKliens` mintája (anthropic SDK, `messages.stream`, adaptive thinking,
`output_config` **json_schema** strukturált kimenet, injektálható SDK teszthez, bounded retry +
fail-soft). ÚJ séma + ÚJ magyar NLP-prompt; NULLA új API-kód-koncepció.

### 3.1 A MEGBÍZHATÓSÁG/MÉLYSÉG biztosítékai (ez a lényeg — nem gyors munka)
1. **Legképesebb modell + mély gondolkodás:** `claude-opus-4-8`, `thinking: adaptive`, magas effort.
2. **Gazdag bemenet:** nem csak a szavak, hanem gyakoriság + volumen + Google-témák + hír-címek →
   a klaszterezés és értelmezés informált, nem felszínes.
3. **GROUNDING (kitalálás-tilalom):** a prompt kimondja, hogy a NER-entitások és a klaszter-tagok
   KIZÁRÓLAG a kapott korpusz szavaiból/azok tartalmából származhatnak; nincs kitalált entitás vagy
   szó. **Utólagos validáció (Python):** minden NER-entitás és klaszter-tag visszavezethető a
   korpuszra (a nem visszavezethetőket kiszűrjük/jelöljük) — így a kimenet auditálható.
4. **Teljes lefedettség:** MINDEN korpusz-szó bekerül pontosan egy klaszterbe (a prompt + a validáció
   ellenőrzi, hogy nincs „lógó" szó); a lemma-térkép MINDEN szóra ad lemmát.
5. **Precíz magyar NLP:** a prompt magyar lemmatizálást (tő/szótári alak), magyar NER-t (magyar
   települések/nevek felismerése), és jelentés-alapú (nem felszíni szó-egyezés) klasztereket kér.
6. **Auditálhatóság:** a kimenet tartalmazza a szó→lemma térképet és a klaszter→tagszavak listát, hogy
   a felhasználó ELLENŐRIZHESSE a feldolgozást (nem fekete doboz).

### 3.2 A kimenet (strukturált JSON séma)
- `lemmak`: `[{szo, lemma}]` — MINDEN korpusz-szóra.
- `ner`: `{orszagok:[{nev, szavak:[...]}], telepulesek:[{nev, szavak}], szemelyek:[{nev, szavak}]}` —
  a felismert entitások + mely keresőszavakban jelennek meg.
- `klaszterek`: `[{cimke, szavak:[...], ertelmezes, uralkodo_temak:[...], megjegyzes?}]` — tematikus
  csoportok magyar címkével, a tag-szavakkal, magyar értelmezéssel, a domináns Google-témákkal.
- `osszegzes`: a hónap keresési érdeklődésének magyar összefoglaló értelmezése (folyó próza).
- (Minden mező magyarul; a séma `additionalProperties:false`, a validáció betartatja.)

## 4. Architektúra

### 4.1 Backend — új `trendfigyelo/havi_nlp.py`
- `havi_korpusz(docs_data, honap) -> dict` — a hónap aggregált korpusza (determinista, pure).
- `_nlp_sema()` — a 3.2 JSON-séma. `RENDSZER_PROMPT_NLP` — a 3.1 elveket betartató magyar prompt.
- `havi_nlp_elemez(korpusz, kliens=None, modell="claude-opus-4-8", probak=3, ...) -> dict` — az
  `_AnthropicKliens`-mintával; bounded retry; a hívás UTÁN **grounding-validáció** (3.1/3) a korpusz
  ellen; injektálható SDK teszthez.
- `havi_nlp_ir(docs_data, honap, eredmeny) -> Path` → `docs/data/havi_nlp/YYYY-MM.json`.
- **Determinizmus-határ:** az LLM-hívás NEM determinista (mint a napi elemzés) → AI-jelölés a
  fülön; a KORPUSZ-építés és a VALIDÁCIÓ determinista és tesztelt.

### 4.2 Adat-séma (`docs/data/havi_nlp/2026-09.json`)
```json
{ "honap": "2026-09", "keszult": "2026-…T…Z", "modell": "claude-opus-4-8",
  "korpusz": { "egyedi_szo": 240, "napok": 30, "forras": "felkapott (reggel+este)" },
  "lemmak": [{ "szo": "csalások", "lemma": "csalás" }],
  "ner": { "orszagok": [{ "nev": "Ukrajna", "szavak": ["ukrajna háború"] }],
           "telepulesek": [{ "nev": "Debrecen", "szavak": [...] }],
           "szemelyek": [{ "nev": "…", "szavak": [...] }] },
  "klaszterek": [{ "cimke": "Bűnügy és csalás", "szavak": ["csalás", "átverés"],
                   "ertelmezes": "…", "uralkodo_temak": ["Business and Finance"] }],
  "osszegzes": "A hónap keresési érdeklődését…" }
```

### 4.3 Frontend — új „Havi elemzés" fül (`docs/havi.html` + `docs/havi.js`)
- Új nav-fül MIND az oldalakon. A meglévő **„Elemzések" fül átnevezve „Napi Elemzések"-re** (USER-kérés;
  a napi vs. havi megkülönböztetés). A nav új sorrendje: **Napi Elemzések · Havi elemzés · Google Trendek ·
  YouTube Trendek · Infó** (a két elemzés-fül egymás mellett). Az átnevezés a nav-szövegben MIND az
  oldalon + az `elemzes.html` fej-címében (h1/`<title>`). A landing (`/` → `elemzes.html`) változatlan.
- A fül (az elemzes/youtube-fül mintájára): **hónap-választó**; megjeleníti a **klasztereket**
  (címke + tag-szavak + értelmezés + domináns témák), a **NER-t** három csoportban (országok /
  települések / személyek), a **szó→lemma térképet** (auditálhatóság), és az **összegzést**. AI-jelölés
  („gépi elemzés"). Interaktív/áttekinthető — „amivel tudunk játszani".
- Nincs `new Date()`/`Date.now()`.

### 4.4 Generálás (1. fázis)
- Külön kis belépési pont (script vagy `havi_nlp` fő-függvény), amit a napi futástól FÜGGETLENÜL
  futtatunk (a kulcs a környezetből). Az 1. fázisban a **jelenlegi hónap** korpuszából egyszer
  legenerálom (valós adat a fülhöz). A napi/utolsó-nap-ütemezés a 2. fázis.

## 5. Tesztelés (TDD)
- **Korpusz-építő** (pure, fabrikált napfájlokból): dedup + gyakoriság + volumen + témák + hírek helyes;
  determinista.
- **NLP-hívás** MOCKOLT SDK-val (mint az elemzo-tesztek): a séma-hívás összeáll; a **grounding-validáció**
  kiszűri a nem-korpusz entitást/tag-szót; fail-soft tartós hibán.
- **Frontend (e2e):** mockolt `havi_nlp` JSON → a fül klasztereket + NER-t (3 csoport) + lemma-térképet
  + összegzést rajzol; hónap-választó; hiányzó adaton fail-soft üzenet.
- **A tesztek NEM az LLM-kimenetet ítélik meg**, hanem a pipeline-t + a validációt + a megjelenítést.

## 6. Hatókörön KÍVÜL (2. fázis / későbbi)
- „Csak a hónap utolsó napján generál/jelenik meg" ütemezés + Elemzések-jelzés.
- A napi futásba integrált automatikus havi generálás (cron).
- Idősoros/hó-hó összevetés, entitás-trendek.

## 7. Kockázatok / megjegyzések
- **Nem determinista** LLM-kimenet — elfogadott (AI-fül, jelölve); a korpusz+validáció determinista.
- **Költség:** 1 Opus-hívás/hónap (nagy, mély) — havonta egyszer, elhanyagolható.
- **Grounding:** a validáció a fő védelem a hallucináció ellen; a nem visszavezethető entitás kiesik.
- **Kulcs:** `ANTHROPIC_API_KEY` a környezetből (mint az elemzo.py); a titkok kezelése változatlan.
