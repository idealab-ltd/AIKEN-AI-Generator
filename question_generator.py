"""
Module for generating questions using LLaMA 2 through Ollama.
"""
import json
import requests
from typing import List, Dict, Any
import logging
import time
import re

logger = logging.getLogger(__name__)

class QuestionGenerator:
    def __init__(self, model: str = "llama3.2"):
        """
        Initialize question generator.
        
        Args:
            model (str): Name of the Ollama model to use
        """
        self.model = model
        self.api_url = "http://localhost:11434/api/chat"
        self.total_valid_questions = 0
        self.total_attempts = 0
        
    def _generate_prompt(self, text: str) -> str:
        """
        Create a prompt for question generation.
        
        Args:
            text (str): Input text chunk
        
        Returns:
            str: Formatted prompt
        """
        return f"""You are a professional Italian law professor. Your task is to create multiple choice questions about Italian law from the given text.

Rules:
1. Create exactly 2 multiple choice questions about Italian legal concepts
2. Each question must have exactly 4 options (A, B, C, D)
3. Only one option should be correct
4. Each question must follow this EXACT format:

[Question text without any prefixes or option letters]
A. [First option]
B. [Second option]
C. [Third option]
D. [Fourth option]
ANSWER: [A or B or C or D]

Important formatting rules:
- Start with the complete question text, without any letter prefix
- NEVER start the question text with "A." or any other letter
- Each option must start with exactly "A.", "B.", "C.", or "D." (in that order)
- Never repeat option letters (no two "A." options)
- The answer must be in the format "ANSWER: X" where X is A, B, C, or D
- Leave exactly one blank line between questions
- Do not add any explanations or additional text

Example of a good question:
Secondo l'articolo 1 del Codice Civile, quando si acquista la capacità giuridica?
A. Dal momento del concepimento
B. Dal momento della nascita
C. Al compimento del diciottesimo anno di età
D. Al momento dell'iscrizione all'anagrafe
ANSWER: B

Example of a BAD question (do not do this):
A. Secondo l'articolo 1, quando si acquista la capacità giuridica?
A. Dal momento del concepimento
B. Dal momento della nascita
C. Al compimento del diciottesimo anno di età
D. Al momento dell'iscrizione all'anagrafe
ANSWER: B

Here is the text to create questions from:
{text}"""

    def generate_questions(self, text: str) -> List[Dict[str, Any]]:
        """
        Generate questions from text using LLaMA 2.
        
        Args:
            text (str): Input text chunk
        
        Returns:
            List[Dict[str, Any]]: List of generated questions
        """
        # Display current statistics
        success_rate = (self.total_valid_questions / self.total_attempts * 100) if self.total_attempts > 0 else 0
        logger.info(f"\nCurrent Statistics:")
        logger.info(f"Total valid questions generated so far: {self.total_valid_questions}")
        logger.info(f"Total generation attempts: {self.total_attempts}")
        logger.info(f"Success rate: {success_rate:.1f}%\n")

        prompt = self._generate_prompt(text)
        logger.info(f"Using model: {self.model}")
        logger.debug(f"Generated prompt length: {len(prompt)} chars")
        
        try:
            # First check if Ollama is running
            try:
                tags_response = requests.get("http://localhost:11434/api/tags")
                tags_data = tags_response.json()
                logger.debug(f"Available models: {[m['name'] for m in tags_data.get('models', [])]}")
            except requests.exceptions.ConnectionError:
                logger.error("Cannot connect to Ollama. Please make sure Ollama is running.")
                raise Exception("Ollama is not running. Please start Ollama first.")

            logger.info("Sending request to Ollama API...")
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "top_k": 40,
                        "num_predict": 500
                    }
                }
            )
            response.raise_for_status()
            
            # Parse the response
            response_data = response.json()
            if "message" not in response_data or "content" not in response_data["message"]:
                logger.error(f"Unexpected response format: {response_data}")
                return []
                
            response_content = response_data["message"]["content"].strip()
            logger.info(f"Raw response from model:\n{response_content}")
            
            # Split into questions by looking for patterns
            questions = []
            current_lines = []
            answer_line = None
            
            for line in response_content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                # If we find an answer line
                if line.startswith('ANSWER:'):
                    answer_line = line
                    # If we have content, this completes a question
                    if current_lines:
                        current_lines.append(answer_line)
                        questions.append('\n'.join(current_lines))
                        current_lines = []
                        answer_line = None
                # If we find a question line and have an answer from previous question
                elif not re.match(r'^[A-D]\.', line) and answer_line:
                    # Start a new question
                    current_lines = [line]
                    answer_line = None
                # Otherwise add to current question
                else:
                    current_lines.append(line)
            
            # Add the last question if there is one with an answer
            if current_lines and answer_line:
                current_lines.append(answer_line)
                questions.append('\n'.join(current_lines))
            
            logger.info(f"Found {len(questions)} potential questions")
            
            parsed_questions = []
            self.total_attempts += len(questions)  # Count attempts for this chunk
            
            for i, q_text in enumerate(questions, 1):
                logger.info(f"Attempting to parse question {i}:\n{q_text}")
                parsed_q = self._parse_question(q_text)
                if parsed_q:
                    parsed_questions.append(parsed_q)
                    self.total_valid_questions += 1  # Increment valid questions counter
                    logger.info(f"Successfully parsed question: {parsed_q['question'][:50]}...")
                else:
                    logger.warning(f"Failed to parse question {i}")
            
            # Add a small delay to avoid overwhelming the API
            time.sleep(1)
            return parsed_questions
            
        except Exception as e:
            logger.error(f"Error generating questions: {str(e)}")
            raise

    def _parse_question(self, text: str) -> Dict[str, Any]:
        """
        Parse a single question text into a structured format.
        
        Args:
            text (str): Raw question text
            
        Returns:
            Dict[str, Any]: Parsed question or None if invalid
        """
        try:
            # Split into components
            components = {'question': [], 'options': [], 'answer': None}
            current_part = 'question'
            
            for line in text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('ANSWER:'):
                    components['answer'] = line
                elif re.match(r'^[A-D]\.', line):
                    current_part = 'options'
                    components['options'].append(line)
                elif current_part == 'question':
                    components['question'].append(line)
            
            # Validate structure
            if not components['question'] or len(components['options']) != 4 or not components['answer']:
                logger.debug(f"Invalid components: {components}")
                return None
            
            # Join question lines
            question_text = ' '.join(components['question']).strip()
            
            # Verify options are in order
            option_dict = {}
            for opt in components['options']:
                prefix = opt[:2]
                if prefix not in ['A.', 'B.', 'C.', 'D.']:
                    logger.warning(f"Invalid option prefix: {prefix}")
                    return None
                option_dict[prefix] = opt[2:].strip()
            
            # Check we have all options in order
            cleaned_options = []
            for prefix in ['A.', 'B.', 'C.', 'D.']:
                if prefix not in option_dict:
                    logger.warning(f"Missing option {prefix}")
                    return None
                cleaned_options.append(option_dict[prefix])
            
            # Parse answer
            answer_match = re.match(r'^ANSWER:\s*([A-D])$', components['answer'])
            if not answer_match:
                logger.warning(f"Invalid answer format: {components['answer']}")
                return None
            
            return {
                "question": question_text,
                "options": cleaned_options,
                "correct": answer_match.group(1)
            }
            
        except Exception as e:
            logger.warning(f"Error parsing question: {str(e)}")
            return None
