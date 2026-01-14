import json
import os

print("--- Generator pliku secrets.toml ---")

# Krok 1: Zapytaj o ścieżkę do pliku klucza
key_file_path = input("Wklej tutaj ścieżkę do swojego pliku klucza JSON i naciśnij Enter: ")
key_file_path = key_file_path.strip().strip("'\"") # Czyszczenie ścieżki

if not os.path.exists(key_file_path):
    print("\nBŁĄD: Nie znaleziono pliku pod tą ścieżką. Spróbuj ponownie.")
else:
    # Krok 2: Odczytaj plik JSON
    with open(key_file_path, 'r') as f:
        creds_json = json.load(f)

    # Krok 3: Wygeneruj idealnie sformatowany tekst TOML
    toml_content = f'''
[gcp_creds]
type = "{creds_json.get("type", "")}"
project_id = "{creds_json.get("project_id", "")}"
private_key_id = "{creds_json.get("private_key_id", "")}"
private_key = """{creds_json.get("private_key", "")}"""
client_email = "{creds_json.get("client_email", "")}"
client_id = "{creds_json.get("client_id", "")}"
auth_uri = "{creds_json.get("auth_uri", "")}"
token_uri = "{creds_json.get("token_uri", "")}"
auth_provider_x509_cert_url = "{creds_json.get("auth_provider_x509_cert_url", "")}"
client_x509_cert_url = "{creds_json.get("client_x509_cert_url", "")}"
'''

    # Krok 4: Wyświetl wynik do skopiowania
    print("\n" + "="*50)
    print("SKOPIUJ CAŁY PONIŻSZY TEKST (od [gcp_creds] do końca)")
    print("="*50)
    print(toml_content.strip())
    print("="*50)
    print("\n...i wklej go do pliku .streamlit/secrets.toml")