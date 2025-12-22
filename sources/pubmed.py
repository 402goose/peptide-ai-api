"""
Peptide AI - PubMed Adapter

Fetches research papers from PubMed/NCBI using the Entrez API.
"""

import asyncio
import logging
from typing import AsyncGenerator, List, Optional
from datetime import datetime
from xml.etree import ElementTree as ET
import httpx

from models.documents import RawDocument, SourceType
from sources.base import BaseAdapter

logger = logging.getLogger(__name__)

# NCBI Entrez API endpoints
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


class PubMedAdapter(BaseAdapter):
    """
    Adapter for fetching research papers from PubMed

    Uses NCBI's Entrez API with proper rate limiting.
    Without an API key: 3 requests/second
    With an API key: 10 requests/second

    Get an API key at: https://www.ncbi.nlm.nih.gov/account/settings/
    """

    source_type = SourceType.PUBMED

    # Common peptide search terms for ingestion
    PEPTIDE_QUERIES = [
        "BPC-157",
        "TB-500 OR Thymosin Beta-4",
        "Semaglutide",
        "Tirzepatide",
        "GHK-Cu",
        "Ipamorelin",
        "CJC-1295",
        "GHRP-6",
        "GHRP-2",
        "Melanotan",
        "PT-141 OR Bremelanotide",
        "Epitalon",
        "Semax",
        "Selank",
        "Dihexa",
        "BPC-157 healing",
        "peptide therapy",
        "therapeutic peptides",
        "peptide wound healing",
        "peptide muscle growth",
        "peptide neuroprotection",
    ]

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.api_key = self.config.get("api_key", "")
        self.email = self.config.get("email", "peptide-ai@example.com")
        self.tool_name = self.config.get("tool", "peptide-ai")

        # Rate limit: 3/sec without key, 10/sec with key
        self.rate_limit = 10 if self.api_key else 3
        self._last_request = 0

    async def _rate_limit_wait(self):
        """Ensure we don't exceed rate limits"""
        now = asyncio.get_event_loop().time()
        min_interval = 1.0 / self.rate_limit
        elapsed = now - self._last_request

        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)

        self._last_request = asyncio.get_event_loop().time()

    def _build_params(self, extra_params: dict) -> dict:
        """Build request parameters with auth"""
        params = {
            "tool": self.tool_name,
            "email": self.email,
        }
        if self.api_key:
            params["api_key"] = self.api_key

        params.update(extra_params)
        return params

    async def search(
        self,
        query: str,
        max_results: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[RawDocument]:
        """
        Search PubMed for papers matching the query

        Args:
            query: PubMed search query (supports boolean operators)
            max_results: Maximum results to return (up to 10000)
            start_date: Filter papers published after this date
            end_date: Filter papers published before this date

        Returns:
            List of RawDocument objects with paper data
        """
        # Build date range filter
        date_filter = ""
        if start_date or end_date:
            start = start_date.strftime("%Y/%m/%d") if start_date else "1900/01/01"
            end = end_date.strftime("%Y/%m/%d") if end_date else "3000/01/01"
            date_filter = f" AND ({start}:{end}[dp])"

        full_query = f"{query}{date_filter}"

        # Get PMIDs
        pmids = await self._search_pmids(full_query, max_results)

        if not pmids:
            return []

        # Fetch full records
        documents = await self._fetch_records(pmids)
        return documents

    async def _search_pmids(self, query: str, max_results: int) -> List[str]:
        """Search for PMIDs matching query"""
        await self._rate_limit_wait()

        params = self._build_params({
            "db": "pubmed",
            "term": query,
            "retmax": min(max_results, 10000),
            "retmode": "json",
            "sort": "relevance",
        })

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(ESEARCH_URL, params=params)
                response.raise_for_status()
                data = response.json()

                result = data.get("esearchresult", {})
                pmids = result.get("idlist", [])

                logger.info(f"Found {len(pmids)} papers for query: {query[:50]}...")
                return pmids

            except Exception as e:
                logger.error(f"PubMed search failed: {e}")
                return []

    async def _fetch_records(self, pmids: List[str]) -> List[RawDocument]:
        """Fetch full records for a list of PMIDs"""
        if not pmids:
            return []

        documents = []

        # Fetch in batches of 200 (NCBI limit)
        batch_size = 200
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i + batch_size]
            await self._rate_limit_wait()

            params = self._build_params({
                "db": "pubmed",
                "id": ",".join(batch),
                "rettype": "xml",
                "retmode": "xml",
            })

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                try:
                    response = await client.get(EFETCH_URL, params=params)
                    response.raise_for_status()

                    # Parse XML
                    docs = self._parse_pubmed_xml(response.text)
                    documents.extend(docs)

                except Exception as e:
                    logger.error(f"PubMed fetch failed for batch: {e}")
                    continue

        return documents

    def _parse_pubmed_xml(self, xml_text: str) -> List[RawDocument]:
        """Parse PubMed XML response into RawDocument objects"""
        documents = []

        try:
            root = ET.fromstring(xml_text)

            for article in root.findall(".//PubmedArticle"):
                doc = self._parse_article(article)
                if doc:
                    documents.append(doc)

        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")

        return documents

    def _parse_article(self, article: ET.Element) -> Optional[RawDocument]:
        """Parse a single PubMed article XML element"""
        try:
            medline = article.find(".//MedlineCitation")
            if medline is None:
                return None

            pmid_elem = medline.find(".//PMID")
            pmid = pmid_elem.text if pmid_elem is not None else None
            if not pmid:
                return None

            article_elem = medline.find(".//Article")
            if article_elem is None:
                return None

            # Title
            title_elem = article_elem.find(".//ArticleTitle")
            title = self._get_text(title_elem) or "Untitled"

            # Abstract
            abstract_parts = []
            abstract_elem = article_elem.find(".//Abstract")
            if abstract_elem is not None:
                for text_elem in abstract_elem.findall(".//AbstractText"):
                    label = text_elem.get("Label", "")
                    text = self._get_text(text_elem) or ""
                    if label:
                        abstract_parts.append(f"{label}: {text}")
                    else:
                        abstract_parts.append(text)

            abstract = "\n\n".join(abstract_parts)

            # Authors
            authors = []
            author_list = article_elem.find(".//AuthorList")
            if author_list is not None:
                for author in author_list.findall(".//Author"):
                    last_name = self._get_text(author.find("LastName")) or ""
                    first_name = self._get_text(author.find("ForeName")) or ""
                    if last_name:
                        authors.append(f"{first_name} {last_name}".strip())

            # Publication date
            pub_date = None
            pub_date_elem = article_elem.find(".//PubDate")
            if pub_date_elem is not None:
                year = self._get_text(pub_date_elem.find("Year"))
                month = self._get_text(pub_date_elem.find("Month")) or "01"
                day = self._get_text(pub_date_elem.find("Day")) or "01"

                if year:
                    # Convert month name to number if needed
                    month_map = {
                        "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
                        "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
                        "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
                    }
                    if month in month_map:
                        month = month_map[month]

                    try:
                        pub_date = datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d")
                    except ValueError:
                        try:
                            pub_date = datetime.strptime(f"{year}-01-01", "%Y-%m-%d")
                        except ValueError:
                            pass

            # DOI
            doi = None
            for id_elem in article_elem.findall(".//ArticleId"):
                if id_elem.get("IdType") == "doi":
                    doi = id_elem.text

            # Also check ELocationID
            if not doi:
                for eloc in article_elem.findall(".//ELocationID"):
                    if eloc.get("EIdType") == "doi":
                        doi = eloc.text

            # Journal info
            journal_elem = article_elem.find(".//Journal")
            journal_title = ""
            if journal_elem is not None:
                journal_title = self._get_text(journal_elem.find(".//Title")) or ""

            # MeSH terms (for metadata)
            mesh_terms = []
            mesh_list = medline.find(".//MeshHeadingList")
            if mesh_list is not None:
                for heading in mesh_list.findall(".//MeshHeading"):
                    desc = heading.find(".//DescriptorName")
                    if desc is not None:
                        mesh_terms.append(desc.text)

            # Keywords
            keywords = []
            keyword_list = medline.find(".//KeywordList")
            if keyword_list is not None:
                for kw in keyword_list.findall(".//Keyword"):
                    if kw.text:
                        keywords.append(kw.text)

            # Build citation
            citation = self._build_citation({
                "authors": authors,
                "title": title,
                "publication_date": pub_date,
                "journal": journal_title,
            })

            return RawDocument(
                source_id=pmid,
                source_type=SourceType.PUBMED,
                title=title,
                content=abstract,
                authors=authors,
                publication_date=pub_date,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                doi=doi,
                citation=citation,
                raw_metadata={
                    "pmid": pmid,
                    "journal": journal_title,
                    "mesh_terms": mesh_terms,
                    "keywords": keywords,
                }
            )

        except Exception as e:
            logger.error(f"Error parsing article: {e}")
            return None

    def _get_text(self, elem: Optional[ET.Element]) -> Optional[str]:
        """Safely get text from an XML element, handling nested elements"""
        if elem is None:
            return None

        # Get all text including from child elements
        text_parts = []
        if elem.text:
            text_parts.append(elem.text)

        for child in elem:
            if child.text:
                text_parts.append(child.text)
            if child.tail:
                text_parts.append(child.tail)

        return "".join(text_parts).strip() if text_parts else None

    def _build_citation(self, doc: dict) -> str:
        """Build a proper citation string for a PubMed article"""
        authors = doc.get("authors", [])
        title = doc.get("title", "")
        pub_date = doc.get("publication_date")
        journal = doc.get("journal", "")

        year = pub_date.year if pub_date else "n.d."

        if authors:
            if len(authors) == 1:
                author_str = authors[0]
            elif len(authors) == 2:
                author_str = f"{authors[0]} & {authors[1]}"
            else:
                author_str = f"{authors[0]} et al."
        else:
            author_str = "Unknown"

        parts = [author_str, f"({year})", title]
        if journal:
            parts.append(journal)

        return ". ".join(parts) + "."

    async def fetch(self, source_id: str) -> Optional[RawDocument]:
        """Fetch a specific paper by PMID"""
        docs = await self._fetch_records([source_id])
        return docs[0] if docs else None

    async def stream(
        self,
        query: str,
        batch_size: int = 100,
        start_date: Optional[datetime] = None
    ) -> AsyncGenerator[List[RawDocument], None]:
        """
        Stream papers for bulk ingestion

        Yields batches of papers for processing.
        """
        # Get all PMIDs first
        pmids = await self._search_pmids(
            query + (f" AND ({start_date.strftime('%Y/%m/%d')}:3000/01/01[dp])" if start_date else ""),
            max_results=10000
        )

        logger.info(f"Streaming {len(pmids)} papers for query: {query}")

        # Yield in batches
        for i in range(0, len(pmids), batch_size):
            batch_pmids = pmids[i:i + batch_size]
            documents = await self._fetch_records(batch_pmids)

            if documents:
                yield documents

            logger.info(f"Streamed batch {i // batch_size + 1}, {len(documents)} documents")

    async def ingest_peptide_corpus(
        self,
        max_per_query: int = 500
    ) -> AsyncGenerator[List[RawDocument], None]:
        """
        Ingest the full peptide research corpus

        Searches all common peptide terms and yields batches.
        """
        seen_pmids = set()

        for query in self.PEPTIDE_QUERIES:
            logger.info(f"Ingesting: {query}")

            async for batch in self.stream(query, batch_size=100):
                # Deduplicate
                unique_docs = []
                for doc in batch:
                    if doc.source_id not in seen_pmids:
                        seen_pmids.add(doc.source_id)
                        unique_docs.append(doc)

                if unique_docs:
                    yield unique_docs

            # Brief pause between queries
            await asyncio.sleep(0.5)

        logger.info(f"Ingestion complete. Total unique papers: {len(seen_pmids)}")
