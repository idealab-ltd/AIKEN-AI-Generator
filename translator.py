"""
Module for translating questions to Italian.
"""
from deep_translator import GoogleTranslator
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class QuestionTranslator:
    def __init__(self):
        """Initialize the translator with Italian as target language."""
        self.translator = GoogleTranslator(source='en', target='it')
        
    def translate_question(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate a single question and its options to Italian.
        
        Args:
            question (Dict[str, Any]): Question dictionary with text and options
            
        Returns:
            Dict[str, Any]: Translated question dictionary
        """
        try:
            translated = {
                "question": self.translator.translate(question["question"]),
                "options": [
                    self.translator.translate(option)
                    for option in question["options"]
                ],
                "correct": question["correct"]  # Keep the same letter
            }
            return translated
            
        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            return question  # Return original if translation fails
            
    def translate_batch(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Translate a batch of questions to Italian.
        
        Args:
            questions (List[Dict[str, Any]]): List of question dictionaries
            
        Returns:
            List[Dict[str, Any]]: List of translated question dictionaries
        """
        translated_questions = []
        total = len(questions)
        
        for i, question in enumerate(questions):
            if i % 10 == 0:
                logger.info(f"Translating question {i+1}/{total}")
            translated = self.translate_question(question)
            translated_questions.append(translated)
            
        return translated_questions
