"""
Second passage validation script for the PDF Question Extractor project.

This script takes a PDF file and a file containing questions in Aiken format,
then uses the LLaMA 3.2 model to validate and improve each question while maintaining
the original question's intent. The improved questions are saved to a new file,
leaving the original questions untouched.

Features:
- Validates questions against their relevant PDF context
- Improves clarity and precision of questions
- Maintains Aiken format compatibility
- Preserves original questions file
- Shows progress with color-coded output

Usage:
    python second_passage.py codice_civ.pdf questions.txt --output improved_questions.txt
"""

import logging
import argparse
import requests
from typing import List, Dict, Any
from tqdm import tqdm
from pdf_extractor import PDFExtractor
from utils import chunk_text, load_questions

# Configure logging with colors for better readability
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

# ANSI Color codes for prettier output
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

class QuestionValidator:
    """
    A class that validates and improves questions using the LLaMA 3.2 model.
    
    This class takes questions in Aiken format and their corresponding context
    from a PDF, then uses the LLaMA model to either approve them as-is or suggest
    improvements while maintaining the original intent.
    """
    
    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434"):
        """
        Initialize the validator with model settings.
        
        Args:
            model (str): Name of the Ollama model to use (default: llama3.2)
            base_url (str): Base URL for the Ollama API
        """
        self.model = model
        self.api_url = f"{base_url}/api/generate"
        
    def validate_and_improve_question(self, question: Dict[str, Any], context: str) -> Dict[str, Any]:
        """
        Validate and potentially improve a single question.
        
        Args:
            question (Dict[str, Any]): Question in dictionary format with 'question',
                                     'options', and 'correct' fields
            context (str): Relevant text from the PDF for this question
            
        Returns:
            Dict[str, Any]: Either the original question if it's good, or an improved
                           version maintaining the same format
        """
        # Construct prompt for the model
        prompt = f"""Sei un esperto professore di diritto italiano. Analizza e migliora questa domanda a scelta multipla:

Domanda:
{question['question']}
A. {question['options'][0]}
B. {question['options'][1]}
C. {question['options'][2]}
D. {question['options'][3]}
Risposta corretta: {question['correct']}

Contesto dal codice civile:
{context}

Se la domanda è corretta, rispondi con "OK".
Se invece ci sono problemi, fornisci la versione corretta della domanda nello stesso formato:
[Domanda corretta]
A. [Opzione corretta]
B. [Opzione corretta]
C. [Opzione corretta]
D. [Opzione corretta]
ANSWER: [Lettera corretta]

Migliora la chiarezza e la precisione della domanda mantenendo lo stesso concetto."""

        try:
            # Send request to Ollama API
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1  # Low temperature for more consistent output
                    }
                }
            )
            response.raise_for_status()
            result = response.json()['response'].strip()
            
            # If model says OK, keep original question
            if result == "OK":
                return question
            else:
                # Parse the improved question from model's response
                lines = result.split('\n')
                improved_question = {
                    'question': lines[0].strip(),
                    'options': [],
                    'correct': None
                }
                
                # Extract options and correct answer
                for line in lines[1:]:
                    line = line.strip()
                    if line.startswith(('A.', 'B.', 'C.', 'D.')):
                        improved_question['options'].append(line[2:].strip())
                    elif line.startswith('ANSWER:'):
                        improved_question['correct'] = line.split(':')[1].strip()
                
                # Return improved version only if it's complete and valid
                if len(improved_question['options']) == 4 and improved_question['correct']:
                    return improved_question
                else:
                    return question
                    
        except Exception as e:
            logger.error(f"{RED}Error improving question: {str(e)}{RESET}")
            return question

def save_validated_questions(questions: List[Dict[str, Any]], output_file: str):
    """
    Save questions to a file in Aiken format.
    
    Args:
        questions (List[Dict[str, Any]]): List of questions to save
        output_file (str): Path where to save the questions
    """
    logger.info(f"\n{BLUE}Saving improved questions...{RESET}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for question in questions:
            f.write(f"{question['question']}\n")
            for i, option in enumerate(question['options']):
                f.write(f"{chr(65 + i)}. {option}\n")
            f.write(f"ANSWER: {question['correct']}\n\n")
    
    logger.info(f"{GREEN}Saved improved questions to {output_file}{RESET}")

def main():
    """
    Main function that orchestrates the question improvement process.
    
    Steps:
    1. Load original questions from file
    2. Extract text from PDF
    3. For each question:
       - Find most relevant context from PDF
       - Validate and potentially improve the question
    4. Save improved questions to new file
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Validate and improve questions using LLaMA 3.2')
    parser.add_argument('pdf_path', help='Path to the original PDF file')
    parser.add_argument('questions_file', help='Path to the generated questions file')
    parser.add_argument('--chunk-size', type=int, default=8000,
                      help='Size of text chunks to process (default: 8000)')
    parser.add_argument('--output', default='questions_improved.txt',
                      help='Output file for improved questions (default: questions_improved.txt)')
    parser.add_argument('--debug', action='store_true',
                      help='Enable debug logging')
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        print(f"\n{BLUE}{'='*20} Question Improvement {'='*20}{RESET}")
        
        # Step 1: Load original questions
        logger.info(f"{BLUE}Loading generated questions...{RESET}")
        questions = load_questions(args.questions_file)
        logger.info(f"{GREEN}Loaded {len(questions)} questions{RESET}")

        # Step 2: Extract text from PDF
        print(f"\n{BLUE}{'='*20} Extracting PDF Text {'='*20}{RESET}")
        logger.info(f"{BLUE}Starting PDF text extraction...{RESET}")
        
        try:
            extractor = PDFExtractor(args.pdf_path)
            text_chunks = extractor.extract_text(chunk_size=args.chunk_size)
            
            # Combine chunks into larger ones for context
            text = ''.join(text_chunks)
            large_chunks = chunk_text(text, args.chunk_size)
            logger.info(f"{GREEN}Extracted {len(text_chunks)} text chunks{RESET}")
            logger.info(f"{GREEN}Combined into {len(large_chunks)} large chunks for validation{RESET}")
        except Exception as e:
            logger.error(f"{RED}Error during PDF extraction: {str(e)}{RESET}")
            raise
        
        # Step 3: Improve questions
        print(f"\n{BLUE}{'='*20} Improving Questions {'='*20}{RESET}")
        logger.info(f"{BLUE}Starting improvement of {len(questions)} questions...{RESET}")

        validator = QuestionValidator()
        improved_questions = []
        
        # Process each question with progress bar
        for i, question in enumerate(tqdm(questions, desc="Questions processed", 
                                        bar_format="{l_bar}%s{bar}%s{r_bar}" % (GREEN, RESET)), 1):
            # Find most relevant chunk for this question
            most_relevant_chunk = None
            max_overlap = 0
            
            for chunk in large_chunks:
                question_words = set(question['question'].lower().split())
                chunk_words = set(chunk.lower().split())
                overlap = len(question_words & chunk_words)
                
                if overlap > max_overlap:
                    max_overlap = overlap
                    most_relevant_chunk = chunk

            if most_relevant_chunk:
                improved_question = validator.validate_and_improve_question(question, most_relevant_chunk)
                improved_questions.append(improved_question)
            else:
                logger.warning(f"{YELLOW}Could not find relevant context for question {i}{RESET}")
                improved_questions.append(question)

        # Step 4: Save results
        print(f"\n{BLUE}{'='*20} Saving Results {'='*20}{RESET}")
        save_validated_questions(improved_questions, args.output)
        
        # Print summary
        print(f"\n{BLUE}{'='*20} Improvement Summary {'='*20}{RESET}")
        logger.info(f"{BLUE}Total questions processed: {len(questions)}")
        logger.info(f"Improved questions saved to: {args.output}{RESET}")
        
        print(f"\n{GREEN}{'='*20} Process Complete {'='*20}{RESET}")

    except Exception as e:
        logger.error(f"{RED}Error during validation: {str(e)}{RESET}")
        raise

if __name__ == '__main__':
    main()
