# Obiettivo: capacità di interrogare su una serie di documenti

## Step generali
1. Immaganizzinare conoscenza
1. Fornire estratti rilevanti al LLM
1. Far generare la risposta al LLM

## Immaganizzinare conoscenza
Approcci diversi
- Grafi RDF
- Embeddings

### Grafi RDF
Vantaggi
- Precisione nell'ambito della conoscenza codificata nel grafo

Svantaggi
- la traduzione della query in lingua naturale a SPARQL non è sempre precisa (se si usano parole uguali o simili a delle relazioni presenti ok, altrimenti potrebbe inventarsi delle relazioni e non trovare nulla)
- limitato alla conoscenza codificata nel grafo

### Embeddings
Prevede una serie di step di ingestione dei pdf con segmentazione possibilmente semanticamente rilevante (es. sui paragrafi). 

Vantaggi
- Può spaziare su tutta la conoscenza immagazzinata
- Non serve codificare la conoscenza come per i grafi

Svantaggi
- Maggiore possibilità di allucinazioni
- Risultato dipende da una segmentazione del PDF ben fatta

## Segmentazione file di input
Se si sceglie di rappresentare il testo in embeddings (vettori) è necessario segmentarlo in modi semanticamente rilevanti, idealmente per paragrafi/capitoli.
### Esplorata trasformazione in HTML e segmentazione su HTML.
- Non vengono riportati tag h1 ecc, per cui non è immediata l'individuazione di headers. 
- Sono presenti invece attributi font size, per cui si è usato un algoritmo che li sfrutta per inferire se una porzione di testo è un header o testo normale, in base alle differenze tra testo precedente e corrente.   
  - Non sembra essere molto efficiente, nei deliverable considera il testo prima delle didascalia delle immagini come heading e il testo della didascalia come testo del paragrafo.

### Esplorata segmentazione basica di PDF in pagine
- Da risultati migliori che con HTML
- La segmentazione corretta del pdf resta il problema principale

### Esplorato algoritmo customizzato
- Basato su assunto che gli header abbiano un font size maggiore del testo normale
  - Già per il D3.1 quest'assunto viene meno, gli header hanno la stessa grandezza del paragrafo ma sono in grassetto 
  - Svariate eccezioni, come titoli su più righe o note a pie di pagina

## Memoria
- Per portare avanti una conversazione con memoria di quanto detto vengono fornite informazioni su quanto detto finora con ogni nuovo messaggio al LLM. Si possono fornire
  - tutti i messaggi interi
  - un tot massimo di messaggi interi precedenti
  - un riassunto di tutti i messaggi precedenti
  - una serie di triplette costruite autonomamente dall'LLM rappresentanti la conoscenza dei messaggi precedenti (da capire eventualmente come fornire al contempo la memoria e i contesti recuperati)