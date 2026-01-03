"""
Document chunking service for splitting documents into manageable chunks
"""
import logging
from typing import List, Dict
import re

logger = logging.getLogger(__name__)

class ChunkingService:
    """Service for chunking documents into smaller pieces"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize chunking service
        
        Args:
            chunk_size: Maximum number of characters per chunk
            chunk_overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict[str, any]]:
        """
        Split text into chunks with metadata
        
        Args:
            text: Text to chunk
            metadata: Additional metadata to attach to each chunk
            
        Returns:
            List of chunk dictionaries with 'text' and 'metadata'
        """
        if not text or not text.strip():
            return []
        
        # Clean and normalize text
        text = self._clean_text(text)
        
        # Try to split by paragraphs first (better semantic chunks)
        chunks = self._chunk_by_paragraphs(text)
        
        # If chunks are too large, split further
        final_chunks = []
        for chunk in chunks:
            if len(chunk) <= self.chunk_size:
                final_chunks.append(chunk)
            else:
                # Split large chunks by sentences
                sub_chunks = self._chunk_by_sentences(chunk)
                final_chunks.extend(sub_chunks)
        
        # Add metadata to each chunk
        result = []
        for idx, chunk_text in enumerate(final_chunks):
            chunk_dict = {
                "text": chunk_text.strip(),
                "metadata": metadata or {}
            }
            chunk_dict["metadata"]["chunk_index"] = idx
            result.append(chunk_dict)
        
        avg_length = sum(len(c['text']) for c in result) // len(result) if result else 0
        logger.info(f"Created {len(result)} chunks from text (avg length: {avg_length} chars)")
        return result
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
    
    def _chunk_by_paragraphs(self, text: str) -> List[str]:
        """Split text by paragraphs"""
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If adding this paragraph would exceed chunk size, save current chunk
            if current_chunk and len(current_chunk) + len(para) + 2 > self.chunk_size:
                chunks.append(current_chunk)
                # Start new chunk with overlap
                if self.chunk_overlap > 0 and current_chunk:
                    overlap_text = current_chunk[-self.chunk_overlap:]
                    current_chunk = overlap_text + "\n\n" + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _chunk_by_sentences(self, text: str) -> List[str]:
        """Split text by sentences (fallback for large paragraphs)"""
        # Simple sentence splitting (can be improved with NLTK or spaCy)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if current_chunk and len(current_chunk) + len(sentence) + 1 > self.chunk_size:
                chunks.append(current_chunk)
                # Start new chunk with overlap
                if self.chunk_overlap > 0 and current_chunk:
                    overlap_text = current_chunk[-self.chunk_overlap:]
                    current_chunk = overlap_text + " " + sentence
                else:
                    current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks


