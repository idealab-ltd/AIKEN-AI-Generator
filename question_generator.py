"""
Question Generator module for the PDF Question Extractor project.

This module handles the generation of multiple-choice questions using the LLaMA 3.2 model
via Ollama API. It includes features for:
- Generating contextually relevant questions from text chunks
- Parsing and validating generated questions
- Converting questions to Aiken format
- Handling model API communication
"""

import json
import logging
import requests
from typing import List, Dict, Any, Optional
from utils import validate_aiken_format

logger = logging.getLogger(__name__)

class QuestionGenerator:
    """
    A class to generate multiple-choice questions using LLaMA 3.2 model.
    """
    
    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434"):
        """
        Initialize the question generator.
        
        Args:
            model (str): Name of the Ollama model to use
            base_url (str): Base URL for the Ollama API
        """
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
        
    def generate_questions(self, text: str, num_questions: int = 5) -> List[Dict[str, Any]]:
        """
        Generate multiple-choice questions from text.
        
        Args:
            text (str): Input text to generate questions from
            num_questions (int): Number of questions to generate
            
        Returns:
            List[Dict[str, Any]]: List of generated questions in dictionary format
            
        Each question dictionary contains:
        - 'question': The question text
        - 'options': List of 4 options
        - 'correct': Correct answer letter (A, B, C, or D)
        """
        prompt = self._create_prompt(text, num_questions)
        
        try:
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            
            # Parse response and extract questions
            questions = self._parse_response(response.json()['response'])
            
            # Validate and filter questions
            valid_questions = []
            for q in questions:
                if validate_aiken_format(q):
                    valid_questions.append(q)
                else:
                    logger.warning(f"Invalid question format: {q.get('question', '')[:50]}...")
                    
            logger.info(f"Generated {len(valid_questions)} valid questions")
            return valid_questions
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise
            
    def _create_prompt(self, text: str, num_questions: int) -> str:
        """
        Create a prompt for the LLaMA model.
        
        Args:
            text (str): Input text
            num_questions (int): Number of questions to generate
            
        Returns:
            str: Formatted prompt
        """
        return f"""
        Genera {num_questions} domande a scelta multipla in italiano basate sul seguente testo.
        Ogni domanda deve avere esattamente 4 opzioni (A, B, C, D) e una sola risposta corretta.
        Usa il formato Aiken:

        [Testo della domanda]
        A. [Opzione A]
        B. [Opzione B]
        C. [Opzione C]
        D. [Opzione D]
        ANSWER: [Lettera della risposta corretta]

        Testo:
        {text}
        """
        
    def _parse_response(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse the model's response into structured question dictionaries.
        
        Args:
            response (str): Raw response from the model
            
        Returns:
            List[Dict[str, Any]]: List of parsed questions
        """
        questions = []
        current_question = None
        current_options = []
        
        for line in response.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Start new question if line doesn't start with a letter or ANSWER
            if not (line.startswith(('A.', 'B.', 'C.', 'D.', 'ANSWER:'))):
                if current_question and current_options:
                    questions.append({
                        'question': current_question,
                        'options': current_options,
                        'correct': None
                    })
                current_question = line
                current_options = []
                continue
                
            # Parse options
            if line.startswith(('A.', 'B.', 'C.', 'D.')):
                option_text = line[2:].strip()
                current_options.append(option_text)
                
            # Parse answer
            elif line.startswith('ANSWER:'):
                answer = line[7:].strip()
                if current_question and current_options:
                    questions.append({
                        'question': current_question,
                        'options': current_options,
                        'correct': answer
                    })
                current_question = None
                current_options = []
                
        # Add last question if exists
        if current_question and current_options:
            questions.append({
                'question': current_question,
                'options': current_options,
                'correct': None
            })
            
        return questions
