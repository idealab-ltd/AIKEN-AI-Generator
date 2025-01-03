"""
Utility functions for the PDF Question Extractor project.
"""
import os
import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def chunk_text(text: str, chunk_size: int = 4000, overlap: int = 500) -> List[str]:
    """
    Split text into smaller chunks for processing.
    
    Args:
        text (str): Input text to be chunked
        chunk_size (int): Maximum size of each chunk
        overlap (int): Number of characters to overlap between chunks
    
    Returns:
        List[str]: List of text chunks
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        
        if end >= text_length:
            chunks.append(text[start:])
            break
            
        # Try to find a good breaking point (preferably at the end of an article or section)
        break_points = [
            text.rfind('\n\nArt.', start, end),
            text.rfind('\n\nArticolo', start, end),
            text.rfind('\n\nSEZIONE', start, end),
            text.rfind('\n\nCAPO', start, end),
            text.rfind('. ', start, end),
            text.rfind('\n', start, end)
        ]
        
        # Use the first valid break point found
        last_break = max([p for p in break_points if p != -1] or [end - overlap])
            
        if last_break != -1:
            end = last_break + 1
            
        chunks.append(text[start:end])
        start = end - overlap
        
    return chunks

def validate_aiken_format(question: Dict[str, Any]) -> bool:
    """
    Validate if a question follows Aiken format requirements.
    
    Args:
        question (Dict[str, Any]): Question dictionary with 'question', 'options', and 'correct' keys
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not all(key in question for key in ['question', 'options', 'correct']):
        return False
        
    if len(question['options']) != 4:
        return False
        
    if question['correct'] not in ['A', 'B', 'C', 'D']:
        return False
        
    return True

def save_questions(questions: List[Dict[str, Any]], output_file: str) -> None:
    """
    Save questions in Aiken format to a file.
    
    Args:
        questions (List[Dict[str, Any]]): List of question dictionaries
        output_file (str): Path to output file
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        for q in questions:
            if not validate_aiken_format(q):
                logger.warning(f"Skipping invalid question: {q['question'][:50]}...")
                continue
                
            # Remove "Question:" prefix if it exists
            question_text = q['question']
            if question_text.startswith('Question:'):
                question_text = question_text[9:].strip()
                
            f.write(f"{question_text}\n")
            for i, option in enumerate(q['options']):
                f.write(f"{chr(65 + i)}. {option}\n")
            f.write(f"ANSWER: {q['correct']}\n\n")
