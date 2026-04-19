"""
Web scraping tool for MedRAG — fetches real medical information from PubMed
(NCBI E-utilities, free, no API key required).
"""
import re
import time
import ssl
import os
from typing import List, Dict, Any

# SSL fix for corporate environments
os.environ.setdefault("HF_HUB_DISABLE_SSL_VERIFY", "1")
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _get_session() -> requests.Session:
    """Create a requests session with retries and SSL bypass."""
    session = requests.Session()
    session.verify = False
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        "User-Agent": "MedRAG-ClinicalDecisionSupport/1.0 (Research Tool)"
    })
    return session


class WebSearchTool:
    """
    Web scraping tool that fetches clinical information from PubMed
    (NCBI E-utilities — free, no key required).
    """

    PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self._session = None

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = _get_session()
        return self._session

    # ── Public API (used by MedicalRetriever) ─────────────────────────────

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search PubMed and return evidence chunks compatible with the pipeline."""
        if not self.enabled:
            return []
        for attempt in range(2):
            try:
                pmids = self._search_pubmed(query, max_results=max_results)
                if not pmids:
                    return []
                return self._fetch_pubmed_articles(pmids)
            except Exception as e:
                print(f"[WebSearch] Error (attempt {attempt+1}): {e}")
                if attempt == 0:
                    self._session = None
                    time.sleep(0.5)
        return []

    def search_and_scrape(self, query: str, max_results: int = 8) -> Dict[str, Any]:
        """
        Full web-scrape pipeline: search PubMed, fetch abstracts, parse them,
        and return structured results with metadata. Used by the /api/webscrape
        endpoint.
        """
        start = time.time()
        results: List[Dict[str, Any]] = []

        # Retry up to 2 times for transient DNS / network issues
        for attempt in range(2):
            try:
                print(f"[WebSearch] search_and_scrape attempt {attempt+1} for: {query[:60]}", flush=True)
                results = self._scrape_pubmed(query, max_results)
                print(f"[WebSearch] Got {len(results)} results", flush=True)
                if results:
                    break
            except Exception as e:
                print(f"[WebSearch] PubMed scrape error (attempt {attempt+1}): {e}", flush=True)
                if attempt == 0:
                    self._session = None  # reset session and retry
                    time.sleep(0.5)

        elapsed = round(time.time() - start, 2)
        return {
            "query": query,
            "source": "PubMed (NCBI)",
            "results": results,
            "total_found": len(results),
            "scrape_time_seconds": elapsed,
        }

    # ── PubMed E-utilities (free, no key) ─────────────────────────────────

    def _search_pubmed(self, query: str, max_results: int = 8) -> List[str]:
        """Search PubMed and return PMIDs."""
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance",
        }
        print(f"[WebSearch] Searching PubMed: {query[:60]}...", flush=True)
        resp = self.session.get(self.PUBMED_SEARCH_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        pmids = data.get("esearchresult", {}).get("idlist", [])
        print(f"[WebSearch] Got {len(pmids)} PMIDs: {pmids}", flush=True)
        return pmids

    def _fetch_pubmed_articles(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """Fetch article abstracts from PubMed by PMID list."""
        if not pmids:
            return []
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract",
        }
        resp = self.session.get(self.PUBMED_FETCH_URL, params=params, timeout=20)
        resp.raise_for_status()
        return self._parse_pubmed_xml(resp.text)

    def _parse_pubmed_xml(self, xml_text: str) -> List[Dict[str, Any]]:
        """Parse PubMed XML into structured evidence chunks."""
        articles = []
        article_blocks = re.findall(
            r"<PubmedArticle>(.*?)</PubmedArticle>", xml_text, re.DOTALL
        )
        for block in article_blocks:
            try:
                title_m = re.search(r"<ArticleTitle>(.*?)</ArticleTitle>", block, re.DOTALL)
                title = self._strip_tags(title_m.group(1)) if title_m else "Untitled"

                abstract_parts = re.findall(
                    r"<AbstractText[^>]*>(.*?)</AbstractText>", block, re.DOTALL
                )
                abstract = " ".join(self._strip_tags(p) for p in abstract_parts)

                pmid_m = re.search(r"<PMID[^>]*>(\d+)</PMID>", block)
                pmid = pmid_m.group(1) if pmid_m else ""

                journal_m = re.search(r"<Title>(.*?)</Title>", block, re.DOTALL)
                journal = self._strip_tags(journal_m.group(1)) if journal_m else ""

                year_m = re.search(r"<PubDate>.*?<Year>(\d{4})</Year>", block, re.DOTALL)
                year = year_m.group(1) if year_m else ""

                author_names = re.findall(
                    r"<LastName>(.*?)</LastName>\s*<ForeName>(.*?)</ForeName>", block
                )
                authors = [f"{fn} {ln}" for ln, fn in author_names[:3]]
                if len(author_names) > 3:
                    authors.append("et al.")

                mesh_terms = re.findall(
                    r'<DescriptorName[^>]*>(.*?)</DescriptorName>', block
                )

                if abstract:
                    articles.append({
                        "id": f"pubmed_{pmid}",
                        "text": abstract,
                        "document": title,
                        "section": "Abstract",
                        "category": "PubMed",
                        "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        "pmid": pmid,
                        "journal": journal,
                        "year": year,
                        "authors": ", ".join(authors),
                        "mesh_terms": mesh_terms[:5],
                        "relevance_score": 0.5,
                    })
            except Exception:
                continue
        return articles

    def _scrape_pubmed(self, query: str, max_results: int = 8) -> List[Dict[str, Any]]:
        pmids = self._search_pubmed(query, max_results)
        if not pmids:
            return []
        return self._fetch_pubmed_articles(pmids)

    @staticmethod
    def _strip_tags(text: str) -> str:
        return re.sub(r"<[^>]+>", "", text).strip()
