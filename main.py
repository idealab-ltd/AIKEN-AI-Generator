"""
Main script for extracting and translating questions from PDF.
"""
import argparse
import logging
import os
from pdf_extractor import PDFExtractor
from question_generator import QuestionGenerator
from translator import QuestionTranslator
from utils import save_questions

def format_question(q):
    """Format a question dictionary for display."""
    output = [
        f"\n{q['question']}",
        *[f"{chr(65+i)}. {opt}" for i, opt in enumerate(q['options'])],
        f"ANSWER: {q['correct']}\n"
    ]
    return '\n'.join(output)

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Extract and translate questions from PDF')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('--output', '-o', default='questions.txt',
                      help='Output file path (default: questions.txt)')
    parser.add_argument('--chunk-size', '-c', type=int, default=4000,
                      help='Size of text chunks to process (default: 4000)')
    parser.add_argument('--overlap', '-v', type=int, default=500,
                      help='Overlap between chunks (default: 500)')
    parser.add_argument('--debug', '-d', action='store_true',
                      help='Enable debug logging')
    parser.add_argument('--show-questions', '-s', action='store_true',
                      help='Show questions as they are generated')
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    try:
        # Extract text from PDF
        logger.info("Extracting text from PDF...")
        extractor = PDFExtractor(args.pdf_path)
        text_chunks = extractor.extract_text()
        
        # Filter out very small chunks
        text_chunks = [chunk for chunk in text_chunks if len(chunk.strip()) >= 500]
        logger.info(f"Extracted {len(text_chunks)} valid text chunks")

        # Generate questions
        logger.info("Generating questions...")
        generator = QuestionGenerator()
        all_questions = []
        total_questions = 0
        total_chunks = len(text_chunks)
        
        for i, chunk in enumerate(text_chunks):
            logger.info(f"Processing chunk {i+1}/{total_chunks} ({len(chunk)} chars)")
            
            # Look for article markers in the chunk
            article_count = chunk.count("Art.") + chunk.count("Articolo")
            logger.debug(f"Chunk {i+1} contains {article_count} article references")
            
            chunk_questions = generator.generate_questions(chunk)
            total_questions += len(chunk_questions)
            if chunk_questions:
                all_questions.extend(chunk_questions)
                logger.info(f"Generated {len(chunk_questions)} questions from chunk {i+1}")
                
                # Display questions if requested
                if args.show_questions and chunk_questions:
                    for q in chunk_questions:
                        print(f"\n{q['question']}")
                        for i, opt in enumerate(q['options']):
                            print(f"{chr(65+i)}. {opt}")
                        print(f"ANSWER: {q['correct']}\n")
            else:
                logger.debug(f"No questions generated from chunk {i+1}")

            # Save progress periodically
            if (i + 1) % 10 == 0:
                logger.info(f"Progress: {i+1}/{len(text_chunks)} chunks processed")
                logger.info(f"Total questions so far: {len(all_questions)}")

        logger.info(f"Total questions generated: {len(all_questions)}")
        logger.info(f"\nProcessing complete:")
        logger.info(f"Total chunks processed: {total_chunks}")
        logger.info(f"Total valid questions generated: {total_questions}")
        logger.info(f"Average questions per chunk: {total_questions/total_chunks:.2f}")

        # Translate questions
        if all_questions:
            logger.info("Translating questions to Italian...")
            translator = QuestionTranslator()
            translated_questions = translator.translate_batch(all_questions)
            
            # Show translated questions if requested
            if args.show_questions:
                print("\n\033[94m=== Translated Questions ===\033[0m")  # Print header in blue
                for q in translated_questions:
                    print("\033[94m" + format_question(q) + "\033[0m")  # Print in blue

            # Save results
            logger.info(f"Saving {len(translated_questions)} questions to {args.output}")
            save_questions(translated_questions, args.output)
            logger.info(f"Questions have been saved to {args.output}")
        else:
            logger.warning("No questions were generated from the text")

        logger.info("Process completed successfully!")

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main()
