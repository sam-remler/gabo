"""
PDF document loader using PyMuPDF
"""

import asyncio
from typing import Dict, Any, List
from pathlib import Path
import fitz  # PyMuPDF
import logging

from .base_loader import BaseLoader

logger = logging.getLogger(__name__)


class PDFLoader(BaseLoader):
    """PDF document loader using PyMuPDF"""
    
    def __init__(self):
        super().__init__()
        self.supported_extensions = ['.pdf']
        self.max_chunk_size = 1000
        self.chunk_overlap = 200
    
    async def load_document(self, file_path: str) -> Dict[str, Any]:
        """Load PDF document content and metadata"""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, self._load_pdf_sync, file_path)
            return content
        except Exception as e:
            logger.error(f"Error loading PDF {file_path}: {e}")
            raise
    
    def _load_pdf_sync(self, file_path: str) -> Dict[str, Any]:
        """Synchronous PDF loading"""
        doc = fitz.open(file_path)
        
        # Extract text from all pages
        text_content = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            text_content.append(text)
        
        # Get document metadata
        metadata = doc.metadata
        metadata.update({
            "page_count": len(doc),
            "file_path": file_path
        })
        
        doc.close()
        
        return {
            "text_content": text_content,
            "metadata": metadata,
            "page_count": len(doc)
        }
    
    def extract_text(self, content: Dict[str, Any]) -> str:
        """Extract text content from PDF"""
        text_content = content.get("text_content", [])
        return "\n\n".join(text_content)
    
    def extract_images(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract images from PDF (for future multimodal support)"""
        try:
            doc = fitz.open(file_path)
            images = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    
                    if pix.n - pix.alpha < 4:  # GRAY or RGB
                        img_data = pix.tobytes("png")
                        images.append({
                            "page": page_num,
                            "image_index": img_index,
                            "data": img_data,
                            "format": "png"
                        })
                    
                    pix = None
            
            doc.close()
            return images
            
        except Exception as e:
            logger.error(f"Error extracting images from PDF {file_path}: {e}")
            return []
    
    def extract_tables(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract tables from PDF (for future structured data support)"""
        # TODO: Implement table extraction
        # This would use libraries like tabula-py or camelot-py
        return [] 