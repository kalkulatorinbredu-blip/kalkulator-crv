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

# --- Funkcja wczytująca i czyszcząca dane ---
@st.cache_data
def wczytaj_dane():
    try:
        # === WCZYTYWANIE Z GOOGLE CLOUD STORAGE (WERSJA DOCELOWA) ===
        creds_dict = {
            "type": "service_account",
            "project_id": st.secrets["project_id"],
            "private_key_id": st.secrets.get("private_key_id", ""),
            "private_key": st.secrets["private_key"],
            "client_email": st.secrets["client_email"],
            "client_id": st.secrets.get("client_id", ""),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": st.secrets.get("client_x509_cert_url", "")
        }
        fs = gcsfs.GCSFileSystem(token=creds_dict)
        
        # VVVV WAŻNE: Wklej tutaj swoją ścieżkę do pliku z rodowodami VVVV
        sciezka_do_rodowodow = "gs://dane_kalkulator_inbredowy_anna/rodowody.xlsx" 
        
        with fs.open(sciezka_do_rodowodow) as f:
             df_rodowody = pd.read_excel(f)
        
        # Plik 'Oferta CRV.xlsx' musi znajdować się w Twoim repozytorium GitHub
        df_crv = pd.read_excel('Oferta CRV.xlsx')

        # === WCZYTYWANIE LOKALNE (DO TESTÓW) - WYŁĄCZONE ===
        # df_rodowody = pd.read_excel('rodowody.xlsx')
        # df_crv = pd.read_excel('Oferta CRV.xlsx')
        
        # Definicja kluczowych kolumn
        glowna_kolumna_id = 'ID_bull'
        glowna_kolumna_nazwy = 'Bull_name'
        kolumny_przodkow_id = ['ID_Sire', 'ID_Dam', 'ID_Maternal_Grand_Sire']

        # Normalizacja kolumn ID na wspólny format (string)
        id_cols_to_normalize = [glowna_kolumna_id] + kolumny_przodkow_id
        for df in [df_rodowody, df_crv]:
            for col in id_cols_to_normalize:
                if col in df.columns:
                    df.loc[:, col] = df[col].astype(str).str.strip()

        # Czyszczenie kolumn z nazwami
        kolumny_z_nazwami_do_czyszczenia = [
            'Bull_name', 'Bull_short_name', 'Sire_name', 'Sire_short_name',
            'Dam_name', 'Maternal_Grand_Sire_name', 'Maternal_Grand_Sire_short_name'
        ]
        for kolumna in kolumny_z_nazwami_do_czyszczenia:
            if kolumna in df_rodowody.columns:
                df_rodowody.loc[:, kolumna] = df_rodowody[kolumna].fillna('').astype(str).str.strip().str.upper()
            if kolumna in df_crv.columns:
                df_crv.loc[:, kolumna] = df_crv[kolumna].fillna('').astype(str).str.strip().str.upper()

        return df_rodowody, df_crv, glowna_kolumna_id, glowna_kolumna_nazwy, kolumny_przodkow_id

    except Exception as e:
        st.error(f"KRYTYCZNY BŁĄD podczas wczytywania danych: {e}")
        st.info("Sprawdź, czy: \n1. Ścieżka 'gs://' jest poprawna. \n2. Plik 'Oferta CRV.xlsx' jest w repozytorium. \n3. Sekrety w panelu Streamlit Cloud są poprawnie skonfigurowane.")
        return None, None, None, None, None

# --- Silnik sprawdzający pokrewieństwo (wersja ostateczna) ---
@st.cache_data
def czy_spokrewnione(id_buhaja1, id_buhaja2, _df_rodowody, glowna_kolumna_id, kolumny_przodkow_id, max_glebokosc):
    def _zbierz_przodkow(bull_id, glebokosc, odwiedzone):
        bull_id = str(bull_id).strip() if pd.notna(bull_id) else None
        if not bull_id or bull_id in ['NAN', 'NONE', ''] or bull_id in odwiedzone or glebokosc >= max_glebokosc:
            return set()
            
        odwiedzone.add(bull_id)
        przodkowie = {bull_id}
        
        try:
            wiersz = _df_rodowody.loc[_df_rodowody[glowna_kolumna_id] == bull_id].iloc[0]
            
            for kolumna_przodka in kolumny_przodkow_id:
                if kolumna_przodka in wiersz:
                    przodek_id = str(wiersz.get(kolumna_przodka)).strip()
                    przodkowie.update(_zbierz_przodkow(przodek_id, glebokosc + 1, odwiedzone))
        except IndexError:
            pass
        return przodkowie

    id1_norm = str(id_buhaja1).strip()
    id2_norm = str(id_buhaja2).strip()
    
    drzewo1 = _zbierz_przodkow(id1_norm, 0, set())
    drzewo2 = _zbierz_przodkow(id2_norm, 0, set())
    
    return not drzewo1.isdisjoint(drzewo2)

# --- Główna część aplikacji (Interfejs) ---
try:
    dodaj_tlo('tlo_kalkulator.jpg')
    st.image('logo.png', width=150)
except Exception:
    pass

st.title("🧮 Kalkulator doboru buhajów")

df_rodowody, df_crv, glowna_kolumna_id, glowna_kolumna_nazwy, kolumny_przodkow_id = wczytaj_dane()

if df_rodowody is not None and df_crv is not None:
    st.sidebar.header("Ustawienia analizy")
    glebokosc_analizy = st.sidebar.slider("Głębokość analizy (pokolenia):", min_value=1, max_value=8, value=4, help="Jak głęboko program ma szukać wspólnych przodków.")
    
    st.markdown("---")
    st.header("Krok 1: Twoje stado")
    
    df_rodowody['display_name'] = df_rodowody[glowna_kolumna_nazwy].astype(str) + " (" + df_rodowody[glowna_kolumna_id].astype(str) + ")"
    lista_do_wyboru = sorted(df_rodowody['display_name'].unique())
    wybrane_etykiety = st.multiselect("Wybierz buhaje, których używałeś w swoim stadzie:", lista_do_wyboru)

    st.markdown("---")
    st.header("Krok 2: Kryteria selekcji")

    st.subheader("Rasa:")
    if 'Rasa' in df_crv.columns:
        opcje_ras = sorted(df_crv['Rasa'].dropna().unique().tolist())
        wybrane_rasy = st.multiselect("Wybierz interesujące Cię rasy:", opcje_ras, default=opcje_ras)
    else:
        wybrane_rasy = []

    st.subheader("Cechy specjalne:")
    czy_tylko_a2a2 = st.checkbox("Tylko beta-kazeina A2A2")
    czy_kappa_ab_bb = st.checkbox("Tylko kappa-kazeina AB lub BB")
    czy_indeks_robotowy = st.checkbox("Wysoki Indeks Robotowy")
    
    st.markdown("---")
    st.subheader("Dodatkowe cechy (indeksy):")
    
    potencjalne_cechy = df_crv.select_dtypes(include=['number']).columns.tolist()
    wykluczone_slowa = ['id', 'rok', 'numer']
    kolumny_cech = sorted([col for col in potencjalne_cechy if not any(slowo in col.lower() for slowo in wykluczone_slowa)])
    
    wybrane_cechy = st.multiselect("Wybierz cechy do filtrowania za pomocą suwaków:", kolumny_cech)

    kryteria_suwakow = []
    if wybrane_cechy:
        for cecha in wybrane_cechy:
            min_val = float(df_crv[cecha].dropna().min())
            max_val = float(df_crv[cecha].dropna().max())
            median_val = float(df_crv[cecha].dropna().median())
            prog = st.slider(f"Min. wartość dla '{cecha}':", min_value=min_val, max_value=max_val, value=median_val)
            kryteria_suwakow.append({'cecha': cecha, 'prog': prog})

    st.markdown("---")
    
    if st.button("🐮 Znajdź pasujące buhaje!", type="primary", use_container_width=True):
        buhaje_w_stadzie_id = df_rodowody[df_rodowody['display_name'].isin(wybrane_etykiety)][glowna_kolumna_id].tolist()

        if not buhaje_w_stadzie_id:
            st.warning("Musisz wybrać przynajmniej jednego buhaja ze swojego stada.")
        else:
            with st.spinner("Trwa głęboka analiza rodowodów..."):
                rekomendacje = df_crv.copy()
                
                if 'Rasa' in rekomendacje.columns and wybrane_rasy:
                    rekomendacje = rekomendacje[rekomendacje['Rasa'].isin(wybrane_rasy)]
                
                for kryterium in kryteria_suwakow:
                    rekomendacje = rekomendacje[rekomendacje[kryterium['cecha']] >= kryterium['prog']]
                
                niespokrewnione_buhaje = []
                for _, buhaj_crv in rekomendacje.iterrows():
                    id_buhaja_crv = buhaj_crv.get(glowna_kolumna_id)

                    if pd.notna(id_buhaja_crv):
                        jest_spokrewniony = any(czy_spokrewnione(id_buhaja_crv, moj_buhaj_id, df_rodowody, glowna_kolumna_id, kolumny_przodkow_id, glebokosc_analizy) for moj_buhaj_id in buhaje_w_stadzie_id)
                        
                        if not jest_spokrewniony:
                            niespokrewnione_buhaje.append(buhaj_crv)
            
            st.header("Wyniki:")
            if not niespokrewnione_buhaje:
                st.error("Nie znaleziono żadnych niespokrewnionych buhajów spełniających podane kryteria.")
            else:
                st.success(f"Znaleziono {len(niespokrewnione_buhaje)} pasujących, niespokrewnionych buhajów:")
                wyniki_df = pd.DataFrame(niespokrewnione_buhaje)
                
                kolumny_do_wyswietlenia = [glowna_kolumna_nazwy, glowna_kolumna_id]
                if 'Rasa' in wyniki_df.columns:
                    kolumny_do_wyswietlenia.append('Rasa')
                
                kolumny_do_wyswietlenia.extend([k['cecha'] for k in kryteria_suwakow])
                
                istniejace_kolumny = [kol for kol in list(dict.fromkeys(kolumny_do_wyswietlenia)) if kol in wyniki_df.columns]
                st.dataframe(wyniki_df[istniejace_kolumny], use_container_width=True)