"""
GIFT format converter for the PDF Question Extractor project.

This script takes an Aiken format question file and converts it to GIFT format,
adding detailed feedback for each answer option based on the PDF context.
The feedback includes direct quotations and law references where applicable.

Features:
- Converts Aiken to GIFT format
- Adds contextual feedback for each answer
- Uses PDF content for accurate feedback
- Preserves original Aiken file
- Shows progress with color-coded output

Usage:
    python gift_converter.py codice_civ.pdf questions_improved.txt --output questions.gift
"""

import logging
import argparse
import requests
from typing import List, Dict, Any, Tuple
from tqdm import tqdm
from pdf_extractor import PDFExtractor
from utils import chunk_text, load_questions
import re

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

class GiftConverter:
    """
    A class that converts Aiken format questions to GIFT format with feedback.
    
    This class takes questions in Aiken format and their corresponding context
    from a PDF, then uses the LLaMA model to generate appropriate feedback for
    each answer option, including relevant quotes and law references.
    """
    
    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434"):
        """
        Initialize the converter with model settings.
        
        Args:
            model (str): Name of the Ollama model to use (default: llama3.2)
            base_url (str): Base URL for the Ollama API
        """
        self.model = model
        self.api_url = f"{base_url}/api/generate"
    
    def generate_feedback(self, question: Dict[str, Any], context: str) -> Tuple[List[str], List[str]]:
        """
        Generate feedback for each answer option.
        
        Args:
            question (Dict[str, Any]): Question in dictionary format with 'question',
                                     'options', and 'correct' fields
            context (str): Relevant text from the PDF for this question
            
        Returns:
            Tuple[List[str], List[str]]: Lists of feedback for correct and incorrect answers
        """
        prompt = f"""Analizza questa domanda del codice civile italiano e fornisci un feedback specifico per ogni risposta, usando SEMPRE citazioni dirette dal testo.

Domanda:
{question['question']}

Opzioni:
A. {question['options'][0]}
B. {question['options'][1]}
C. {question['options'][2]}
D. {question['options'][3]}

Risposta corretta: {question['correct']}

Contesto dal codice civile:
{context}

ISTRUZIONI IMPORTANTI:
1. Per OGNI risposta DEVI:
   - Includere una citazione diretta dal codice civile usando le virgolette (" ")
   - Specificare l'articolo di riferimento
   - Non fare MAI riferimento alle altre opzioni

2. Formato del feedback per risposta corretta:
   "Corretto. L'articolo [X] stabilisce: '[citazione diretta]'"

3. Formato del feedback per risposta errata:
   "Errato. L'articolo [X] stabilisce invece: '[citazione diretta]'"

4. Se non trovi una citazione diretta pertinente nel contesto fornito, usa questa formula:
   "Consultare l'articolo [X] del Codice Civile per il testo completo"

ESEMPIO DI FEEDBACK:
FEEDBACK_A: Errato. L'articolo 230-bis stabilisce: "Il familiare che presta in modo continuativo la sua attività di lavoro nella famiglia o nell'impresa familiare ha diritto [...]"
FEEDBACK_B: Corretto. L'articolo 230-bis stabilisce: "Salvo che sia configurabile un diverso rapporto, il familiare che presta in modo continuativo la sua attività di lavoro [...]"

Fornisci il feedback per ogni opzione:
FEEDBACK_A: [feedback per opzione A con citazione]
FEEDBACK_B: [feedback per opzione B con citazione]
FEEDBACK_C: [feedback per opzione C con citazione]
FEEDBACK_D: [feedback per opzione D con citazione]"""

        try:
            # Send request to Ollama API
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1
                    }
                }
            )
            response.raise_for_status()
            result = response.json()['response'].strip()
            
            # Parse feedback for each option
            feedbacks = {'A': '', 'B': '', 'C': '', 'D': ''}
            current_feedback = None
            
            for line in result.split('\n'):
                line = line.strip()
                if line.startswith('FEEDBACK_'):
                    current_feedback = line[9:10]  # Get the option letter
                    line = line[12:].strip()  # Remove "FEEDBACK_X: "
                
                if current_feedback and line:
                    if feedbacks[current_feedback]:
                        feedbacks[current_feedback] += ' ' + line
                    else:
                        feedbacks[current_feedback] = line
            
            # Validate feedbacks contain citations
            for letter, feedback in feedbacks.items():
                if not ('"' in feedback or "'" in feedback):
                    article_match = re.search(r'articolo (\d+(?:-[a-z]+)?)', feedback, re.IGNORECASE)
                    if article_match:
                        article = article_match.group(1)
                        feedbacks[letter] = f"Consultare l'articolo {article} del Codice Civile per il testo completo"
            
            # Separate correct and incorrect feedbacks
            correct_letter = question['correct']
            correct_feedback = [feedbacks[correct_letter]] if feedbacks[correct_letter] else ["Consultare il Codice Civile per il testo completo"]
            
            wrong_feedback = []
            for letter in ['A', 'B', 'C', 'D']:
                if letter != correct_letter and feedbacks[letter]:
                    wrong_feedback.append(feedbacks[letter])
            
            if not wrong_feedback:
                wrong_feedback = ["Consultare il Codice Civile per il testo completo"]
            
            return correct_feedback, wrong_feedback
                    
        except Exception as e:
            logger.error(f"{RED}Error generating feedback: {str(e)}{RESET}")
            return (["Consultare il Codice Civile per il testo completo"], 
                   ["Consultare il Codice Civile per il testo completo"])

    def convert_to_gift(self, question: Dict[str, Any], context: str) -> str:
        """
        Convert a single question from Aiken to GIFT format with feedback.
        
        Args:
            question (Dict[str, Any]): Question in Aiken format
            context (str): Relevant text from PDF
            
        Returns:
            str: Question in GIFT format with feedback
        """
        # Get feedback for answers
        correct_feedback, wrong_feedback = self.generate_feedback(question, context)
        
        # Start building GIFT format
        gift = f"::Q:: {question['question']}\n{{"
        
        # Add each option with appropriate feedback
        wrong_idx = 0
        for i, option in enumerate(question['options']):
            if chr(65 + i) == question['correct']:
                feedback = correct_feedback[0] if correct_feedback else "Consultare il Codice Civile per il testo completo"
                gift += f" ={option} # {feedback}"
            else:
                feedback = wrong_feedback[wrong_idx] if wrong_idx < len(wrong_feedback) else "Consultare il Codice Civile per il testo completo"
                wrong_idx += 1
                gift += f" ~{option} # {feedback}"
        
        gift += " }\n\n"
        return gift

def save_gift_questions(questions: List[str], output_file: str, batch_size: int = 500, show_gift: bool = False):
    """
    Save questions in GIFT format, creating a new file every batch_size questions.
    
    Args:
        questions (List[str]): List of questions in GIFT format
        output_file (str): Base path for output files. Will append _1, _2, etc.
                          for each batch of batch_size questions
        batch_size (int): Number of questions per output file (default: 500)
        show_gift (bool): If True, display converted questions in output
    """
    logger.info(f"\n{BLUE}Saving GIFT format questions...{RESET}")
    
    # Split questions into batches
    num_batches = (len(questions) + batch_size - 1) // batch_size
    
    # Get base filename without extension
    base_name = output_file.rsplit('.', 1)[0]
    extension = output_file.rsplit('.', 1)[1] if '.' in output_file else 'gift'
    
    for batch_num in range(num_batches):
        start_idx = batch_num * batch_size
        end_idx = min((batch_num + 1) * batch_size, len(questions))
        
        # Create batch filename
        if num_batches > 1:
            batch_file = f"{base_name}_{batch_num + 1}.{extension}"
        else:
            batch_file = output_file
            
        # Get questions for this batch
        batch_questions = questions[start_idx:end_idx]
        
        # Save this batch
        with open(batch_file, 'w', encoding='utf-8') as f:
            f.writelines(batch_questions)
        
        logger.info(f"{GREEN}Saved questions {start_idx + 1}-{end_idx} to {batch_file}{RESET}")
        
        # Show converted questions if requested
        if show_gift:
            logger.info(f"\n{BLUE}Questions in {batch_file}:{RESET}")
            for i, question in enumerate(batch_questions, start=start_idx + 1):
                logger.info(f"\n{YELLOW}Question {i}:{RESET}")
                logger.info(question.strip())
    
    logger.info(f"\n{GREEN}Completed saving all {len(questions)} questions across {num_batches} files{RESET}")

def main():
    """
    Main function that orchestrates the GIFT conversion process.
    
    Steps:
    1. Load Aiken format questions
    2. Extract text from PDF
    3. For each question:
       - Find most relevant context from PDF
       - Generate feedback based on context
       - Convert to GIFT format with feedback
    4. Save GIFT format questions to new files (batch_size questions per file)
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Convert Aiken questions to GIFT format with feedback')
    parser.add_argument('pdf_path', help='Path to the original PDF file')
    parser.add_argument('questions_file', help='Path to the Aiken format questions file')
    parser.add_argument('--chunk-size', type=int, default=8000,
                      help='Size of text chunks to process (default: 8000)')
    parser.add_argument('--output', default='questions.gift',
                      help='Output file for GIFT format questions (default: questions.gift). Will append _1, _2, etc. if more than batch_size questions')
    parser.add_argument('--batch-size', type=int, default=500,
                      help='Number of questions per output file (default: 500)')
    parser.add_argument('--show-gift', action='store_true',
                      help='Show converted questions in output')
    parser.add_argument('--debug', action='store_true',
                      help='Enable debug logging')
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        print(f"\n{BLUE}{'='*20} GIFT Format Conversion {'='*20}{RESET}")
        
        # Step 1: Load Aiken questions
        logger.info(f"{BLUE}Loading Aiken format questions...{RESET}")
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
            logger.info(f"{GREEN}Combined into {len(large_chunks)} large chunks for context{RESET}")
        except Exception as e:
            logger.error(f"{RED}Error during PDF extraction: {str(e)}{RESET}")
            raise
        
        # Step 3: Convert questions to GIFT format
        print(f"\n{BLUE}{'='*20} Converting to GIFT Format {'='*20}{RESET}")
        logger.info(f"{BLUE}Starting conversion of {len(questions)} questions...{RESET}")

        converter = GiftConverter()
        gift_questions = []
        
        # Process each question with progress bar
        for i, question in enumerate(tqdm(questions, desc="Questions converted", 
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
                gift_question = converter.convert_to_gift(question, most_relevant_chunk)
                gift_questions.append(gift_question)
                
                # Show conversion in real-time if requested
                if args.show_gift:
                    logger.info(f"\n{YELLOW}Converting Question {i}:{RESET}")
                    logger.info(f"{BLUE}Original (Aiken):{RESET}")
                    logger.info(f"{question['question']}")
                    for j, opt in enumerate(question['options']):
                        logger.info(f"{chr(65 + j)}. {opt}")
                    logger.info(f"ANSWER: {question['correct']}\n")
                    logger.info(f"{GREEN}Converted (GIFT):{RESET}")
                    logger.info(gift_question)
            else:
                logger.warning(f"{YELLOW}Could not find relevant context for question {i}{RESET}")
                # Create basic GIFT format without detailed feedback
                gift_question = converter.convert_to_gift(question, "")
                gift_questions.append(gift_question)

        # Step 4: Save results
        print(f"\n{BLUE}{'='*20} Saving Results {'='*20}{RESET}")
        save_gift_questions(gift_questions, args.output, batch_size=args.batch_size, show_gift=args.show_gift)
        
        # Print summary
        print(f"\n{BLUE}{'='*20} Conversion Summary {'='*20}{RESET}")
        logger.info(f"{BLUE}Total questions converted: {len(questions)}")
        logger.info(f"GIFT format questions saved to: {args.output}{RESET}")
        
        print(f"\n{GREEN}{'='*20} Process Complete {'='*20}{RESET}")

    except Exception as e:
        logger.error(f"{RED}Error during conversion: {str(e)}{RESET}")
        raise

if __name__ == '__main__':
    main()
