import re
from typing import List, Dict, Any
from .helpers import clean_text, generate_doc_id


class SectionAwareChunker:
    """
    Section-aware chunking that preserves complete medical protocols.
    Unlike naive chunking, this keeps dosing + conditions together.
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.section_markers = [
            r'^#{1,4}\s+',
            r'^(?:Section|Chapter|Part)\s+\d+',
            r'^(?:DIAGNOSIS|TREATMENT|MANAGEMENT|MONITORING|CONTRAINDICATIONS|DOSING|EMERGENCY|PROTOCOL|GUIDELINES)',
            r'^\d+\.\s+[A-Z]',
            r'^[A-Z][A-Z\s]{5,}:?\s*$',
        ]

    def chunk_document(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunk a clinical document while preserving sections."""
        chunks = []
        title = document.get("title", "Unknown Document")
        category = document.get("category", "General")

        if "sections" in document:
            for section in document["sections"]:
                section_chunks = self._chunk_section(
                    section.get("content", ""),
                    section_heading=section.get("heading", ""),
                    doc_title=title,
                    category=category,
                    metadata=document.get("metadata", {})
                )
                chunks.extend(section_chunks)
        elif "content" in document:
            chunks = self._chunk_text(
                document["content"],
                doc_title=title,
                category=category,
                metadata=document.get("metadata", {})
            )

        return chunks

    def _chunk_section(self, content: str, section_heading: str = "",
                       doc_title: str = "", category: str = "",
                       metadata: Dict = None) -> List[Dict[str, Any]]:
        """Chunk a section while preserving subsections."""
        if not content.strip():
            return []

        subsections = self._split_into_subsections(content)

        chunks = []
        for subsection in subsections:
            sub_chunks = self._chunk_text(
                subsection,
                section_heading=section_heading,
                doc_title=doc_title,
                category=category,
                metadata=metadata or {}
            )
            chunks.extend(sub_chunks)

        return chunks

    def _split_into_subsections(self, text: str) -> List[str]:
        """Split text into subsections based on section markers."""
        lines = text.split('\n')
        subsections = []
        current = []

        for line in lines:
            is_header = any(re.match(p, line.strip(), re.IGNORECASE) for p in self.section_markers)
            if is_header and current:
                subsections.append('\n'.join(current))
                current = [line]
            else:
                current.append(line)

        if current:
            subsections.append('\n'.join(current))

        return subsections if subsections else [text]

    def _chunk_text(self, text: str, section_heading: str = "",
                    doc_title: str = "", category: str = "",
                    metadata: Dict = None) -> List[Dict[str, Any]]:
        """Chunk text with overlap, preserving sentence boundaries."""
        text = clean_text(text)
        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [self._create_chunk(text, section_heading, doc_title, category, metadata or {})]

        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_len = len(sentence)

            if current_length + sentence_len > self.chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append(self._create_chunk(
                    chunk_text, section_heading, doc_title, category, metadata or {}
                ))

                overlap_text = ''
                overlap_sentences = []
                for s in reversed(current_chunk):
                    if len(overlap_text) + len(s) <= self.chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_text = ' '.join(overlap_sentences)
                    else:
                        break

                current_chunk = overlap_sentences + [sentence]
                current_length = sum(len(s) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_length += sentence_len

        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(self._create_chunk(
                chunk_text, section_heading, doc_title, category, metadata or {}
            ))

        return chunks

    def _create_chunk(self, text: str, section_heading: str,
                      doc_title: str, category: str,
                      metadata: Dict) -> Dict[str, Any]:
        """Create a chunk with metadata."""
        has_numbers = bool(re.search(r'\d+\.?\d*\s*(?:mg|mcg|g|kg|ml|mmol|mmHg|%|bpm)', text, re.IGNORECASE))

        return {
            "id": generate_doc_id(text),
            "text": text,
            "section": section_heading,
            "document": doc_title,
            "category": category,
            "has_numeric_data": has_numbers,
            "metadata": metadata,
            "char_length": len(text)
        }

    def chunk_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Chunk multiple documents."""
        all_chunks = []
        for doc in documents:
            chunks = self.chunk_document(doc)
            all_chunks.extend(chunks)
        return all_chunks
