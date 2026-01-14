import pandas as pd
import os
import sys

def zmien_na_parquet():
    print("🚀 START: Skrypt został uruchomiony...")
    
    plik_wejsciowy = 'rodowody.xlsx'
    
    if not os.path.exists(plik_wejsciowy):
        print(f"❌ BŁĄD: Nie widzę pliku '{plik_wejsciowy}' w tym folderze!")
        print(f"Obecne pliki w folderze: {os.listdir('.')}")
        return

    print(f"⏳ Wczytywanie '{plik_wejsciowy}'... (To może zająć parę minut, nie zamykaj okna!)")
    sys.stdout.flush() # Wymusza wyświetlenie napisu natychmiast
    
    try:
        # Wczytywanie
        df = pd.read_excel(plik_wejsciowy, dtype=str)
        print(f"✅ Wczytano danych: {len(df)} wierszy.")
        
        df.columns = df.columns.str.strip()
        
        plik_wyjsciowy = 'rodowody.parquet'
        print(f"🚀 Zapisywanie do formatu Parquet...")
        sys.stdout.flush()
        
        df.to_parquet(plik_wyjsciowy, engine='pyarrow', compression='snappy')
        
        rozmiar = os.path.getsize(plik_wyjsciowy) / (1024 * 1024)
        print(f"✨ GOTOWE! Plik: {plik_wyjsciowy} ({rozmiar:.2f} MB)")
        
    except Exception as e:
        print(f"❌ WYSTĄPIŁ BŁĄD: {e}")

if __name__ == "__main__":
    zmien_na_parquet()