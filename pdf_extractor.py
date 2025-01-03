"""
Module for extracting text from PDF files.
"""
import PyPDF2
from typing import List
import logging
from utils import chunk_text

logger = logging.getLogger(__name__)

class PDFExtractor:
    def __init__(self, pdf_path: str):
        """
        Initialize PDF extractor.
        
        Args:
            pdf_path (str): Path to the PDF file
        """
        self.pdf_path = pdf_path
        
    def extract_text(self) -> List[str]:
        """
        Extract text from PDF and split it into manageable chunks.
        
        Returns:
            List[str]: List of text chunks
        """
        try:
            with open(self.pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                
                total_pages = len(reader.pages)
                logger.info(f"Processing {total_pages} pages...")
                
                for i, page in enumerate(reader.pages):
                    if i % 50 == 0:
                        logger.info(f"Processing page {i+1}/{total_pages}")
                    text += page.extract_text() + "\n"
                
                # Split text into chunks for processing
                chunks = chunk_text(text)
                logger.info(f"Text split into {len(chunks)} chunks")
                
                return chunks
                
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise
