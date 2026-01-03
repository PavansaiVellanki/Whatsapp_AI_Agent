"""
Document processing service for extracting text from various file formats
"""
import logging
from typing import Optional, Tuple
import io

logger = logging.getLogger(__name__)

class DocumentService:
    """Service for extracting text from documents"""
    
    def __init__(self):
        """Initialize document service with required libraries"""
        self.supported_formats = {
            '.pdf': self._extract_from_pdf,
            '.txt': self._extract_from_txt,
            '.docx': self._extract_from_docx,
            '.doc': self._extract_from_doc,
            '.md': self._extract_from_txt,
        }
    
    def extract_text(self, file_bytes: bytes, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract text from document based on file extension
        
        Args:
            file_bytes: Document file as bytes
            filename: Original filename with extension
            
        Returns:
            Tuple of (extracted_text, error_message)
        """
        import os
        file_ext = os.path.splitext(filename.lower())[1]
        
        if file_ext not in self.supported_formats:
            return None, f"Unsupported file format: {file_ext}. Supported formats: {', '.join(self.supported_formats.keys())}"
        
        try:
            extractor = self.supported_formats[file_ext]
            text = extractor(file_bytes)
            if not text or not text.strip():
                return None, "No text content found in document"
            return text, None
        except Exception as e:
            logger.error(f"Error extracting text from {filename}: {e}", exc_info=True)
            return None, f"Error extracting text: {str(e)}"
    
    def _extract_from_pdf(self, file_bytes: bytes) -> str:
        """Extract text from PDF file using PyMuPDF (fitz)"""
        try:
            import fitz  # PyMuPDF
            pdf_file = io.BytesIO(file_bytes)
            doc = fitz.open(stream=pdf_file, filetype="pdf")
            
            text = ""
            for page_num in range(len(doc)):
                page = doc[page_num]
                # Extract text with layout preservation
                page_text = page.get_text("text")
                if page_text:
                    text += page_text + "\n"
            
            doc.close()
            return text.strip()
        except ImportError:
            logger.error("PyMuPDF not installed. Install with: pip install pymupdf")
            raise ImportError("PyMuPDF (pymupdf) is required for PDF extraction. Install with: pip install pymupdf")
        except Exception as e:
            logger.error(f"Error reading PDF with PyMuPDF: {e}", exc_info=True)
            raise
    
    def _extract_from_txt(self, file_bytes: bytes) -> str:
        """Extract text from plain text file"""
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            for encoding in encodings:
                try:
                    return file_bytes.decode(encoding)
                except UnicodeDecodeError:
                    continue
            raise ValueError("Could not decode text file with any standard encoding")
        except Exception as e:
            logger.error(f"Error reading text file: {e}")
            raise
    
    def _extract_from_docx(self, file_bytes: bytes) -> str:
        """Extract text from DOCX file"""
        try:
            from docx import Document
            doc_file = io.BytesIO(file_bytes)
            doc = Document(doc_file)
            
            text = ""
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text += paragraph.text + "\n"
            
            return text.strip()
        except ImportError:
            logger.error("python-docx not installed. Install with: pip install python-docx")
            raise ImportError("python-docx is required for DOCX extraction. Install with: pip install python-docx")
        except Exception as e:
            logger.error(f"Error reading DOCX: {e}", exc_info=True)
            raise
    
    def _extract_from_doc(self, file_bytes: bytes) -> str:
        """Extract text from DOC file (legacy Word format)"""
        logger.warning("DOC file format support is limited. Consider converting to DOCX or PDF.")
        try:
            # DOC files are binary and harder to parse
            # You might need additional libraries like textract or antiword
            raise NotImplementedError("DOC file format requires additional libraries. Please convert to DOCX or PDF.")
        except Exception as e:
            logger.error(f"Error reading DOC: {e}")
            raise


