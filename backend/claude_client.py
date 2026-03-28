import anthropic


def _format_sources(papers: list[dict]) -> str:
    lines = []
    for i, p in enumerate(papers, 1):
        authors = ", ".join(p["authors"][:3])
        if len(p["authors"]) > 3:
            authors += " et al."
        lines.append(
            f"{i}. {authors} ({p['year']}). \"{p['title']}\". {p['url']}\n"
            f"   Abstract: {p['abstract'][:500]}"
        )
    return "\n\n".join(lines)


async def generate_project(topic: str, papers: list[dict], api_key: str) -> str:
    """Generate the academic project text in Romanian using Claude."""
    client = anthropic.AsyncAnthropic(api_key=api_key)
    sources_text = _format_sources(papers)

    prompt = f"""Ești un asistent academic expert. Generează un proiect academic complet în limba română pe tema: "{topic}".

Folosește OBLIGATORIU sursele bibliografice de mai jos (cel puțin 4 dintre ele) și citează-le în text folosind formatul (Autor, An).

SURSE DISPONIBILE:
{sources_text}

STRUCTURA PROIECTULUI:
- Prima linie: TITLUL proiectului centrat (tema reformulată ca titlu academic)
- Linie goală
- Introducere — prezintă tema, relevanța și obiectivele (200-300 cuvinte)
- Secțiune cu titlu descriptiv — primul aspect major al temei (350-450 cuvinte)
- Secțiune cu titlu descriptiv — al doilea aspect major (350-450 cuvinte)
- Secțiune cu titlu descriptiv — al treilea aspect major (350-450 cuvinte)
- Concluzii — sintetizează ideile principale (200-250 cuvinte)
- Bibliografie — lista completă a surselor folosite, format academic

LUNGIME TOTALĂ: aproximativ 1800-2200 cuvinte (circa 5 pagini A4 cu spațiere mică).

IMPORTANT:
- Scrie DOAR în limba română
- Folosește un stil academic formal
- Fiecare secțiune trebuie să aibă un TITLU descriptiv relevant pentru conținut, NU numerota secțiunile
- Include citări în text (Autor, An) pentru fiecare sursă folosită
- Bibliografia trebuie să conțină minim 4 surse reale din lista furnizată
- Proiectul trebuie să fie coerent și bine structurat
- NU folosi markdown, scrie text simplu. Titlurile secțiunilor pe linii separate, fără marcaje speciale, fără numerotare.
- Separă secțiunile cu o linie goală."""

    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


async def generate_explanation(topic: str, project_text: str, api_key: str) -> str:
    """Generate a simple explanation document in Romanian."""
    client = anthropic.AsyncAnthropic(api_key=api_key)

    prompt = f"""Ai mai jos textul unui proiect academic pe tema "{topic}".

Scrie un DOCUMENT EXPLICATIV în limba română, în limbaj simplu și accesibil, care:
1. Explică pe scurt despre ce este proiectul
2. Rezumă fiecare secțiune în 2-3 propoziții simple
3. Explică termenii tehnici folosiți
4. Oferă o concluzie simplificată

Textul trebuie să fie ușor de înțeles de un student care vrea să prezinte proiectul verbal.
NU folosi markdown, scrie text simplu. Titlurile pe linii separate.

TEXTUL PROIECTULUI:
{project_text[:6000]}"""

    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text
