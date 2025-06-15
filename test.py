import pandas as pd

# 📄 CSV-Datei einlesen (Passe den Dateinamen ggf. an)
df = pd.read_csv("tickets.csv")

# 📌 Nur gültige ZIP-Codes behalten und auf 5-stellige Strings formatieren
df = df[df['zip_code'].notna()]  # Entfernt NaN-Werte
df['zip_code'] = df['zip_code'].astype(float).astype(int).astype(str).str.zfill(5)

# 🔍 Einzigartige ZIP-Codes extrahieren und sortieren
unique_zip_codes = sorted(df['zip_code'].unique())

# 📋 Ausgabe
print("Eindeutige ZIP-Codes im Datensatz:")
for zip_code in unique_zip_codes:
    print(zip_code)
