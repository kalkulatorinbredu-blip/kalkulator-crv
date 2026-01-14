import streamlit as st
import base64

# --- Konfiguracja strony ---
st.set_page_config(
    page_title="Kalkulator Inbredu CRV",
    page_icon="🐮",
    layout="wide"
)

# --- Funkcja do wstawienia tła z półprzezroczystą nakładką ---
# ZMIANA: Zamiast gradientu, nakładamy białą, półprzezroczystą warstwę na cały obraz,
# co sprawia, że jest on widoczny w całości, a napisy są czytelne.
def dodaj_tlo(nazwa_pliku):
    with open(nazwa_pliku, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: linear-gradient(rgba(255,255,255,0.8), rgba(255,255,255,0.8)), url(data:image/{"jpg"};base64,{encoded_string});
        background-size: cover;
    }}
    header {{
        background-color: transparent !important;
    }}
    </style>
    """,
    unsafe_allow_html=True
    )

# --- Rysowanie strony ---
dodaj_tlo('tlo.jpg')

# ZMIANA: Logo jest teraz na górze, w lewej kolumnie, co daje efekt lewego górnego rogu.
# Jest też znacznie większe.
lewa_kol, prawa_kol = st.columns([1, 2]) # Dzielimy stronę na dwie kolumny
with lewa_kol:
    st.image('logo.png', width=300)

# Reszta treści jest w drugiej kolumnie lub pod spodem, dla lepszego układu
st.write("") # Dystans
st.write("")

# ZMIANA: Wyśrodkowany tytuł i podtytuł
st.markdown("<h1 style='text-align: center;'>Kalkulator Inbredu CRV</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #333;'>Inteligentne narzędzie wspierające decyzje hodowlane</h3>", unsafe_allow_html=True)

st.write("")
st.write("")

# ZMIANA: Przycisk używa teraz koloru "primary", który zdefiniowaliśmy w pliku config.toml
# Jest wyśrodkowany za pomocą kolumn
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("Wypróbuj", type="primary", use_container_width=True):
        st.switch_page("pages/2_Kalkulator.py")

st.sidebar.info("Witaj! Kliknij w przycisk 'Wypróbuj' lub wybierz stronę z menu, aby rozpocząć.")