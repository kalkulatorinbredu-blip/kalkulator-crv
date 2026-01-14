import streamlit as st
import pandas as pd
import os
import base64

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Kalkulator Doboru", page_icon="🐄", layout="wide")

SCIEZKA_RODOWODY = "rodowody.parquet"
SCIEZKA_OFERTA = "Oferta CRV.xlsx"

MAPA_CECH = {
    "Kg_mleka": "Kilogramy mleka",
    "%_tluszczu": "% tłuszczu",
    "%_bialka": "% białka",
    "Nogi": "Nogi",
    "Wymie": "Wymię",
    "Ocena_ogolna": "Ocena ogólna",
    "NVI": "NVI",
    "LKS": "LKS",
    "INET": "INET",
    "Dlugowiecznosc": "Długowieczność",
    "Wykorzystanie_paszy": "Wykorzystanie paszy",
    "Zdrow._wymienia": "Zdrowotność wymienia",
    "Zdrowotnosc_racic": "Zdrowotność racic",
    "Ketoza": "Ketoza",
    "Latwosc_wycielen": "Łatwość wycieleń",
    "Plod._Corek": "Płodność córek",
    "Dlugosc_strzykow": "Długość strzyków"
}

# --- 2. FUNKCJE POMOCNICZE ---
def dodaj_tlo(nazwa_pliku):
    try:
        if os.path.exists(nazwa_pliku):
            with open(nazwa_pliku, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode()
            # NAPRAWIONE TŁO: Używamy {{ }} dla CSS, ale { } dla zmiennej Pythona
            st.markdown(f"""
                <style>
                .stApp {{
                    background-image: linear-gradient(to bottom, white 50%, rgba(255,255,255,0) 100%),
                                      linear-gradient(rgba(255,255,255,0.7), rgba(255,255,255,0.7)),
                                      url(data:image/jpg;base64,{encoded_string});
                    background-position: bottom; background-repeat: no-repeat; background-size: cover;
                }}
                </style>""", unsafe_allow_html=True)
    except: pass

@st.cache_data
def wczytaj_i_przygotuj_dane():
    try:
        if not os.path.exists(SCIEZKA_RODOWODY) or not os.path.exists(SCIEZKA_OFERTA):
            return None, None, None, None, None

        # Odczyt danych
        df_rod = pd.read_parquet(SCIEZKA_RODOWODY, engine='pyarrow')
        df_off = pd.read_excel(SCIEZKA_OFERTA, dtype=str)

        # Standaryzacja nazw kolumn
        df_rod.columns = df_rod.columns.str.strip()
        df_off.columns = df_off.columns.str.strip()

        # Normalizacja nazw kluczowych kolumn
        rename_map = {'ID_Bull': 'ID_bull', 'ID_sire': 'ID_Sire', 'ID_sire_of_dam': 'ID_Maternal_Grand_Sire'}
        df_rod = df_rod.rename(columns=rename_map)
        df_off = df_off.rename(columns=rename_map)

        # Optymalizacja RAM w cache
        cols_to_std = ['ID_bull', 'ID_Sire', 'ID_Dam', 'Bull_name', 'ID_Maternal_Grand_Sire', 'ID_Maternal_Grand_Dam_Sire']
        for df_temp in [df_rod, df_off]:
            for col in cols_to_std:
                if col in df_temp.columns:
                    df_temp[col] = df_temp[col].astype(str).str.strip().replace(['nan', 'None', '', 'nan '], 'BRAK')

        # Przygotowanie nazw wyświetlanych
        df_rod = df_rod[df_rod['ID_bull'] != "BRAK"].drop_duplicates(subset=['ID_bull'])
        df_rod['Display_name'] = df_rod['Bull_name'] + " (" + df_rod['ID_bull'] + ")"

        # Mapy pomocnicze
        n2id = pd.Series(df_rod['ID_bull'].values, index=df_rod['Display_name']).to_dict()
        id2n = pd.Series(df_rod['Bull_name'].values, index=df_rod['ID_bull']).to_dict()
        id2rodzic = pd.Series(zip(df_rod['ID_Sire'], df_rod['ID_Dam']), index=df_rod['ID_bull']).to_dict()

        return df_rod, df_off, n2id, id2rodzic, id2n
    except Exception as e:
        st.error(f"Błąd krytyczny danych: {e}")
        return None, None, None, None, None

# --- 3. SERCE APLIKACJI (Bez zmian w logice) ---
def pobierz_drzewo_z_poziomem(start_id, _id_do_rodzicow_map, max_g, poziom_startowy):
    drzewo = {}
    def _szukaj(cid, g):
        if cid in ["BRAK", "nan", ""] or g > max_g: return
        if cid not in drzewo or g < drzewo[cid]:
            drzewo[cid] = g
            rodzice = _id_do_rodzicow_map.get(cid)
            if rodzice:
                ojciec, matka = rodzice
                _szukaj(ojciec, g + 1)
                _szukaj(matka, g + 1)
    _szukaj(start_id, poziom_startowy)
    return drzewo

# --- 4. URUCHOMIENIE INTERFEJSU ---
dodaj_tlo("tlo_kalkulator.jpg")
df_rodowody, df_crv, nazwa_to_id_map, id_do_rodzicow_map, id_do_nazwy_map = wczytaj_i_przygotuj_dane()

if df_rodowody is not None:
    st.success("✅ Baza załadowana!")
    
    st.sidebar.header("Ustawienia analizy")
    prog = st.sidebar.selectbox("Dopuszczalne pokrewieństwo:", [4, 6, 10, 12], index=1)
    mapowanie_glebokosci = {4: 14, 6: 12, 10: 8, 12: 6}
    glebokosc_analizy = mapowanie_glebokosci[prog]

    st.header("Krok 1: Twoje stado")
    wybrane_nazwy = st.multiselect("Wybierz buhaje obecnie używane w stadzie:", sorted(nazwa_to_id_map.keys()))

    st.header("Krok 2: Kryteria selekcji")
    c1, c2 = st.columns(2)
    with c1:
        wybrane_rasy = st.multiselect("Wybierz rasy:", sorted(df_crv['Rasa'].unique().tolist()) if 'Rasa' in df_crv.columns else [])
    with c2:
        a2a2 = st.checkbox("Beta-kazeina A2A2")
        kappa = st.checkbox("Kappa-kazeina AB/BB")
        robot = st.checkbox("Indeks robotowy")

    st.subheader("Dodatkowe cechy funkcjonalne:")
    dostepne_cechy = [col for col in MAPA_CECH.keys() if col in df_crv.columns]
    wybrane_techniczne = st.multiselect("Wybierz cechy do parametrów:", options=dostepne_cechy, format_func=lambda x: MAPA_CECH[x])
    
    kryteria_suwakow = []
    for tech_name in wybrane_techniczne:
        pretty_name = MAPA_CECH[tech_name]
        dane_kolumny = pd.to_numeric(df_crv[tech_name], errors='coerce').dropna()
        if not dane_kolumny.empty:
            min_v, max_v, med_v = float(dane_kolumny.min()), float(dane_kolumny.max()), float(dane_kolumny.median())
            if tech_name in ["%_tluszczu", "%_bialka"]:
                # NAPRAWIONE: używamy pojedynczych klamer { } do wstawienia nazwy
                v = st.slider(f"Min. {pretty_name}", min_v, max_v, med_v, step=0.01, format="%.2f")
            else:
                # NAPRAWIONE: używamy pojedynczych klamer { } do wstawienia nazwy
                v = st.slider(f"Min. {pretty_name}", int(min_v), int(max_v), int(med_v), step=1)
            kryteria_suwakow.append((tech_name, v))

    if st.button("🐮 Rozpocznij analizę doboru", type="primary", use_container_width=True):
        if not wybrane_nazwy:
            st.warning("Najpierw wskaż buhaje używane w stadzie.")
        else:
            with st.spinner("Analiza drzew genealogicznych..."):
                # (Logika budowania stada - bez zmian)
                mapa_konfliktow_stada = {}
                for nazwa_wyswietlana in wybrane_nazwy:
                    ids_stada = nazwa_to_id_map[nazwa_wyswietlana]
                    nazwa_czysta = id_do_nazwy_map.get(ids_stada, nazwa_wyswietlana)
                    def _buduj_stado(cid, g):
                        if cid in ["BRAK", "nan", ""] or g > 6: return
                        if cid not in mapa_konfliktow_stada: mapa_konfliktow_stada[cid] = nazwa_czysta
                        rodzice = id_do_rodzicow_map.get(cid)
                        if rodzice:
                            o, m = rodzice
                            _buduj_stado(o, g + 1); _buduj_stado(m, g + 1)
                    _buduj_stado(ids_stada, 0)

                # (Logika filtrowania - bez zmian)
                df_wynik = df_crv.copy()
                if wybrane_rasy: df_wynik = df_wynik[df_wynik['Rasa'].isin(wybrane_rasy)]
                if a2a2 and 'Beta_kazeina' in df_wynik.columns: df_wynik = df_wynik[df_wynik['Beta_kazeina'] == 'A2A2']
                if kappa and 'Kappa_kazeina' in df_wynik.columns: df_wynik = df_wynik[df_wynik['Kappa_kazeina'].isin(['AB', 'BB'])]
                if robot and 'Wydajnosc_robotowa' in df_wynik.columns:
                    df_wynik = df_wynik[pd.to_numeric(df_wynik['Wydajnosc_robotowa'], errors='coerce') >= 98]
                for c, p in kryteria_suwakow:
                    df_wynik = df_wynik[pd.to_numeric(df_wynik[c], errors='coerce') >= p]

                finalne = []
                raport_detektywa = []

                # (Logika analizy inbredu - bez zmian)
                for idx, wiersz in df_wynik.iterrows():
                    id_o = str(wiersz.get('ID_bull', 'BRAK'))
                    sondy = [(id_o, 0), (str(wiersz.get('ID_Sire', 'BRAK')), 1),
                             (str(wiersz.get('ID_Maternal_Grand_Sire', 'BRAK')), 2),
                             (str(wiersz.get('ID_Maternal_Grand_Dam_Sire', 'BRAK')), 3)]
                    
                    pelne_drzewo_oferty = {}
                    for sid, poziom in sondy:
                        if sid != "BRAK":
                            dz = pobierz_drzewo_z_poziomem(sid, id_do_rodzicow_map, glebokosc_analizy, poziom)
                            for k, v in dz.items():
                                if k not in pelne_drzewo_oferty or v < pelne_drzewo_oferty[k]: pelne_drzewo_oferty[k] = v

                    konflikty = set(pelne_drzewo_oferty.keys()) & set(mapa_konfliktow_stada.keys())
                    if not konflikty:
                        finalne.append(wiersz)
                    else:
                        najblizszy_id = min(konflikty, key=lambda x: pelne_drzewo_oferty[x])
                        odleglosc = pelne_drzewo_oferty[najblizszy_id]
                        nazwa_p = id_do_nazwy_map.get(najblizszy_id, najblizszy_id)
                        winowajca = mapa_konfliktow_stada[najblizszy_id]
                        # NAPRAWIONE: używamy pojedynczych klamer { } do wstawiania danych
                        relacja = {0: "TEN SAM BUHAJ", 1: "OJCIEC", 2: "DZIADEK", 3: "PRADZIADEK"}.get(odleglosc, f"{odleglosc}. POKOLENIE")
                        raport_detektywa.append({
                            "Buhaj z oferty": wiersz['Bull_name'], "Konflikt z": winowajca,
                            # NAPRAWIONE: używamy pojedynczych klamer { } do wstawiania danych
                            "Wspólny przodek": f"{nazwa_p} ({najblizszy_id})", "Relacja": relacja
                        })

                if finalne:
                    # NAPRAWIONE: wstawiamy liczbę znalezionych buhajów
                    st.success(f"Znaleziono {len(finalne)} bezpiecznych buhajów.")
                    st.dataframe(pd.DataFrame(finalne)[['Bull_name', 'ID_bull', 'Rasa']], use_container_width=True)
                else: st.error("Brak bezpiecznych dopasowań.")
                if raport_detektywa:
                    with st.expander("🕵️ ANALIZA KONFLIKTÓW"): st.table(pd.DataFrame(raport_detektywa))
else:
    st.error("Problem z plikami danych. Sprawdź rodowody.parquet i Oferta CRV.xlsx.")