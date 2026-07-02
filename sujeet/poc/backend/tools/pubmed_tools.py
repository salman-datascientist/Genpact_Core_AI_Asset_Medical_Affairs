"""
PubMed Tools  Agent Tool Implementations
==========================================
Tools:
   pubmed_search   search PubMed, return PMIDs
   pubmed_fetch    fetch full metadata for PMIDs
   save_to_db      persist papers to SQLite
"""

import os
import json
import sqlite3
import requests
import xmltodict
from datetime import datetime
from dotenv import load_dotenv

from tools.pubmed_rate_limiter import (
    PubMedRateLimitError,
    eutils_get,
    get_rate_limiter,
)

load_dotenv()

PUBMED_API_KEY = os.getenv("PUBMED_API_KEY", "")
BASE_URL       = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
# DB_PATH is relative — resolved from this file's location → poc/data/pubmed_papers.db
# api_server.py overrides this at runtime to ensure it always points to poc/data/
DB_PATH        = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "pubmed_papers.db"))


def _format_pubmed_error(exc: Exception, context: str) -> str:
    if isinstance(exc, PubMedRateLimitError):
        return (
            f"ERROR {context}: PubMed rate limit hit — {exc}. "
            f"Current limit: {get_rate_limiter().max_requests_per_second:.1f} req/s. "
            "Lower the requests/second setting or wait before retrying."
        )
    if isinstance(exc, requests.HTTPError):
        return f"ERROR {context}: HTTP {exc.response.status_code} from PubMed — {exc}"
    return f"ERROR {context}: {type(exc).__name__}: {exc}"


def _eutils_params(extra: dict | None = None) -> dict:
    params = dict(extra or {})
    if PUBMED_API_KEY:
        params["api_key"] = PUBMED_API_KEY
    return params


#  TOOL: pubmed_search 

def pubmed_search(query: str, max_results: int = 50,
                  label: str = "search", _state=None, **kwargs) -> str:
    """
    Search PubMed. Stores PMIDs in agent state.
    Returns a summary string for the agent to observe.
    """
    params = _eutils_params({
        "db":      "pubmed",
        "term":    query,
        "retmax":  max_results,
        "retmode": "json",
    })
    try:
        resp = eutils_get(f"{BASE_URL}/esearch.fcgi", params, timeout=15)
        resp.raise_for_status()
        data    = resp.json()
        pmids   = data["esearchresult"]["idlist"]
        total   = int(data["esearchresult"]["count"])

        # Store in state for next tool to read
        if _state is not None:
            existing = {p["pmid"] for p in _state.papers_found}
            new_pmids = [p for p in pmids if p not in existing]
            # Store as stub dicts so fetch tool can identify them
            _state.papers_found.extend(
                [{"pmid": p, "_fetched": False, "_label": label} for p in new_pmids]
            )

        return (
            f"[{label}] PubMed returned {total} total matches. "
            f"Queued {len(pmids)} PMIDs for fetching. "
            f"First 5: {pmids[:5]}"
        )
    except Exception as e:
        return _format_pubmed_error(e, "pubmed_search")


#  TOOL: pubmed_fetch 

def pubmed_fetch(_state=None, source: str = "state", **kwargs) -> str:
    """
    Fetch full metadata for all un-fetched PMIDs in agent state.
    Parses XML and updates state.papers_found with rich dicts.
    """
    if _state is None:
        return "ERROR: No agent state provided"

    unfetched = [p for p in _state.papers_found if not p.get("_fetched")]
    if not unfetched:
        return "No new PMIDs to fetch  all papers already retrieved."

    pmids      = [p["pmid"] for p in unfetched]
    batch_size = 50
    fetched    = 0
    errors     = 0
    error_msgs = []  # capture actual error messages

    for i in range(0, len(pmids), batch_size):
        batch = pmids[i: i + batch_size]
        params = _eutils_params({
            "db":      "pubmed",
            "id":      ",".join(batch),
            "retmode": "xml",
            "rettype": "abstract",
        })
        try:
            resp = eutils_get(f"{BASE_URL}/efetch.fcgi", params, timeout=30)
            resp.raise_for_status()
            data     = xmltodict.parse(resp.text)
            articles = data.get("PubmedArticleSet", {}).get("PubmedArticle", [])

            if isinstance(articles, dict):
                articles = [articles]

            parsed_map = {}
            for art in articles:
                p = _parse_article(art)
                if p:
                    parsed_map[p["pmid"]] = p
                    fetched += 1

            # Replace stub dicts with full parsed dicts in state
            for idx, stub in enumerate(_state.papers_found):
                if stub["pmid"] in parsed_map:
                    label = stub.get("_label", "")
                    full  = parsed_map[stub["pmid"]]
                    full["_fetched"] = True
                    full["_label"]   = label
                    _state.papers_found[idx] = full

        except Exception as e:
            errors += 1
            msg = _format_pubmed_error(e, f"pubmed_fetch batch {i // batch_size + 1}")
            error_msgs.append(msg)
            print(f"[pubmed_fetch ERROR] {msg}")  # visible in server terminal

    result = (
        f"Fetched full metadata for {fetched} papers "
        f"({errors} errors). "
        f"State now has {len(_state.papers_found)} papers total."
    )
    if error_msgs:
        result += f" ERRORS: {'; '.join(error_msgs)}"
    return result



def _parse_article(article: dict) -> dict | None:
    """Parse one PubMed XML article dict  flat dict."""
    try:
        medline     = article.get("MedlineCitation", {})
        pubmed_data = article.get("PubmedData", {})
        art         = medline.get("Article", {})

        pmid = str(medline.get("PMID", {}).get("#text", medline.get("PMID", "")))

        # Title
        title = art.get("ArticleTitle", "")
        if isinstance(title, dict):
            title = title.get("#text", str(title))

        # Abstract
        abstract_raw = art.get("Abstract", {}).get("AbstractText", "")
        if isinstance(abstract_raw, list):
            abstract = " ".join(
                f"{a.get('@Label','')}: {a.get('#text', a) if isinstance(a, dict) else a}"
                for a in abstract_raw
            )
        elif isinstance(abstract_raw, dict):
            abstract = abstract_raw.get("#text", str(abstract_raw))
        else:
            abstract = str(abstract_raw)

        # Authors
        author_list = art.get("AuthorList", {}).get("Author", [])
        if isinstance(author_list, dict):
            author_list = [author_list]
        authors = [
            f"{a.get('LastName', '')} {a.get('Initials', '')}".strip()
            for a in author_list if isinstance(a, dict)
        ]

        # Journal & year
        journal_info = art.get("Journal", {})
        journal_name = journal_info.get("Title", "")
        pub_date_raw = journal_info.get("JournalIssue", {}).get("PubDate", {})
        pub_year     = pub_date_raw.get("Year", pub_date_raw.get("MedlineDate", ""))
        if isinstance(pub_year, str) and len(pub_year) > 4:
            pub_year = pub_year[:4]

        # Publication types
        pt_raw = art.get("PublicationTypeList", {}).get("PublicationType", [])
        if isinstance(pt_raw, dict):
            pt_raw = [pt_raw]
        elif isinstance(pt_raw, str):
            pt_raw = [pt_raw]
        pub_types = [
            p.get("#text", str(p)) if isinstance(p, dict) else str(p)
            for p in pt_raw
        ]

        # MeSH terms
        mesh_raw = medline.get("MeshHeadingList", {}).get("MeshHeading", [])
        if isinstance(mesh_raw, dict):
            mesh_raw = [mesh_raw]
        mesh_terms = []
        for m in mesh_raw:
            if not isinstance(m, dict):
                continue
            desc = m.get("DescriptorName", "")
            if isinstance(desc, dict):
                term = desc.get("#text", "")
            else:
                term = str(desc) if desc else ""
            if term:
                mesh_terms.append(term)

        # DOI
        article_ids = pubmed_data.get("ArticleIdList", {}).get("ArticleId", [])
        if isinstance(article_ids, dict):
            article_ids = [article_ids]
        doi = next(
            (a.get("#text", "") for a in article_ids
             if isinstance(a, dict) and a.get("@IdType") == "doi"),
            ""
        )

        # Country
        country = medline.get("MedlineJournalInfo", {}).get("Country", "")

        # Keywords
        kw_list_raw = medline.get("KeywordList", {})
        if isinstance(kw_list_raw, dict):
            kw_raw = kw_list_raw.get("Keyword", [])
            if isinstance(kw_raw, dict):
                kw_raw = [kw_raw]
            keywords = [
                k.get("#text", k) if isinstance(k, dict) else str(k)
                for k in kw_raw
            ]
        else:
            keywords = []

        embed_text = (
            f"Title: {title}\n"
            f"Authors: {', '.join(authors)}\n"
            f"Journal: {journal_name} ({pub_year})\n"
            f"MeSH: {', '.join(mesh_terms[:8])}\n"
            f"Keywords: {', '.join(keywords[:8])}\n"
            f"Abstract: {abstract}"
        ).strip()

        return {
            "pmid":       pmid,
            "title":      title,
            "authors":    authors,
            "journal":    journal_name,
            "pub_year":   pub_year,
            "doi":        doi,
            "country":    country,
            "pub_types":  pub_types,
            "mesh_terms": mesh_terms,
            "keywords":   keywords,
            "abstract":   abstract,
            "embed_text": embed_text,
            "fetched_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return None


#  TOOL: save_to_db 

def save_to_db(_state=None, source: str = "state", **kwargs) -> str:
    """Persist all fetched papers to SQLite."""
    if _state is None:
        return "ERROR: No state"

    papers = [p for p in _state.papers_found if p.get("_fetched")]
    if not papers:
        return "No fetched papers to save."

    # Auto-create data directory if it doesn't exist (e.g. fresh clone from git)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            pmid        TEXT PRIMARY KEY,
            title       TEXT,
            authors     TEXT,
            journal     TEXT,
            pub_year    TEXT,
            doi         TEXT,
            country     TEXT,
            pub_types   TEXT,
            mesh_terms  TEXT,
            keywords    TEXT,
            abstract    TEXT,
            embed_text  TEXT,
            label       TEXT,
            fetched_at  TEXT
        )
    """)

    inserted = 0
    for p in papers:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO papers
                (pmid, title, authors, journal, pub_year, doi, country,
                 pub_types, mesh_terms, keywords, abstract, embed_text,
                 label, fetched_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                p.get("pmid"), p.get("title"),
                json.dumps(p.get("authors", [])),
                p.get("journal"), p.get("pub_year"), p.get("doi"),
                p.get("country"),
                json.dumps(p.get("pub_types", [])),
                json.dumps(p.get("mesh_terms", [])),
                json.dumps(p.get("keywords", [])),
                p.get("abstract"), p.get("embed_text"),
                p.get("_label", ""),
                p.get("fetched_at"),
            ))
            inserted += 1
        except Exception:
            pass

    conn.commit()
    conn.close()
    return f"Saved {inserted} papers to SQLite at {DB_PATH}"
