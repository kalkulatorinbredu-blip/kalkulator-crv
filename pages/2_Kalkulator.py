import streamlit as st
import pandas as pd
import gcsfs
import json
import base64
import os

# --- KONFIGURACJA ŚCIEŻEK ---
# Plik JSON musi znajdować się w głównym folderze projektu (obok app.py)
SCIEZKA_LOKALNA_DO_KLUCZA_JSON = "noted-wares-474211-g2-e39e145b3780.json"
SCIEZKA_GS_DO_RODOWODOW = "gs://dane_kalkulator_inbredowy_anna/rodowody.xlsx"

# --- Konfiguracja strony ---
st.set_page_config(page_title="Kalkulator", page_icon="🧮", layout="wide")

# --- Funkcja tła ---
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
            background-position: bottom;
            background-repeat: no-repeat;
            background-size: cover;
        }}
        header {{
            background-color: transparent !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
        )
    except:
        pass

# --- FUNKCJA WCZYTUJĄCA DANE ---
@st.cache_data
def wczytaj_dane():
    try:
        # Bardziej niezawodne sprawdzenie, czy jesteśmy na Streamlit Cloud
        is_cloud = False
        try:
            if st.secrets and "project_id" in st.secrets:
                is_cloud = True
        except:
            is_cloud = False

        if is_cloud:
            # Używamy danych z "Secrets" na Streamlit Cloud
            creds_dict = {
                "type": "service_account", 
                "project_id": st.secrets["project_id"],
                "private_key": st.secrets["private_key"], 
                "client_email": st.secrets["client_email"],
                "token_uri": "https://oauth2.googleapis.com/token",
            }
            fs = gcsfs.GCSFileSystem(token=creds_dict)
        else:
            # Jesteśmy lokalnie - szukamy pliku JSON
            if not os.path.exists(SCIEZKA_LOKALNA_DO_KLUCZA_JSON):
                st.error(f"Nie znaleziono pliku klucza: {SCIEZKA_LOKALNA_DO_KLUCZA_JSON} w folderze projektu!")
                return None, None, None, None
            
            with open(SCIEZKA_LOKALNA_DO_KLUCZA_JSON, 'r') as f:
                klucz_json = json.load(f)
            fs = gcsfs.GCSFileSystem(token=klucz_json)
        
        st.info("Wczytuję dane rodowodowe... Proszę czekać.")
        with fs.open(SCIEZKA_GS_DO_RODOWODOW) as f:
            df_rodowody = pd.read_excel(f, dtype=str)

        df_crv = pd.read_excel('Oferta CRV.xlsx')
        
        # Standaryzacja nazw kolumn
        df_rodowody.columns = df_rodowody.columns.str.strip()
        df_crv.columns = df_crv.columns.str.strip()
        
        # ID i nazwy jako tekst bez spacji
        for df in [df_rodowody, df_crv]:
            for col in ['ID_bull', 'ID_Sire', 'ID_Dam', 'Bull_name', 'Sire_name', 'Dam_name']:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip().replace('nan', 'BRAK')

        df_rodowody = df_rodowody[df_rodowody['ID_bull'] != "BRAK"].dropna(subset=['ID_bull', 'Bull_name']).drop_duplicates(subset=['ID_bull'])

        # Mapy danych do analizy pokrewieństwa
        nazwa_do_id_map = pd.Series(df_rodowody['ID_bull'].values, index=df_rodowody['Bull_name']).to_dict()
        id_do_rodzicow_map = pd.Series(zip(df_rodowody['ID_Sire'], df_rodowody['ID_Dam']), index=df_rodowody['ID_bull']).to_dict()
            
        return df_rodowody, df_crv, nazwa_do_id_map, id_do_rodzicow_map
    except Exception as e:
        st.error(f"Błąd krytyczny danych: {e}")
        return None, None, None, None

# --- SILNIK ANALIZY POKREWIEŃSTWA ---
def czy_spokrewnione(id_buhaja1, id_buhaja2, _id_do_rodzicow_map, max_glebokosc):
    def _zbierz_przodkow(bull_id, glebokosc, odwiedzone):
        if not isinstance(bull_id, str) or bull_id in ["BRAK", "nan", ""] or bull_id in odwiedzone or glebokosc > max_glebokosc:
            return set()
        odwiedzone.add(bull_id)
        przodkowie = {bull_id}
        ojciec, matka = _id_do_rodzicow_map.get(bull_id, ("BRAK", "BRAK"))
        przodkowie.update(_zbierz_przodkow(ojciec, glebokosc + 1, odwiedzone))
        przodkowie.update(_zbierz_przodkow(matka, glebokosc + 1, odwiedzone))
        return przodkowie
    
    set1 = _zbierz_przodkow(id_buhaja1, 1, set())
    set2 = _zbierz_przodkow(id_buhaja2, 1, set())
    return not set1.isdisjoint(set2)

# --- START APLIKACJI ---
dodaj_tlo('tlo_kalkulator.jpg')
st.title("🧮 Kalkulator doboru buhajów")

df_rodowody, df_crv, nazwa_do_id_map, id_do_rodzicow_map = wczytaj_dane()

if df_rodowody is not None and nazwa_do_id_map is not None:
    # Sidebar - Wybór progu pokrewieństwa
    st.sidebar.header("Ustawienia analizy")
    prog_pokrewienstwa = st.sidebar.selectbox(
        "Maksymalne dopuszczalne pokrewieństwo:",
        options=[4, 6, 10, 12],
        format_func=lambda x: f"poniżej {x}%",
        index=1
    )
    # Mapowanie progu na głębokość szukania przodków
    mapowanie_glebokosci = {4: 5, 6: 4, 10: 3, 12: 2}
    glebokosc_analizy = mapowanie_glebokosci[prog_pokrewienstwa]
    
    st.markdown("---")
    st.header("Krok 1: Twoje stado")
    wybrane_nazwy = st.multiselect("Wybierz buhaje używane w stadzie:", sorted(nazwa_do_id_map.keys()))

    st.markdown("---")
    st.header("Krok 2: Kryteria selekcji")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Rasa:")
        rasy_dostepne = sorted(df_crv['Rasa'].dropna().unique().tolist()) if 'Rasa' in df_crv.columns else []
        wybrane_rasy = st.multiselect("Wybierz rasy:", rasy_dostepne)
    
    with c2:
        st.subheader("Cechy specjalne:")
        a2a2 = st.checkbox("Beta-kazeina A2A2")
        kappa = st.checkbox("Kappa-kazeina AB/BB")
        robot = st.checkbox("Indeks Robotowy")

    st.markdown("---")
    st.subheader("Dodatkowe indeksy:")
    kolumny_num = sorted(df_crv.select_dtypes(include=['number']).columns.tolist())
    wybrane_cechy = st.multiselect("Dodaj suwaki dla cech:", kolumny_num)

    kryteria_suwakow = []
    for cecha in wybrane_cechy:
        dane_c = pd.to_numeric(df_crv[cecha], errors='coerce').dropna()
        if not dane_c.empty:
            # Rozróżnienie suwaka dziesiętnego (%) od całkowitego
            if '%' in cecha:
                v = st.slider(f"Min. {cecha}", float(dane_c.min()), float(dane_c.max()), float(dane_c.median()), 0.01, "%.2f")
            else:
                v = st.slider(f"Min. {cecha}", int(dane_c.min()), int(dane_c.max()), int(dane_c.median()), 1)
            kryteria_suwakow.append((cecha, v))

    st.markdown("---")

    if st.button("🐮 Znajdź pasujące buhaje!", type="primary", use_container_width=True):
        if not wybrane_nazwy:
            st.warning("Musisz wybrać chociaż jednego buhaja z Twojego stada (Krok 1).")
        else:
            with st.spinner("Przeszukuję ofertę i sprawdzam rodowody..."):
                id_stada = [nazwa_do_id_map[n] for n in wybrane_nazwy if n in nazwa_do_id_map]
                df_wynik = df_crv.copy()

                # Filtry opcjonalne (zastosowane tylko jeśli wybrane)
                if wybrane_rasy:
                    df_wynik = df_wynik[df_wynik['Rasa'].isin(wybrane_rasy)]
                if a2a2 and 'Beta_kazeina' in df_wynik.columns:
                    df_wynik = df_wynik[df_wynik['Beta_kazeina'] == 'A2A2']
                if kappa and 'Kappa_kazeina' in df_wynik.columns:
                    df_wynik = df_wynik[df_wynik['Kappa_kazeina'].isin(['AB', 'BB'])]
                if robot and 'Wydajnosc_robotowa' in df_wynik.columns:
                    df_wynik = df_wynik[pd.to_numeric(df_wynik['Wydajnosc_robotowa'], errors='coerce') >= 98]

                for cecha, prog in kryteria_suwakow:
                    df_wynik = df_wynik[pd.to_numeric(df_wynik[cecha], errors='coerce') >= prog]

                # Analiza pokrewieństwa
                finalne = []
                p_bar = st.progress(0)
                total = len(df_wynik)
                
                for i, (idx, wiersz) in enumerate(df_wynik.iterrows()):
                    id_o = str(wiersz['ID_bull']).strip()
                    spokrewniony = any(czy_spokrewnione(id_o, id_m, id_do_rodzicow_map, glebokosc_analizy) for id_m in id_stada)
                    if not spokrewniony:
                        finalne.append(wiersz)
                    if total > 0: p_bar.progress((i + 1) / total)
                
                p_bar.empty()
                if not finalne:
                    st.error("Brak buhajów spełniających kryteria.")
                else:
                    st.success(f"Znaleziono {len(finalne)} bezpiecznych propozycji!")
                    res_df = pd.DataFrame(finalne)
                    
                    # Kolumny do wyświetlenia w tabeli wyników
                    cols_to_show = ['Bull_name', 'Rasa'] + [c for c, p in kryteria_suwakow]
                    st.dataframe(res_df[[c for c in cols_to_show if c in res_df.columns]], use_container_width=True)
