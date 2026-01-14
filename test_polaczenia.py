import streamlit as st
import gcsfs

st.title("Test połączenia z Google Cloud")

try:
    st.info("1. Próba odczytania uproszczonych sekretów...")
    # Budujemy "klucz" na podstawie uproszczonego pliku secrets.toml
    creds = {
        "type": "service_account",
        "project_id": st.secrets["project_id"],
        "private_key_id": "", # To pole nie jest krytyczne dla tego typu autentykacji
        "private_key": st.secrets["private_key"],
        "client_email": st.secrets["client_email"],
        "client_id": "", # To pole nie jest krytyczne
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "" # To pole nie jest krytyczne
    }
    st.success("   ...sekrety odczytane poprawnie.")

    st.info("2. Próba połączenia z Google Cloud Storage...")
    fs = gcsfs.GCSFileSystem(token=creds)
    st.success("   ...połączenie udane.")

    # Wklej tutaj tylko nazwę swojego bucketu!
    sciezka_do_bucketu = "gs://dane_kalkulator_inbredowy_anna/" 
    st.info(f"3. Próba wylistowania plików w buckecie: {sciezka_do_bucketu}")
    files = fs.ls(sciezka_do_bucketu)
    st.success("   ...pliki wylistowane.")

    st.balloons()
    st.header("✅ SUKCES! Połączenie działa. Twój plik secrets.toml jest poprawny.")
    st.write("Znalezione pliki:")
    st.dataframe(files)

except Exception as e:
    st.error(f"❌ BŁĄD: {e}")
    st.warning("Problem na 100% leży w pliku .streamlit/secrets.toml. Upewnij się, że wartości private_key, client_email i project_id są poprawnie skopiowane z Twojego oryginalnego pliku JSON.")