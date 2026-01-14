import streamlit as st
import pandas as pd
import os
import base64  # zostawiamy, jeśli używasz go np. do wyświetlania logo lub pobierania plików

# --- KONFIGURACJA ŚCIEŻEK ---
SCIEZKA_LOKALNA_DO_KLUCZA_JSON = "noted-wares-474211-g2-e39e145b3780.json"
SCIEZKA_GS_DO_RODOWODOW = "gs://dane_kalkulator_inbredowy_anna/rodowody.xlsx"

st.set_page_config(page_title="Kalkulator Doboru", page_icon="🐮", layout="wide")

# --- MAPA CECH (Techniczna Nazwa : Ładna Nazwa) ---
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

# --- FUNKCJA TŁA ---
def dodaj_tlo(nazwa_pliku):
    try:
        with open(nazwa_pliku, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: linear-gradient(to bottom, white 50%, rgba(255,255,255,0) 100%),
                              linear-gradient(rgba(255,255,255,0.7), rgba(255,255,255,0.7)),
                              url(data:image/jpg;base64,{encoded_string});
            background-position: bottom; background-repeat: no-repeat; background-size: cover;
        }}
        </style>
        """, unsafe_allow_html=True)
    except: pass

# --- WCZYTYWANIE DANYCH ---
@st.cache_data
def wczytaj_dane():
    try:
        # 1. Ścieżki do plików lokalnych (są w tym samym folderze na Renderze)
        sciezka_rodowody = 'rodowody.parquet'
        sciezka_oferta = 'Oferta CRV.xlsx'
        
        # 2. Szybki odczyt danych
        if not os.path.exists(sciezka_rodowody):
            st.error(f"❌ Nie znaleziono pliku: {sciezka_rodowody}")
            return None, None, None, None, None
            
        df_rodowody = pd.read_parquet(sciezka_rodowody)
        df_crv = pd.read_excel(sciezka_oferta, dtype=str)
        
        # 3. Czyszczenie nazw kolumn
        df_rodowody.columns = df_rodowody.columns.str.strip()
        df_crv.columns = df_crv.columns.str.strip()

        # --- Dalsza część standaryzacji (renaming i mapy) zostaje bez zmian ---

        # Normalizacja nazw kolumn
        rename_map = {'ID_Bull': 'ID_bull', 'ID_sire': 'ID_Sire', 'ID_sire_of_dam': 'ID_Maternal_Grand_Sire'}
        df_rodowody = df_rodowody.rename(columns=rename_map)
        df_crv = df_crv.rename(columns=rename_map)
        
        cols_to_std = ['ID_bull', 'ID_Sire', 'ID_Dam', 'Bull_name', 'ID_Maternal_Grand_Sire', 'ID_Maternal_Grand_Dam_Sire']
        for df in [df_rodowody, df_crv]:
            for col in cols_to_std:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip().replace(['nan', 'None', '', 'nan '], 'BRAK')

        df_rodowody = df_rodowody[df_rodowody['ID_bull'] != "BRAK"].drop_duplicates(subset=['ID_bull'])
        df_rodowody['Display_name'] = df_rodowody['Bull_name'] + " (" + df_rodowody['ID_bull'] + ")"
        
        nazwa_to_id_map = pd.Series(df_rodowody['ID_bull'].values, index=df_rodowody['Display_name']).to_dict()
        id_do_nazwy_map = pd.Series(df_rodowody['Bull_name'].values, index=df_rodowody['ID_bull']).to_dict()
        id_do_rodzicow_map = pd.Series(zip(df_rodowody['ID_Sire'], df_rodowody['ID_Dam']), index=df_rodowody['ID_bull']).to_dict()
            
        return df_rodowody, df_crv, nazwa_to_id_map, id_do_rodzicow_map, id_do_nazwy_map
    except Exception as e:
        st.error(f"Błąd danych: {e}")
        return None, None, None, None, None

# --- SILNIK REKURENCYJNY ---
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

# --- START APLIKACJI ---
dodaj_tlo('tlo_kalkulator.jpg')
df_rodowody, df_crv, nazwa_to_id_map, id_do_rodzicow_map, id_do_nazwy_map = wczytaj_dane()

if df_rodowody is not None:
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

    # --- POPRAWIONE SUWAKI DLA CECH FUNKCJONALNYCH ---
    st.subheader("Dodatkowe cechy:")
    
    # Filtrujemy tylko te kolumny, które istnieją w pliku Excel i są w naszej MAPA_CECH
    dostepne_cechy = [col for col in MAPA_CECH.keys() if col in df_crv.columns]
    
    wybrane_techniczne = st.multiselect(
        "Wybierz cechy do ustawienia parametrów:",
        options=dostepne_cechy,
        format_func=lambda x: MAPA_CECH[x] # Tutaj zamieniamy tech-nazwę na ładną polską nazwę
    )
    
    kryteria_suwakow = []
    for tech_name in wybrane_techniczne:
        pretty_name = MAPA_CECH[tech_name]
        dane_kolumny = pd.to_numeric(df_crv[tech_name], errors='coerce').dropna()
        
        if not dane_kolumny.empty:
            min_v = float(dane_kolumny.min())
            max_v = float(dane_kolumny.max())
            med_v = float(dane_kolumny.median())
            
            # Formaty dla procentów
            if tech_name in ["%_tluszczu", "%_bialka"]:
                v = st.slider(f"Min. {pretty_name}", min_v, max_v, med_v, step=0.01, format="%.2f")
            else:
                v = st.slider(f"Min. {pretty_name}", int(min_v), int(max_v), int(med_v), step=1)
            
            kryteria_suwakow.append((tech_name, v))

    if st.button("🐮 Rozpocznij analizę doboru", type="primary", use_container_width=True):
        if not wybrane_nazwy:
            st.warning("Najpierw wskaż buhaje używane w stadzie.")
        else:
            with st.spinner("Analiza..."):
                id_stada = [nazwa_to_id_map[n] for n in wybrane_nazwy]
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

                for idx, wiersz in df_wynik.iterrows():
                    id_o = str(wiersz.get('ID_bull', 'BRAK'))
                    sondy = [
                        (id_o, 0),
                        (str(wiersz.get('ID_Sire', 'BRAK')), 1),
                        (str(wiersz.get('ID_Maternal_Grand_Sire', 'BRAK')), 2),
                        (str(wiersz.get('ID_Maternal_Grand_Dam_Sire', 'BRAK')), 3)
                    ]
                    
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
                        relacja = {0: "TEN SAM BUHAJ", 1: "OJCIEC", 2: "DZIADEK", 3: "PRADZIADEK", 4: "PRAPRADZIADEK"}.get(odleglosc, f"{odleglosc}. POKOLENIE")
                        raport_detektywa.append({
                            "Buhaj z oferty": wiersz['Bull_name'],
                            "Konflikt z buhajem ze stada": winowajca,
                            "Wspólny przodek": f"{nazwa_p} ({najblizszy_id})",
                            "Relacja dla oferty": relacja
                        })

                if finalne:
                    st.success(f"Znaleziono {len(finalne)} bezpiecznych buhajów.")
                    st.dataframe(pd.DataFrame(finalne)[['Bull_name', 'ID_bull', 'Rasa']], use_container_width=True)
                else: st.error("Brak dopasowań.")
                if raport_detektywa:
                    with st.expander("🕵️ SZCZEGÓŁOWA ANALIZA KONFLIKTÓW"): st.table(pd.DataFrame(raport_detektywa))