import socket
import httpx


def _resolve_with_google_dns(hostname: str) -> str:
    """Resolve hostname using Google DNS (8.8.8.8) as fallback."""
    import subprocess
    result = subprocess.run(
        ["nslookup", hostname, "8.8.8.8"],
        capture_output=True, text=True, timeout=10,
    )
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("Address") and "8.8.8.8" not in line and "#" not in line:
            addr = line.split(":", 1)[-1].strip()
            # Skip IPv6 addresses
            if ":" not in addr:
                return addr
    raise Exception(f"Could not resolve {hostname} via Google DNS")


async def search_papers(topic: str, limit: int = 8) -> list[dict]:
    """Search OpenAlex for papers related to the topic."""
    host = "api.openalex.org"

    # Try to resolve via system DNS first, fallback to Google DNS
    try:
        socket.getaddrinfo(host, 443)
        base_url = f"https://{host}"
    except socket.gaierror:
        ip = _resolve_with_google_dns(host)
        base_url = f"https://{ip}"

    url = f"{base_url}/works"
    params = {
        "search": topic,
        "per_page": limit,
        "select": "title,authorships,publication_year,doi,open_access,abstract_inverted_index",
    }
    headers = {
        "User-Agent": "FEAAEseuGenerator/1.0 (mailto:contact@example.com)",
        "Host": host,
    }

    async with httpx.AsyncClient(timeout=30, verify=False) as client:
        resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    papers = []
    for work in data.get("results", []):
        abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))
        if not abstract:
            continue

        authors = []
        for authorship in (work.get("authorships") or []):
            name = (authorship.get("author") or {}).get("display_name")
            if name:
                authors.append(name)

        doi = work.get("doi") or ""

        papers.append({
            "title": work.get("title", ""),
            "abstract": abstract,
            "authors": authors,
            "year": work.get("publication_year"),
            "url": doi,
        })

    return papers


def _reconstruct_abstract(inverted_index: dict | None) -> str:
    """OpenAlex stores abstracts as inverted indexes — reconstruct to plain text."""
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort()
    return " ".join(w for _, w in word_positions)
