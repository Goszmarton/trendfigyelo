"""Közpolitikai (szakpolitikai) taxonómia és determinista besorolás a Bővítés fülhöz. IZOLÁLT
modul — a config.yaml (gyűjtés-kritikus) ÉRINTETLEN. 3-szintű besorolás: kulcsszó-térkép →
domén-fallback → Google-témacímke-fallback → 'egyeb'."""

SZAKPOLITIKAK = [
    ("szocialpolitika", "Szociálpolitika"),
    ("egeszsegpolitika", "Egészségpolitika"),
    ("oktataspolitika", "Oktatáspolitika"),
    ("gazdasag_foglalkoztatas", "Gazdaság- és foglalkoztatáspolitika"),
    ("lakhatas", "Lakhatás"),
    ("energia_rezsi", "Energia és rezsi"),
    ("kozelet_kozigazgatas", "Közélet és közigazgatás"),
    ("egyeb", "Egyéb / nem közpolitikai"),
]
SZAKPOLITIKA_SLUGOK = {s for s, _ in SZAKPOLITIKAK}

KULCSSZO_SZAKPOLITIKA = {
    "állás": "gazdasag_foglalkoztatas", "kormányablak": "kozelet_kozigazgatas",
    "eladó lakás": "lakhatas", "albérlet": "lakhatas", "akciós újság": "egyeb",
    "benzin": "energia_rezsi", "nyaralás": "egyeb", "kórház": "egeszsegpolitika",
    "betegség": "egeszsegpolitika", "napelem": "energia_rezsi", "nyugdíj": "szocialpolitika",
    "hitel": "lakhatas", "tüntetés": "kozelet_kozigazgatas", "infláció": "gazdasag_foglalkoztatas",
    "rezsi": "energia_rezsi", "fizetés": "gazdasag_foglalkoztatas", "segély": "szocialpolitika",
    "várólista": "egeszsegpolitika", "háziorvos": "egeszsegpolitika", "műtét": "egeszsegpolitika",
    "iskola": "oktataspolitika", "munkanélküliség": "gazdasag_foglalkoztatas",
    "csőd": "gazdasag_foglalkoztatas", "kölcsön": "lakhatas", "sürgősségi": "egeszsegpolitika",
    "pedagógus": "oktataspolitika", "korrupció": "kozelet_kozigazgatas", "kormány": "kozelet_kozigazgatas",
}
DOMEN_SZAKPOLITIKA = {
    "megelhetes": "gazdasag_foglalkoztatas", "egeszsegugy": "egeszsegpolitika",
    "oktatas": "oktataspolitika", "gazdasag": "gazdasag_foglalkoztatas",
    "politika": "kozelet_kozigazgatas",
}
GOOGLE_TEMA_SZAKPOLITIKA = {
    "Politics": "kozelet_kozigazgatas", "Law and Government": "kozelet_kozigazgatas",
    "Health": "egeszsegpolitika", "Business and Finance": "gazdasag_foglalkoztatas",
    "Jobs and Education": "oktataspolitika", "Climate": "energia_rezsi",
    "Science": "egyeb", "Technology": "egyeb", "Sports": "egyeb", "Entertainment": "egyeb",
    "Hobbies and Leisure": "egyeb", "Other": "egyeb",
}


def szakpolitika_besorol(kifejezes=None, domen=None, temak=None):
    """3-szintű determinista besorolás: pontos kulcsszó → domén → Google-témacímke → 'egyeb'."""
    if kifejezes and kifejezes in KULCSSZO_SZAKPOLITIKA:
        return KULCSSZO_SZAKPOLITIKA[kifejezes]
    if domen and domen in DOMEN_SZAKPOLITIKA:
        return DOMEN_SZAKPOLITIKA[domen]
    for t in (temak or []):
        if t in GOOGLE_TEMA_SZAKPOLITIKA:
            return GOOGLE_TEMA_SZAKPOLITIKA[t]
    return "egyeb"
