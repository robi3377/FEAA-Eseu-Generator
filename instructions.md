## Spec pentru Claude Code

### Stack
- **Backend:** FastAPI + Claude API + `python-docx` + `WeasyPrint` + `httpx` (Semantic Scholar)
- **Frontend:** Next.js (dark mode)
- **Auth:** HTTP Basic Auth simplu prin Nginx sau middleware FastAPI

### Pagina principală
- Sus: prompt pre-făcut afișat într-un box stilizat (copy-paste friendly), ex:
  > *"Generează-mi 10 topicuri pentru un proiect academic de scriere în română, domeniul [X], nivel universitar."*
- Jos: input topic + buton "Generează proiect"
- Progress indicator în timp ce rulează pipeline-ul

### Pipeline backend (`POST /generate`)
1. Caută articole pe **Semantic Scholar API** după topic → minim 4, ideal 6–8
2. Extrage abstractele (+ conținut PDF dacă e open-access)
3. Trimite la **Claude API** cu prompt structurat → generează proiectul în română:
   - Introducere
   - 5-6 secțiuni de conținut
   - Concluzii  
   - Bibliografie (minim 4 surse reale din pasul 1)
4. Al doilea apel Claude → generează **documentul explicativ** în limbaj simplu
5. Inlocuieste toate literele "a" cu "а" in fisierul word si pdf al proiectului, in pdf explicativ nu e nevoie.
6. Generează `.docx` + `.pdf` proiect + `.pdf` explicativ
7. Returnează cele 3 fișiere pentru download

### Output
- `proiect.docx`
- `proiect.pdf`
- `explicatie_topic.pdf`

### ENV
- Create the .env file and put in it all the keys the project needs so I can feel in after it is done