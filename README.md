# Colorimetro

**Colorimetro** è un’applicazione desktop multipiattaforma per il campionamento, l’analisi e la documentazione di informazioni cromatiche a partire da immagini digitali, con particolare attenzione alla **riproducibilità** e alla **trasparenza metodologica**.

- **Piattaforme**: macOS, Windows (esecuzione via Python)
- **GUI**: PySide6 (Qt)
- **Output**: report PDF con immagine, campioni, notazione Munsell e metadati

---

## Funzionalità principali

- Caricamento immagini (PNG/JPG/TIFF/BMP).
- Campionamento del colore in una ROI quadrata (“spot”) centrata sul punto selezionato.
- Modalità di campionamento:
  - **Exact**: singolo pixel
  - **Average**: media aritmetica nella ROI
  - **Weighted**: media ponderata con kernel gaussiano deterministico
- Calcolo dell’**indice di omogeneità locale**: **σRGB** = (σR, σG, σB) sulla ROI.
- Assegnazione della notazione **Munsell** (dataset “Munsell Real”) tramite ricerca del vicino più prossimo in spazio CIELAB.
- Indicazione della qualità dell’approssimazione: **Match ΔE** (CIE76 o CIEDE2000).
- Esportazione **PDF** del report (immagine, overlay campioni, tabella e note).
- Guida interna richiamabile dal programma.

---

## Metodo (sintesi)

Pipeline colorimetrica esplicita e fissa:

- **Input**: sRGB  
- **Conversione**: sRGB → XYZ (D65) → CIELAB (D65/2°, osservatore standard)  
- **Note**: non è implementata gestione profili ICC né calibrazione; le immagini sono assunte come sRGB.

Interpretazione:
- **Match ΔE basso** ⇒ approssimazione Munsell più affidabile.
- **σRGB alto** ⇒ area localmente eterogenea (texture/rumore/bordi), campione potenzialmente poco rappresentativo.

---

## Requisiti

- Python **3.12** consigliato (testato con ambiente virtuale)
- Dipendenze elencate in `requirements.txt`

> Nota: l’applicazione è distribuita come progetto Python (cartella). Non è un eseguibile “standalone”.

---

## Installazione e avvio (utente finale)

### macOS (Terminale)

- Copia la cartella `colorimetro` sul Desktop.
- Esegui:

```
bash
cd ~/Desktop/colorimetro
chmod +x run_mac.command
./run_mac.command
```

Lo script:
	•	crea/usa un ambiente virtuale .venv
	•	installa le dipendenze
	•	avvia src/app.py

### Windows (PowerShell / Prompt)

- Copia la cartella colorimetro sul Desktop.
- Esegui:

```
  cd %USERPROFILE%\Desktop\colorimetro
run_windows.bat

```

---

## Download rapido (Release) da terminale

Gli utenti possono scaricare una specifica versione dalla sezione Releases.

### macOS / Linux (esempio)

```
cd ~/Desktop && \
curl -L -o colorimetro.zip https://github.com/<OWNER>/<REPO>/archive/refs/tags/v0.4.0.zip && \
unzip -q colorimetro.zip && \
mv <REPO>-0.4.0 colorimetro && \
rm colorimetro.zip
```

### Windows PowerShell (esempio)

```
cd $HOME\Desktop
Invoke-WebRequest -Uri https://github.com/<OWNER>/<REPO>/archive/refs/tags/v0.4.0.zip -OutFile colorimetro.zip
Expand-Archive colorimetro.zip .
Rename-Item <REPO>-0.4.0 colorimetro
Remove-Item colorimetro.zip
```

Sostituisci <OWNER> e <REPO> con i valori del repository GitHub.

---

## Struttura del progetto

- src/ – codice applicazione
- gui/ – interfaccia grafica (PySide6)
- core/ – logica (campionamento, pipeline, Munsell, export PDF)
- assets/ – risorse (guida, eventuali icone/loghi)
- tools/ – strumenti di supporto (build dataset, self-check, ecc.)
- requirements.txt – dipendenze Python
- run_mac.command – avvio su macOS
- run_windows.bat – avvio su Windows

⸻

Licenza

Questo software è distribuito sotto Custom Academic License.

Uso consentito per scopi accademici e di ricerca non commerciali.
Redistribuzione, modifica o uso commerciale richiedono permesso esplicito dell’autore.
Vedere il file LICENSE.


⸻

Autore

Carlo Tessaro
© 2026

