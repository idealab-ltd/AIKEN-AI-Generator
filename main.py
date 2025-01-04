"""
Main script for the PDF Question Extractor project.

This script orchestrates the process of:
1. Extracting text from PDF documents
2. Generating multiple-choice questions using LLaMA 3.2
3. Saving questions in Aiken format
"""

import os
import logging
import argparse
from typing import List, Dict, Any
from tqdm import tqdm
from pdf_extractor import PDFExtractor
from question_generator import QuestionGenerator
from utils import save_questions

# Configure logging with colors
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'  # Simplified format since we'll add colors manually
)
logger = logging.getLogger(__name__)

# ANSI Color codes
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

def process_pdf(pdf_path: str, chunk_size: int = 4000, show_questions: bool = False) -> List[Dict[str, Any]]:
    """
    Process a PDF file to generate questions.
    
    Args:
        pdf_path (str): Path to PDF file
        chunk_size (int): Size of text chunks to process
        show_questions (bool): Whether to display questions as they're generated
        
    Returns:
        List[Dict[str, Any]]: Generated questions
    """
    all_questions = []
    
    try:
        # Step 1: Extract text from PDF
        print(f"\n{BLUE}{'='*20} Extracting PDF Text {'='*20}{RESET}")
        logger.info(f"{BLUE}Starting PDF text extraction...{RESET}")
        
        extractor = PDFExtractor(pdf_path)
        text_chunks = extractor.extract_text()
        
        logger.info(f"{GREEN}Successfully extracted {len(text_chunks)} text chunks{RESET}")
        
        # Step 2: Generate questions from chunks
        print(f"\n{BLUE}{'='*20} Generating Questions {'='*20}{RESET}")
        logger.info(f"{BLUE}Initializing question generator with LLaMA 3.2...{RESET}")
        
        generator = QuestionGenerator()
        total_chunks = len(text_chunks)
        
        # Use tqdm for progress tracking
        for i, chunk in enumerate(tqdm(text_chunks, desc="Processing chunks", 
                                     bar_format="{l_bar}%s{bar}%s{r_bar}" % (GREEN, RESET)), 1):
            logger.info(f"\n{BLUE}Processing chunk {i}/{total_chunks}{RESET}")
            
            try:
                questions = generator.generate_questions(chunk)
                all_questions.extend(questions)
                
                if show_questions:
                    print(f"\n{YELLOW}Generated {len(questions)} questions from chunk {i}:{RESET}")
                    for q in questions:
                        print(f"\n{YELLOW}Question: {q['question']}")
                        for j, opt in enumerate(q['options']):
                            print(f"{chr(65 + j)}. {opt}")
                        print(f"ANSWER: {q['correct']}{RESET}")
                
            except Exception as e:
                logger.error(f"{RED}Error processing chunk {i}: {str(e)}{RESET}")
                continue
        
        logger.info(f"\n{GREEN}Question Generation Complete!")
        logger.info(f"Total questions generated: {len(all_questions)}{RESET}")
        
        return all_questions
        
    except Exception as e:
        logger.error(f"{RED}Error processing PDF: {str(e)}{RESET}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Generate multiple-choice questions from a PDF file')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('--chunk-size', type=int, default=4000,
                      help='Size of text chunks to process (default: 4000)')
    parser.add_argument('--output', default='questions.txt',
                      help='Output file path (default: questions.txt)')
    parser.add_argument('--show-questions', action='store_true',
                      help='Display questions as they are generated')
    parser.add_argument('--debug', action='store_true',
                      help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        print(f"\n{BLUE}{'='*20} PDF Question Extractor {'='*20}{RESET}")
        logger.info(f"{BLUE}Starting question generation process...{RESET}")
        
        # Process PDF and generate questions
        questions = process_pdf(args.pdf_path, args.chunk_size, args.show_questions)
        
        # Save questions
        print(f"\n{BLUE}{'='*20} Saving Questions {'='*20}{RESET}")
        logger.info(f"{BLUE}Saving questions to {args.output}...{RESET}")
        
        save_questions(questions, args.output)
        
        logger.info(f"{GREEN}Successfully saved {len(questions)} questions to {args.output}{RESET}")
        print(f"\n{GREEN}{'='*20} Process Complete {'='*20}{RESET}")
        
    except Exception as e:
        logger.error(f"{RED}Error: {str(e)}{RESET}")
        raise

if __name__ == '__main__':
    main()
