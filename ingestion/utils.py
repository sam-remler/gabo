"""
Utility functions for document processing
"""

import re
import hashlib
from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def chunk_text(text: str, max_chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks
    
    Args:
        text: Input text to chunk
        max_chunk_size: Maximum size of each chunk
        overlap: Number of characters to overlap between chunks
    
    Returns:
        List of text chunks
    """
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings
            sentence_end = text.rfind('.', start, end)
            if sentence_end > start + max_chunk_size * 0.7:  # At least 70% of max size
                end = sentence_end + 1
            else:
                # Look for paragraph breaks
                paragraph_end = text.rfind('\n\n', start, end)
                if paragraph_end > start + max_chunk_size * 0.5:
                    end = paragraph_end + 2
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position with overlap
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks


def clean_text(text: str) -> str:
    """
    Clean and normalize text
    
    Args:
        text: Raw text to clean
    
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove excessive newlines
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Normalize unicode
    text = text.encode('utf-8', errors='ignore').decode('utf-8')
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def extract_metadata(content: Dict[str, Any], chunk: str, chunk_index: int) -> Dict[str, Any]:
    """
    Extract metadata from document content and chunk
    
    Args:
        content: Original document content
        chunk: Text chunk
        chunk_index: Index of the chunk
    
    Returns:
        Dictionary of metadata
    """
    metadata = {
        "chunk_index": chunk_index,
        "chunk_size": len(chunk),
        "word_count": len(chunk.split()),
        "extraction_timestamp": datetime.utcnow().isoformat(),
        "chunk_hash": hashlib.md5(chunk.encode()).hexdigest()
    }
    
    # Add document-level metadata if available
    if "metadata" in content:
        doc_metadata = content["metadata"]
        metadata.update({
            "source_metadata": doc_metadata
        })
    
    # Extract basic text statistics
    metadata.update({
        "avg_word_length": _calculate_avg_word_length(chunk),
        "sentence_count": _count_sentences(chunk),
        "paragraph_count": _count_paragraphs(chunk)
    })
    
    return metadata


def _calculate_avg_word_length(text: str) -> float:
    """Calculate average word length"""
    words = text.split()
    if not words:
        return 0.0
    return sum(len(word) for word in words) / len(words)


def _count_sentences(text: str) -> int:
    """Count sentences in text"""
    # Simple sentence counting - can be improved with NLP
    sentences = re.split(r'[.!?]+', text)
    return len([s for s in sentences if s.strip()])


def _count_paragraphs(text: str) -> int:
    """Count paragraphs in text"""
    paragraphs = text.split('\n\n')
    return len([p for p in paragraphs if p.strip()])


def extract_entities(text: str) -> List[Dict[str, Any]]:
    """
    Extract named entities from text (placeholder for future NLP integration)
    
    Args:
        text: Input text
    
    Returns:
        List of extracted entities
    """
    # TODO: Implement with spaCy or similar NLP library
    entities = []
    
    # Simple pattern matching for common entities
    # Email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    for email in emails:
        entities.append({
            "text": email,
            "type": "EMAIL",
            "start": text.find(email),
            "end": text.find(email) + len(email)
        })
    
    # URLs
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, text)
    for url in urls:
        entities.append({
            "text": url,
            "type": "URL",
            "start": text.find(url),
            "end": text.find(url) + len(url)
        })
    
    return entities


def extract_keywords(text: str, top_k: int = 10) -> List[str]:
    """
    Extract keywords from text (placeholder for future implementation)
    
    Args:
        text: Input text
        top_k: Number of keywords to extract
    
    Returns:
        List of keywords
    """
    # TODO: Implement with TF-IDF, TextRank, or similar
    # For now, return simple word frequency
    words = re.findall(r'\b\w+\b', text.lower())
    word_freq = {}
    
    for word in words:
        if len(word) > 3:  # Filter out short words
            word_freq[word] = word_freq.get(word, 0) + 1
    
    # Sort by frequency and return top_k
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_words[:top_k]]


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity between two text chunks
    
    Args:
        text1: First text chunk
        text2: Second text chunk
    
    Returns:
        Similarity score between 0 and 1
    """
    # Simple Jaccard similarity implementation
    # TODO: Implement more sophisticated similarity metrics
    
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 and not words2:
        return 1.0
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union) 