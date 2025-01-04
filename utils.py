"""
Utility functions for the PDF Question Extractor project.

This module provides helper functions for:
- Text chunking
- File I/O operations for questions
- Data formatting
"""

from typing import List, Dict, Any

def chunk_text(text: str, chunk_size: int = 4000) -> List[str]:
    """
    Split text into chunks of approximately equal size.
    
    Args:
        text (str): Text to split
        chunk_size (int): Target size for each chunk
        
    Returns:
        List[str]: List of text chunks
    """
    chunks = []
    current_pos = 0
    text_length = len(text)

    while current_pos < text_length:
        if current_pos + chunk_size >= text_length:
            chunks.append(text[current_pos:])
            break
            
        # Try to find a good splitting point
        end = min(current_pos + chunk_size, text_length)
        
        # Look for the last period within the chunk
        split_pos = max(
            text.rfind('. ', current_pos, end),
            text.rfind('? ', current_pos, end),
            text.rfind('! ', current_pos, end)
        )
        
        if split_pos == -1:
            # If no good splitting point found, just split at chunk_size
            split_pos = end
            
        chunks.append(text[current_pos:split_pos + 1].strip())
        current_pos = split_pos + 1
        
    return chunks

def save_questions(questions: List[Dict[str, Any]], output_file: str):
    """
    Save questions in Aiken format.
    
    Args:
        questions (List[Dict[str, Any]]): List of question dictionaries
        output_file (str): Path to save questions
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        for question in questions:
            # Write question text
            f.write(f"{question['question']}\n")
            
            # Write options
            for i, option in enumerate(question['options']):
                f.write(f"{chr(65 + i)}. {option}\n")
                
            # Write correct answer
            f.write(f"ANSWER: {question['correct']}\n\n")

def load_questions(file_path: str) -> List[Dict[str, Any]]:
    """
    Load questions from a file in Aiken format.
    
    Args:
        file_path (str): Path to questions file
        
    Returns:
        List[Dict[str, Any]]: List of question dictionaries
    """
    questions = []
    current_question = None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            if current_question and len(current_question['options']) == 4:
                questions.append(current_question)
            current_question = None
            i += 1
            continue
            
        if not line.startswith(('A.', 'B.', 'C.', 'D.', 'ANSWER:')):
            # This is a question
            current_question = {
                'question': line,
                'options': [],
                'correct': None
            }
        elif line.startswith('ANSWER:'):
            if current_question:
                current_question['correct'] = line.split(':')[1].strip()
        elif current_question and line[0] in 'ABCD' and line[1] == '.':
            current_question['options'].append(line[2:].strip())
            
        i += 1
        
    # Add the last question if it exists
    if current_question and len(current_question['options']) == 4:
        questions.append(current_question)
        
    return questions
