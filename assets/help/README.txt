COLORIMETRO
Strumento per il campionamento e l’analisi del colore

Versione: 0.4.0
Autore: Carlo Tessaro

============================================================
1. INTRODUZIONE
============================================================

Colorimetro è un’applicazione desktop progettata per il campionamento,
l’analisi e la documentazione delle informazioni cromatiche ricavate
da immagini digitali, con particolare attenzione alla riproducibilità
dei risultati e alla trasparenza metodologica.

Il software è concepito per un uso accademico e di ricerca, in contesti
in cui il colore rappresenta un parametro descrittivo o comparativo
(ad esempio archeologia, studio dei materiali, analisi visiva), e non
come strumento di misura colorimetrica strumentale calibrata.


============================================================
2. PIPELINE COLORIMETRICA
============================================================

Tutte le elaborazioni cromatiche sono effettuate utilizzando una
pipeline fissa ed esplicita, al fine di garantire coerenza interna e
riproducibilità dei risultati.

Definizione della pipeline:

- Spazio colore di input: sRGB
- Conversione: sRGB → XYZ
- Illuminante di riferimento: D65
- Osservatore standard: 2°
- Spazio colore di lavoro: CIELAB (L*, a*, b*)

Non viene applicata alcuna gestione dei profili ICC né adattamento
cromatico. Le immagini di input sono pertanto considerate come
codificate in sRGB standard.


============================================================
3. MODALITÀ DI CAMPIONAMENTO
============================================================

Il campionamento del colore viene eseguito su una regione quadrata
di interesse (ROI), centrata sulla coordinata selezionata
dall’utente.

Sono disponibili tre modalità di campionamento:

1. Exact
   Campionamento del singolo pixel selezionato.

2. Average
   Calcolo della media aritmetica dei valori RGB all’interno della ROI.

3. Weighted
   Calcolo della media RGB ponderata mediante un kernel gaussiano
   bidimensionale, che attribuisce maggiore peso ai pixel centrali
   rispetto a quelli periferici.

La modalità weighted utilizza un kernel deterministico, derivato
dalle dimensioni della ROI. A parità di immagine, coordinate e
parametri, il risultato è completamente riproducibile.


============================================================
4. OMOGENEITÀ LOCALE DEL COLORE (σRGB)
============================================================

Per ogni ROI campionata viene calcolata la deviazione standard dei
valori RGB:

σRGB = (σR, σG, σB)

Questo valore rappresenta un indice quantitativo di omogeneità locale
del colore:

- Valori bassi di σRGB indicano un’area cromaticamente uniforme.
- Valori elevati di σRGB indicano eterogeneità, presenza di texture,
  rumore o discontinuità cromatiche.

In presenza di σRGB elevati, la rappresentatività di un singolo valore
cromatico deve essere valutata con cautela.


============================================================
5. ASSEGNAZIONE MUNSELL
============================================================

Per ogni colore campionato, Colorimetro individua la notazione Munsell
più vicina mediante una ricerca del vicino più prossimo nello spazio
CIELAB, utilizzando un dataset di riferimento (“Munsell Real”).

La procedura consiste in:

- Conversione del colore campionato da RGB a CIELAB.
- Calcolo della differenza cromatica tra il campione e tutte le
  referenze Munsell disponibili.
- Selezione della referenza con differenza cromatica minima.

Sono disponibili due metriche di differenza cromatica:

- CIE76 (ΔE*ab)
- CIEDE2000 (ΔE00)

La notazione Munsell restituita rappresenta pertanto una
approssimazione, non una corrispondenza assoluta.


============================================================
6. MATCH ΔE (QUALITÀ DELL’APPROSSIMAZIONE)
============================================================

Unitamente alla notazione Munsell, il software riporta il valore di
Match ΔE, ovvero la differenza cromatica minima tra il colore
campionato e la referenza Munsell selezionata.

Interpretazione generale:

- Valori bassi di Match ΔE indicano una buona approssimazione.
- Valori elevati di Match ΔE indicano una corrispondenza debole e
  suggeriscono cautela interpretativa.

Il valore di Match ΔE fornisce quindi un indicatore quantitativo
dell’affidabilità dell’assegnazione Munsell.


============================================================
7. RIPRODUCIBILITÀ
============================================================

Tutte le operazioni di campionamento ed elaborazione sono
deterministiche. A parità di:

- immagine di input,
- coordinate di campionamento,
- dimensione dello spot,
- modalità di campionamento,
- metrica di differenza cromatica,
- versione del software,

i risultati ottenuti sono riproducibili.


============================================================
8. LIMITI DEL SOFTWARE
============================================================

Colorimetro non sostituisce strumenti di misura colorimetrica
calibrati. In particolare:

- non viene effettuata calibrazione del colore;
- non viene gestita la catena di acquisizione dell’immagine;
- non viene applicata la gestione dei profili colore ICC.

I risultati devono pertanto essere intesi come descrittivi e
comparativi, non come misure strumentali assolute.


============================================================
9. VERSIONE E CITAZIONE
============================================================

Versione software:
Colorimetro v0.4.0

Citazione consigliata:
Carlo Tessaro, Colorimetro, v0.4.0, strumento per il campionamento
e l’analisi del colore, 2026.


============================================================
10. COPYRIGHT
============================================================

© 2026 Carlo Tessaro
Software ad uso accademico e di ricerca.

Tutti i diritti riservati.