"""
Peptide AI - Document Chunker

Splits documents into chunks optimized for retrieval.
Uses semantic-aware chunking that respects section boundaries.
"""

import re
import logging
from typing import List, Optional
from uuid import uuid4
import hashlib

from models.documents import RawDocument, ProcessedChunk, SourceType, FDAStatus

logger = logging.getLogger(__name__)


class PeptideChunker:
    """
    Chunks documents for vector storage

    Strategy:
    - Target chunk size: 512 tokens (~2000 chars)
    - Overlap: 50 tokens for context continuity
    - Section-aware: respects abstract/methods/results boundaries
    - Paragraph-aware: doesn't split mid-sentence
    """

    def __init__(
        self,
        target_size: int = 2000,  # characters
        overlap: int = 200,
        min_size: int = 100
    ):
        self.target_size = target_size
        self.overlap = overlap
        self.min_size = min_size

    def chunk_document(self, doc: RawDocument) -> List[ProcessedChunk]:
        """
        Split a document into chunks

        Returns list of ProcessedChunk objects ready for enrichment.
        """
        content = doc.content.strip()

        if not content:
            return []

        # Detect if content has section markers
        sections = self._detect_sections(content)

        if sections:
            # Chunk each section separately
            chunks = []
            for section_type, section_content in sections:
                section_chunks = self._chunk_text(
                    text=section_content,
                    doc=doc,
                    section_type=section_type
                )
                chunks.extend(section_chunks)
        else:
            # Chunk as single unit
            chunks = self._chunk_text(text=content, doc=doc, section_type=None)

        return chunks

    def _detect_sections(self, content: str) -> List[tuple]:
        """
        Detect section boundaries in content

        Returns list of (section_type, section_content) tuples
        """
        sections = []

        # Common section patterns in research papers
        section_patterns = [
            (r"(?:^|\n)(?:ABSTRACT|Abstract)[:\s]*\n?", "abstract"),
            (r"(?:^|\n)(?:BACKGROUND|Background)[:\s]*\n?", "background"),
            (r"(?:^|\n)(?:INTRODUCTION|Introduction)[:\s]*\n?", "introduction"),
            (r"(?:^|\n)(?:METHODS?|Methods?|MATERIALS? AND METHODS?)[:\s]*\n?", "methods"),
            (r"(?:^|\n)(?:RESULTS?|Results?)[:\s]*\n?", "results"),
            (r"(?:^|\n)(?:DISCUSSION|Discussion)[:\s]*\n?", "discussion"),
            (r"(?:^|\n)(?:CONCLUSION|Conclusion|CONCLUSIONS|Conclusions)[:\s]*\n?", "conclusion"),
        ]

        # Find all section markers and their positions
        markers = []
        for pattern, section_type in section_patterns:
            for match in re.finditer(pattern, content):
                markers.append((match.start(), match.end(), section_type))

        if not markers:
            return []

        # Sort by position
        markers.sort(key=lambda x: x[0])

        # Extract sections
        for i, (start, end, section_type) in enumerate(markers):
            # Section content goes from end of marker to start of next marker (or end)
            if i + 1 < len(markers):
                section_content = content[end:markers[i + 1][0]]
            else:
                section_content = content[end:]

            section_content = section_content.strip()
            if section_content:
                sections.append((section_type, section_content))

        return sections

    def _chunk_text(
        self,
        text: str,
        doc: RawDocument,
        section_type: Optional[str]
    ) -> List[ProcessedChunk]:
        """
        Chunk a piece of text into overlapping segments
        """
        chunks = []

        # Split into paragraphs first
        paragraphs = self._split_paragraphs(text)

        current_chunk = ""
        current_start = 0

        for para in paragraphs:
            # If adding this paragraph exceeds target, save current and start new
            if len(current_chunk) + len(para) > self.target_size and current_chunk:
                chunk = self._create_chunk(
                    content=current_chunk.strip(),
                    doc=doc,
                    section_type=section_type,
                    chunk_index=len(chunks)
                )
                if chunk:
                    chunks.append(chunk)

                # Start new chunk with overlap from previous
                overlap_text = self._get_overlap(current_chunk)
                current_chunk = overlap_text + para
            else:
                current_chunk += para

        # Don't forget the last chunk
        if current_chunk.strip():
            chunk = self._create_chunk(
                content=current_chunk.strip(),
                doc=doc,
                section_type=section_type,
                chunk_index=len(chunks)
            )
            if chunk:
                chunks.append(chunk)

        return chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs, preserving paragraph breaks"""
        # Split on double newlines or single newlines followed by indent
        paragraphs = re.split(r'\n\s*\n', text)

        result = []
        for p in paragraphs:
            p = p.strip()
            if p:
                result.append(p + "\n\n")

        return result

    def _get_overlap(self, text: str) -> str:
        """Get the last N characters for overlap"""
        if len(text) <= self.overlap:
            return text

        # Try to break at sentence boundary
        overlap_text = text[-self.overlap:]

        # Find last sentence end in overlap
        sentence_ends = [
            overlap_text.rfind(". "),
            overlap_text.rfind("? "),
            overlap_text.rfind("! "),
        ]
        best_end = max(sentence_ends)

        if best_end > 0:
            return overlap_text[best_end + 2:]

        return overlap_text

    def _create_chunk(
        self,
        content: str,
        doc: RawDocument,
        section_type: Optional[str],
        chunk_index: int
    ) -> Optional[ProcessedChunk]:
        """Create a ProcessedChunk from content"""
        if len(content) < self.min_size:
            return None

        # Generate unique chunk ID
        chunk_id = self._generate_chunk_id(doc.source_id, chunk_index, content)

        return ProcessedChunk(
            chunk_id=chunk_id,
            document_id=doc.source_id,
            source_type=doc.source_type,
            content=content,
            section_type=section_type,
            title=doc.title,
            authors=doc.authors,
            publication_date=doc.publication_date,
            url=doc.url,
            doi=doc.doi,
            citation=doc.citation or "",
            original_language="en",
            # These will be filled by enricher
            peptides_mentioned=[],
            fda_status=FDAStatus.UNKNOWN,
            conditions_mentioned=[]
        )

    def _generate_chunk_id(self, doc_id: str, index: int, content: str) -> str:
        """Generate unique, deterministic chunk ID"""
        # Hash the content for uniqueness
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{doc_id}_chunk_{index}_{content_hash}"


class SimpleChunker:
    """
    Simple fixed-size chunker for quick testing

    Less sophisticated but faster for initial data loading.
    """

    def __init__(self, chunk_size: int = 1500, overlap: int = 150):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_document(self, doc: RawDocument) -> List[ProcessedChunk]:
        """Chunk document with simple fixed-size windows"""
        content = doc.content.strip()
        if not content:
            return []

        chunks = []
        start = 0

        while start < len(content):
            end = start + self.chunk_size

            # Try to break at sentence boundary
            if end < len(content):
                # Look for sentence end near the boundary
                search_start = max(start + self.chunk_size - 100, start)
                search_end = min(start + self.chunk_size + 100, len(content))
                search_text = content[search_start:search_end]

                # Find best break point
                for delim in [". ", ".\n", "? ", "! "]:
                    pos = search_text.rfind(delim)
                    if pos > 0:
                        end = search_start + pos + len(delim)
                        break

            chunk_content = content[start:end].strip()

            if len(chunk_content) >= 50:  # Minimum chunk size
                chunk_id = f"{doc.source_id}_c{len(chunks)}"
                chunks.append(ProcessedChunk(
                    chunk_id=chunk_id,
                    document_id=doc.source_id,
                    source_type=doc.source_type,
                    content=chunk_content,
                    title=doc.title,
                    authors=doc.authors,
                    publication_date=doc.publication_date,
                    url=doc.url,
                    doi=doc.doi,
                    citation=doc.citation or "",
                    peptides_mentioned=[],
                    fda_status=FDAStatus.UNKNOWN,
                    conditions_mentioned=[]
                ))

            start = end - self.overlap

        return chunks
