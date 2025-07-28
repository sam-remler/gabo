"""
Ingestion module for gabo platform
"""

from .base_loader import BaseLoader
from .pdf_loader import PDFLoader
from .email_loader import EmailLoader
from .utils import chunk_text, clean_text, extract_metadata

__all__ = [
    "BaseLoader",
    "PDFLoader", 
    "EmailLoader",
    "chunk_text",
    "clean_text",
    "extract_metadata"
] 