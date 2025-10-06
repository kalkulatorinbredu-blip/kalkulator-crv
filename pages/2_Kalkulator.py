import streamlit as st
import pandas as pd
import base64

# --- Konfiguracja strony ---
st.set_page_config(page_title="Kalkulator", page_icon="🧮", layout="wide")

# --- Funkcja tła ---
def dodaj_tlo(nazwa_pliku):
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

# --- Wczytywanie danych ---
@st.cache_data
def wczytaj_dane():
    try:
        df_rodowody = pd.read_excel('rodowody.xlsx')
        df_crv = pd.read_excel('Oferta CRV.xlsx')
        glowna_kolumna_nazwy = 'Bull_name'
        kolumny_przodkow = ['Sire_name', 'Dam_name', 'Maternal_Grand_Sire_name']
        kolumny_do_czyszczenia = [glowna_kolumna_nazwy] + kolumny_przodkow
        for kolumna in kolumny_do_czyszczenia:
            if kolumna in df_rodowody.columns: df_rodowody[kolumna] = df_rodowody[kolumna].astype(str).str.strip()
            if kolumna in df_crv.columns: df_crv[kolumna] = df_crv[kolumna].astype(str).str.strip()
        return df_rodowody, df_crv, glowna_kolumna_nazwy, kolumny_przodkow
    except FileNotFoundError as e:
        st.error(f"BŁĄD: Plik '{e.filename}' nie został znaleziony.")
        return None, None, None, None

df_rodowody, df_crv, glowna_kolumna_nazwy, kolumny_przodkow = wczytaj_dane()

# --- Funkcja sprawdzająca pokrewieństwo ---
def czy_spokrewnione(nazwa_buhaja1, nazwa_buhaja2, df_rodowody_func):
    try:
        wiersz_buhaja1 = df_rodowody_func.loc[df_rodowody_func[glowna_kolumna_nazwy] == nazwa_buhaja1].iloc[0]
        rodzina1 = {nazwa_buhaja1}.union(set(wiersz_buhaja1[kolumny_przodkow].dropna()))
        wiersz_buhaja2 = df_rodowody_func.loc[df_rodowody_func[glowna_kolumna_nazwy] == nazwa_buhaja2].iloc[0]
        rodzina2 = {nazwa_buhaja2}.union(set(wiersz_buhaja2[kolumny_przodkow].dropna()))
        return len(rodzina1.intersection(rodzina2)) > 0
    except IndexError:
        return False

# --- Interfejs kalkulatora ---
dodaj_tlo('tlo_kalkulator.jpg')
st.image('logo.png', width=150)
st.title("🧮 Kalkulator doboru buhajów")

if df_rodowody is not None and df_crv is not None:
    st.markdown("---")
    st.header("Krok 1: Twoje stado")
    lista_buhajow_w_rodowodach = sorted(df_rodowody[glowna_kolumna_nazwy].unique())
    buhaje_w_stadzie = st.multiselect("Wybierz buhaje, których używałeś w swoim stadzie:", lista_buhajow_w_rodowodach)

    st.markdown("---")
    st.header("Krok 2: Kryteria selekcji")

    st.subheader("Rasa:")
    if 'Rasa' in df_crv.columns:
        opcje_ras = df_crv['Rasa'].unique().tolist()
        wybrane_rasy = st.multiselect("Wybierz interesujące Cię rasy (jedną lub obie):", opcje_ras, default=opcje_ras)
    else:
        wybrane_rasy = []
        st.info("Nie znaleziono kolumny 'Rasa' w pliku 'Oferta CRV.xlsx'. Filtr rasy jest niedostępny.")

    st.subheader("Cechy specjalne:")
    czy_tylko_a2a2 = st.checkbox("Szukaj tylko buhajów z genotypem beta-kazeiny A2A2", help="Wymaga kolumny 'Beta_kazeina'")
    czy_kappa_ab_bb = st.checkbox("Szukaj tylko buhajów z genotypem kappa-kazeiny AB lub BB", help="Wymaga kolumny 'Kappa_kazeina'")
    czy_indeks_robotowy = st.checkbox("Szukaj buhajów z wysokim Indeksem Robotowym", help="Filtruje buhaje z 'Wydajnosc_robotowa' >= 98 oraz 'Szybkosc_doju' >= 96")

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
        if not buhaje_w_stadzie:
            st.warning("Musisz wybrać przynajmniej jednego buhaja z Twojego stada.")
        elif 'Rasa' in df_crv.columns and not wybrane_rasy:
            st.warning("Musisz wybrać przynajmniej jedną rasę.")
        else:
            with st.spinner("Przeliczam..."):
                rekomendacje = df_crv.copy()

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

                niespokrewnione_buhaje = []
                for index, buhaj_crv in rekomendacje.iterrows():
                    jest_spokrewniony = any(czy_spokrewnione(buhaj_crv[glowna_kolumna_nazwy], moj_buhaj, df_rodowody) for moj_buhaj in buhaje_w_stadzie)
                    if not jest_spokrewniony:
                        niespokrewnione_buhaje.append(buhaj_crv)
                
                st.header("Wyniki:")
                if not niespokrewnione_buhaje:
                    st.error("Brak buhajów spełniających wszystkie kryteria. Spróbuj poluzować wymagania.")
                else:
                    st.success(f"Znaleziono {len(niespokrewnione_buhaje)} pasujących buhajów:")
                    wyniki_df = pd.DataFrame(niespokrewnione_buhaje)
                    
                    kolumny_do_wyswietlenia = [glowna_kolumna_nazwy]
                    if 'Rasa' in wyniki_df.columns: kolumny_do_wyswietlenia.append('Rasa')
                    if czy_tylko_a2a2 and 'Beta_kazeina' in wyniki_df.columns: kolumny_do_wyswietlenia.append('Beta_kazeina')
                    if czy_kappa_ab_bb and 'Kappa_kazeina' in wyniki_df.columns: kolumny_do_wyswietlenia.append('Kappa_kazeina')
                    if czy_indeks_robotowy and 'Wydajnosc_robotowa' in wyniki_df.columns: kolumny_do_wyswietlenia.append('Wydajnosc_robotowa')
                    if czy_indeks_robotowy and 'Szybkosc_doju' in wyniki_df.columns: kolumny_do_wyswietlenia.append('Szybkosc_doju')
                    kolumny_do_wyswietlenia.extend(list(dict.fromkeys([k['cecha'] for k in kryteria_suwakow])))
                    
                    st.dataframe(wyniki_df[kolumny_do_wyswietlenia], use_container_width=True)