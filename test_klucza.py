import json
import gcsfs

print("--- OSTATECZNY TEST KLUCZA ---")

# 1. Wklej tutaj DOKŁADNĄ ścieżkę do swojego pliku klucza JSON
sciezka_do_klucza = "/Users/anna/Downloads/noted-wares-474211-g2-e39e145b3780.json"

# 2. Wklej tutaj ścieżkę gs:// do swojego BUCKETU
sciezka_do_bucketu = "gs://dane_kalkulator_inbredowy_anna/"

try:
    print(f"Próbuję otworzyć plik klucza: {sciezka_do_klucza}")
    with open(sciezka_do_klucza, 'r') as f:
        klucz_json = json.load(f)
    print("✅ Plik klucza odczytany poprawnie.")

    print("Próbuję połączyć się z Google Cloud...")
    fs = gcsfs.GCSFileSystem(token=klucz_json)

    print(f"Próbuję wylistować pliki w buckecie: {sciezka_do_bucketu}")
    pliki = fs.ls(sciezka_do_bucketu)
    print("✅ Połączenie z Google Cloud udane!")

    print("\n" + "="*50)
    print("GRATULACJE! Twój plik klucza i uprawnienia działają poprawnie.")
    print("Znaleziono pliki:")
    for p in pliki:
        print(f"- {p}")
    print("="*50)

except Exception as e:
    print("\n" + "!"*50)
    print(f"❌ BŁĄD: {e}")
    print("Jeśli widzisz ten błąd, problem leży w samym pliku klucza JSON lub w fundamentalnych uprawnieniach.")
    print("!"*50)