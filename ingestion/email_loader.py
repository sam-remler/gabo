"""
Email document loader for EML files
"""

import asyncio
from typing import Dict, Any, List
from pathlib import Path
import email
from email import policy
import logging

from .base_loader import BaseLoader

logger = logging.getLogger(__name__)


class EmailLoader(BaseLoader):
    """Email document loader for EML files"""
    
    def __init__(self):
        super().__init__()
        self.supported_extensions = ['.eml', '.msg']
        self.max_chunk_size = 1000
        self.chunk_overlap = 200
    
    async def load_document(self, file_path: str) -> Dict[str, Any]:
        """Load email document content and metadata"""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, self._load_email_sync, file_path)
            return content
        except Exception as e:
            logger.error(f"Error loading email {file_path}: {e}")
            raise
    
    def _load_email_sync(self, file_path: str) -> Dict[str, Any]:
        """Synchronous email loading"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            email_content = f.read()
        
        # Parse email
        msg = email.message_from_string(email_content, policy=policy.default)
        
        # Extract headers
        headers = dict(msg.items())
        
        # Extract body
        body = self._extract_email_body(msg)
        
        # Extract attachments
        attachments = self._extract_attachments(msg)
        
        return {
            "headers": headers,
            "body": body,
            "attachments": attachments,
            "metadata": {
                "subject": headers.get("Subject", ""),
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "date": headers.get("Date", ""),
                "message_id": headers.get("Message-ID", ""),
                "file_path": file_path
            }
        }
    
    def _extract_email_body(self, msg) -> str:
        """Extract text body from email message"""
        body_parts = []
        
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body_parts.append(part.get_content())
                    except Exception as e:
                        logger.warning(f"Error extracting text part: {e}")
        else:
            if msg.get_content_type() == "text/plain":
                try:
                    body_parts.append(msg.get_content())
                except Exception as e:
                    logger.warning(f"Error extracting text content: {e}")
        
        return "\n\n".join(body_parts)
    
    def _extract_attachments(self, msg) -> List[Dict[str, Any]]:
        """Extract attachments from email message"""
        attachments = []
        
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_disposition() == "attachment":
                    try:
                        filename = part.get_filename()
                        content_type = part.get_content_type()
                        content = part.get_content()
                        
                        attachments.append({
                            "filename": filename,
                            "content_type": content_type,
                            "content": content,
                            "size": len(content) if content else 0
                        })
                    except Exception as e:
                        logger.warning(f"Error extracting attachment: {e}")
        
        return attachments
    
    def extract_text(self, content: Dict[str, Any]) -> str:
        """Extract text content from email"""
        body = content.get("body", "")
        subject = content.get("metadata", {}).get("subject", "")
        
        # Combine subject and body
        text_parts = []
        if subject:
            text_parts.append(f"Subject: {subject}")
        if body:
            text_parts.append(body)
        
        return "\n\n".join(text_parts)
    
    def extract_metadata(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract enhanced metadata from email"""
        metadata = content.get("metadata", {})
        headers = content.get("headers", {})
        
        # Add additional metadata
        enhanced_metadata = {
            **metadata,
            "email_headers": headers,
            "attachment_count": len(content.get("attachments", [])),
            "has_attachments": len(content.get("attachments", [])) > 0
        }
        
        return enhanced_metadata 