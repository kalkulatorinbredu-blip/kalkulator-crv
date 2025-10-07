import streamlit as st
import pandas as pd
import gcsfs
import json
import base64

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
    except FileNotFoundError:
        st.warning(f"Nie znaleziono pliku tła: {nazwa_pliku}")

# --- Funkcja wczytująca dane ---
@st.cache_data
def wczytaj_dane():
    try:
        creds_dict = {
            "type": "service_account",
            "project_id": st.secrets["project_id"],
            "private_key_id": "",
            "private_key": st.secrets["private_key"],
            "client_email": st.secrets["client_email"],
            "client_id": "",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": ""
        }
        fs = gcsfs.GCSFileSystem(token=creds_dict)
        
        sciezka_do_rodowodow = "gs://dane_kalkulator_inbredowy_anna/rodowody.xlsx"
        
        with fs.open(sciezka_do_rodowodow) as f:
            df_rodowody = pd.read_excel(f)

        df_crv = pd.read_excel('Oferta CRV.xlsx')
        
        # Czyszczenie danych (konwertowanie ID na liczby, ignorując błędy)
        for df in [df_rodowody, df_crv]:
            for col in ['ID_bull', 'ID_Sire', 'ID_Dam']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Czyszczenie spacji w nazwach
        for df in [df_rodowody, df_crv]:
            for col in ['Bull_name', 'Sire_name', 'Dam_name']:
                 if col in df.columns:
                    df[col] = df[col].astype(str).str.strip()
            
        return df_rodowody, df_crv
    except Exception as e:
        st.error(f"BŁĄD podczas wczytywania danych: {e}")
        st.info("Sprawdź, czy sekrety i ścieżka 'gs://' są prawidłowe.")
        return None, None

# --- NOWY, ZAAWANSOWANY SILNIK POKREWIEŃSTWA OPARTY NA ID ---
@st.cache_data
def czy_spokrewnione(id_buhaja1, id_buhaja2, _id_do_rodzicow_map, max_glebokosc):
    
    def _zbierz_przodkow_id(bull_id, glebokosc, odwiedzone):
        if pd.isna(bull_id) or bull_id in odwiedzone or glebokosc > max_glebokosc:
            return set()
        
        odwiedzone.add(bull_id)
        przodkowie = {bull_id}
        
        # Błyskawiczne wyszukiwanie rodziców w mapie
        id_ojca, id_matki = _id_do_rodzicow_map.get(bull_id, (None, None))
        
        przodkowie.update(_zbierz_przodkow_id(id_ojca, glebokosc + 1, odwiedzone))
        przodkowie.update(_zbierz_przodkow_id(id_matki, glebokosc + 1, odwiedzone))
        
        return przodkowie

    drzewo1 = _zbierz_przodkow_id(id_buhaja1, 1, set())
    drzewo2 = _zbierz_przodkow_id(id_buhaja2, 1, set())
    
    return not drzewo1.isdisjoint(drzewo2)

# --- Główna część aplikacji ---
try:
    dodaj_tlo('tlo_kalkulator.jpg')
    st.image('logo.png', width=150)
except FileNotFoundError:
    st.warning("Nie znaleziono pliku logo.png lub tlo_kalkulator.jpg.")

st.title("🧮 Kalkulator doboru buhajów")

df_rodowody, df_crv = wczytaj_dane()

if df_rodowody is not None and df_crv is not None:
    # --- NOWOŚĆ: Przygotowanie map do szybkiego wyszukiwania ---
    # Tworzymy słowniki, które pozwolą błyskawicznie zamieniać nazwy na ID i znajdować rodziców
    nazwa_do_id_map = pd.Series(df_rodowody.ID_bull.values, index=df_rodowody.Bull_name).to_dict()
    id_do_rodzicow_map = pd.Series(zip(df_rodowody.ID_Sire, df_rodowody.ID_Dam), index=df_rodowody.ID_bull).to_dict()

    st.sidebar.header("Ustawienia analizy")
    glebokosc_analizy = st.sidebar.slider("Głębokość analizy (pokolenia):", min_value=2, max_value=8, value=5, help="Jak głęboko program ma szukać wspólnych przodków.")
    
    st.markdown("---")
    st.header("Krok 1: Twoje stado")
    # Użytkownik wciąż wybiera po nazwie
    wybrane_nazwy_buhajow = st.multiselect("Wybierz buhaje, których używałeś w swoim stadzie:", sorted(nazwa_do_id_map.keys()))

    # ... (reszta interfejsu bez zmian) ...
    st.markdown("---")
    st.header("Krok 2: Kryteria selekcji")

    st.subheader("Rasa:")
    if 'Rasa' in df_crv.columns:
        opcje_ras = df_crv['Rasa'].unique().tolist()
        wybrane_rasy = st.multiselect("Wybierz interesujące Cię rasy:", opcje_ras, default=opcje_ras)
    else:
        wybrane_rasy = []

    st.subheader("Cechy specjalne:")
    czy_tylko_a2a2 = st.checkbox("Tylko beta-kazeina A2A2", help="Wymaga kolumny 'Beta_kazeina'")
    czy_kappa_ab_bb = st.checkbox("Tylko kappa-kazeina AB lub BB", help="Wymaga kolumny 'Kappa_kazeina'")
    czy_indeks_robotowy = st.checkbox("Wysoki Indeks Robotowy", help="Filtruje 'Wydajnosc_robotowa' >= 98 oraz 'Szybkosc_doju' >= 96")

    st.markdown("---")
    st.subheader("Dodatkowe cechy (indeksy):")
    kolumny_cech = sorted([col for col in df_crv.columns if 'name' not in col.lower() and 'id' not in col.lower() and 'urodzenia' not in col.lower() and 'kazeina' not in col.lower() and 'rasa' not in col.lower()])
    wybrane_cechy = st.multiselect("Wybierz cechy do analizy za pomocą suwaków:", kolumny_cech)

    kryteria_suwakow = []
    if wybrane_cechy:
        for cecha in wybrane_cechy:
            prog = st.slider(f"Min. wartość dla '{cecha}':", int(df_crv[cecha].min()), int(df_crv[cecha].max()), int(df_crv[cecha].median()))
            kryteria_suwakow.append({'cecha': cecha, 'prog': prog})

    st.markdown("---")

    if st.button("🐮 Znajdź pasujące buhaje!", type="primary", use_container_width=True):
        if not wybrane_nazwy_buhajow:
            st.warning("Musisz wybrać przynajmniej jednego buhaja z Twojego stada.")
        elif 'Rasa' in df_crv.columns and not wybrane_rasy:
            st.warning("Musisz wybrać przynajmniej jedną rasę.")
        else:
            with st.spinner(f"Głęboka analiza rodowodów (do {glebokosc_analizy} pokoleń wstecz)..."):
                # Konwersja wybranych nazw na listę ID
                id_buhajow_w_stadzie = [nazwa_do_id_map[nazwa] for nazwa in wybrane_nazwy_buhajow]
                
                rekomendacje = df_crv.copy()

                # Filtrowanie (bez zmian)
                if 'Rasa' in rekomendacje.columns and wybrane_rasy:
                    rekomendacje = rekomendacje[rekomendacje['Rasa'].isin(wybrane_rasy)]
                if czy_tylko_a2a2 and 'Beta_kazeina' in rekomendacje.columns:
                    rekomendacje = rekomendacje[rekomendacje['Beta_kazeina'] == 'A2A2']
                if czy_kappa_ab_bb and 'Kappa_kazeina' in rekomendacje.columns:
                    rekomendacje = rekomendacje[rekomendacje['Kappa_kazeina'].isin(['AB', 'BB'])]
                if czy_indeks_robotowy and 'Wydajnosc_robotowa' in rekomendacje.columns and 'Szybkosc_doju' in rekomendacje.columns:
                    rekomendacje = rekomendacje[(rekomendacje['Wydajnosc_robotowa'] >= 98) & (rekomendacje['Szybkosc_doju'] >= 96)]
                for kryterium in kryteria_suwakow:
                    rekomendacje = rekomendacje[rekomendacje[kryterium['cecha']] >= kryterium['prog']]

                # Główna pętla analizy pokrewieństwa na ID
                niespokrewnione_buhaje = []
                progress_bar = st.progress(0, text="Analiza pokrewieństwa...")
                for i, (index, buhaj_crv) in enumerate(rekomendacje.iterrows()):
                    id_buhaja_crv = buhaj_crv['ID_bull']
                    jest_spokrewniony = any(czy_spokrewnione(id_buhaja_crv, id_mojego_buhaja, id_do_rodzicow_map, glebokosc_analizy) for id_mojego_buhaja in id_buhajow_w_stadzie)
                    if not jest_spokrewniony:
                        niespokrewnione_buhaje.append(buhaj_crv)
                    progress_bar.progress((i + 1) / len(rekomendacje), text=f"Analiza pokrewieństwa... ({i+1}/{len(rekomendacje)})")
                
                progress_bar.empty()
                st.header("Wyniki:")
                if not niespokrewnione_buhaje:
                    st.error("Brak buhajów spełniających wszystkie kryteria.")
                else:
                    st.success(f"Znaleziono {len(niespokrewnione_buhaje)} pasujących buhajów:")
                    wyniki_df = pd.DataFrame(niespokrewnione_buhaje)
                    
                    kolumny_do_wyswietlenia = ['Bull_name']
                    if 'Rasa' in wyniki_df.columns: kolumny_do_wyswietlenia.append('Rasa')
                    if czy_tylko_a2a2 and 'Beta_kazeina' in wyniki_df.columns: kolumny_do_wyswietlenia.append('Beta_kazeina')
                    if czy_kappa_ab_bb and 'Kappa_kazeina' in wyniki_df.columns: kolumny_do_wyswietlenia.append('Kappa_kazeina')
                    if czy_indeks_robotowy and 'Wydajnosc_robotowa' in wyniki_df.columns: kolumny_do_wyswietlenia.append('Wydajnosc_robotowa')
                    if czy_indeks_robotowy and 'Szybkosc_doju' in wyniki_df.columns: kolumny_do_wyswietlenia.append('Szybkosc_doju')
                    kolumny_do_wyswietlenia.extend(list(dict.fromkeys([k['cecha'] for k in kryteria_suwakow])))
                    
                    st.dataframe(wyniki_df[kolumny_do_wyswietlenia], use_container_width=True)