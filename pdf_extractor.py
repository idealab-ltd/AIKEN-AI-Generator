"""
PDF Extractor module for the PDF Question Extractor project.

This module handles the extraction of text from PDF documents and splits it into
manageable chunks for processing. It includes features for:
- Reading PDF files using PyPDF2
- Cleaning and normalizing extracted text
- Splitting text into chunks while preserving context
- Handling PDF reading errors gracefully
"""

import PyPDF2
import logging
from typing import List
from utils import chunk_text
from tqdm import tqdm

logger = logging.getLogger(__name__)

# ANSI Color codes
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

class PDFExtractor:
    def __init__(self, pdf_path: str = None):
        """
        Initialize PDF extractor.
        
        Args:
            pdf_path (str, optional): Path to PDF file
        """
        self.pdf_path = pdf_path
        
    def extract_text(self, chunk_size: int = 4000) -> List[str]:
        """
        Extract text from PDF and split into chunks.
        
        Args:
            chunk_size (int): Size of text chunks to process (default: 4000)
        
        Returns:
            List[str]: List of text chunks
            
        Raises:
            FileNotFoundError: If PDF file not found
            PyPDF2.errors.PdfReadError: If PDF cannot be read
        """
        if not self.pdf_path:
            raise ValueError("PDF path not set")
            
        try:
            logger.info(f"{BLUE}Opening PDF file: {self.pdf_path}{RESET}")
            with open(self.pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                total_chars = 0
                
                # Extract text from each page with progress bar
                total_pages = len(reader.pages)
                logger.info(f"{BLUE}Processing {total_pages} pages...{RESET}")
                
                for i in tqdm(range(total_pages), desc="Extracting pages", 
                            bar_format="{l_bar}{bar}{r_bar}"):
                    page = reader.pages[i]
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
                        total_chars += len(page_text)
                    logger.debug(f"Extracted page {i+1}/{total_pages}")
                        
                # Clean and normalize text
                text = self._clean_text(text)
                logger.info(f"{GREEN}Text extraction completed")
                logger.info(f"Total characters extracted: {total_chars:,}{RESET}")
                
                # Split into chunks
                chunks = chunk_text(text, chunk_size)
                valid_chunks = [chunk for chunk in chunks if len(chunk.strip()) > 100]  # Filter out very small chunks
                
                # Log chunk statistics
                total_chunks = len(chunks)
                valid_chunk_count = len(valid_chunks)
                avg_chunk_size = sum(len(chunk) for chunk in valid_chunks) / valid_chunk_count if valid_chunk_count > 0 else 0
                
                logger.info(f"{GREEN}Extracted {valid_chunk_count:,} valid text chunks")
                logger.info(f"Average chunk size: {avg_chunk_size:,.0f} characters")
                if total_chunks != valid_chunk_count:
                    logger.info(f"{YELLOW}Filtered out {total_chunks - valid_chunk_count} small chunks{RESET}")
                
                return valid_chunks
                
        except FileNotFoundError:
            logger.error(f"{RED}PDF file not found: {self.pdf_path}{RESET}")
            raise
        except PyPDF2.errors.PdfReadError as e:
            logger.error(f"{RED}Error reading PDF: {str(e)}{RESET}")
            raise
        except Exception as e:
            logger.error(f"{RED}Unexpected error: {str(e)}{RESET}")
            raise
            
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.
        
        Args:
            text (str): Raw text from PDF
            
        Returns:
            str: Cleaned text
        """
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Normalize line endings
        text = text.replace('\r\n', '\n')
        
        # Add space after periods if missing
        text = text.replace('.',' . ').replace('  ', ' ')
        
        # Remove any non-breaking spaces
        text = text.replace('\xa0', ' ')
        
        return text
