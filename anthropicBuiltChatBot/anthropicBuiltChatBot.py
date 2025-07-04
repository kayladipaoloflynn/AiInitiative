import anthropic
import os
import re
from typing import List, Tuple, Optional
import time
from collections import Counter

# 👉 Step 1: Set your Claude API key
client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")  # CHANGE THIS if needed
)

# Enhanced system prompt that emphasizes evidence-based answers
system_prompt = """You are an expert transcript analyst for Flynn Construction, specializing in analyzing construction project handover meetings.

Your analysis approach:
1. Read the ENTIRE transcript carefully before answering each question
2. ALWAYS provide direct quotes from the transcript to support your statements
3. Include speaker names with ALL quotes (e.g., "Frank Jonathan stated: 'quote here'")
4. When multiple people discuss the same topic, include all relevant perspectives
5. If information is not explicitly stated in the transcript, clearly indicate this
6. Distinguish between what is directly stated vs. what can be inferred
7. For yes/no questions, provide the answer first, then the supporting evidence
8. Include ALL relevant details that would help someone preparing for this project
9. Structure longer answers with clear sections or numbered points
10. Note any items that need clarification or confirmation with the customer

Your goal is to provide comprehensive, actionable information that project teams can use for planning and execution."""

def create_enhanced_prompt(transcript: str, question: str) -> str:
    """Create an enhanced prompt that encourages comprehensive answers"""
    return f"""Analyze the following construction handover meeting transcript to answer the question below.

TRANSCRIPT:
\"\"\"{transcript}\"\"\"

QUESTION: {question}

INSTRUCTIONS:
- Quote DIRECTLY from the transcript with speaker names (e.g., "KEL-WoodLake-BR(10)(VC) stated: 'exact quote'")
- Include ALL relevant information discussed, even if mentioned briefly
- If multiple speakers discuss this topic, include all perspectives
- If the answer is not explicitly in the transcript, state what information is missing
- For lists or multiple items, use numbered points or bullet points
- Include any caveats, conditions, or items requiring confirmation
- Provide context for quotes when necessary for clarity

Provide a comprehensive answer that someone unfamiliar with the project could understand and act upon.

ANSWER:"""

def extract_speakers(transcript: str) -> List[str]:
    """Extract unique speaker names from the transcript with better filtering"""
    
    # Pattern to match speaker names followed by timestamp
    # This assumes format like: "Speaker Name - HH:MM" or "Speaker Name - H:MM"
    speaker_pattern = r'^([A-Za-z][A-Za-z\s\-\(\)]+?)(?:\s*-\s*\d{1,2}:\d{2})'
    
    potential_speakers = []
    
    for line in transcript.split('\n'):
        line = line.strip()
        if line:
            match = re.match(speaker_pattern, line)
            if match:
                speaker = match.group(1).strip()
                # Filter out likely false positives
                if (2 < len(speaker) < 50 and  # Reasonable length
                    not speaker.isupper() and  # Not all caps (likely a section header)
                    speaker.count(' ') < 5):    # Not too many spaces (likely not a sentence)
                    potential_speakers.append(speaker)
    
    # Count occurrences and filter out rare mentions (likely false positives)
    speaker_counts = Counter(potential_speakers)
    
    # Only keep speakers who appear at least 3 times
    confirmed_speakers = [
        speaker for speaker, count in speaker_counts.items() 
        if count >= 3
    ]
    
    # If we still have too many, take the top 10 most frequent
    if len(confirmed_speakers) > 10:
        confirmed_speakers = [
            speaker for speaker, _ in speaker_counts.most_common(10)
        ]
    
    print(f"\nSpeaker frequency analysis (top 10):")
    for speaker, count in speaker_counts.most_common(10):
        print(f"  {speaker}: {count} times")
    
    return confirmed_speakers

def analyze_transcript_format(transcript: str) -> None:
    """Debug function to understand the transcript format"""
    print("\nTRANSCRIPT FORMAT ANALYSIS")
    print("=" * 50)
    
    lines = transcript.split('\n')[:30]  # First 30 lines
    
    print("First few lines that might be speakers:")
    for i, line in enumerate(lines):
        line = line.strip()
        if line and (
            # Has timestamp pattern
            re.search(r'\d{1,2}:\d{2}', line) or 
            # Has colon near the beginning
            (':' in line[:50] and line.index(':') < 50) or
            # Starts with capital letter and has dash
            (line and line[0].isupper() and '-' in line[:50])
        ):
            print(f"Line {i}: {line[:100]}...")
    
    print("=" * 50)

def validate_answer(answer: str, speakers: List[str]) -> dict:
    """Validate answer quality with better speaker detection"""
    
    # Basic validation
    validation = {
        "has_quotes": '"' in answer,
        "quote_count": len(re.findall(r'"[^"]+?"', answer)),
        "length": len(answer),
        "detected_speakers": len(speakers)
    }
    
    # Check for speaker attribution more flexibly
    # Look for common patterns like "stated:", "mentioned:", "said:", etc.
    attribution_patterns = [
        r'\b(?:stated|mentioned|said|responded|confirmed|noted|explained|asked|answered)\b',
        r'\b(?:According to|As|When asked)\b',
        r'\b(?:from the transcript|in the transcript)\b'
    ]
    
    has_attribution = any(re.search(pattern, answer, re.IGNORECASE) for pattern in attribution_patterns)
    
    # Also check if any detected speakers are mentioned
    has_speaker_name = any(speaker in answer for speaker in speakers) if speakers else False
    
    validation["has_speaker_attribution"] = has_attribution or has_speaker_name
    
    # Check for uncertainty acknowledgment
    validation["has_uncertainty_acknowledgment"] = any(
        phrase in answer.lower() for phrase in 
        ["not mentioned", "not specified", "unclear", "need to confirm", 
         "not explicitly", "does not appear", "no information"]
    )
    
    # Check structure
    validation["is_structured"] = bool(re.search(r'^\d+\.|^[-•]|^[A-Z][^.]+:', answer, re.MULTILINE))
    
    # Calculate quality score with adjusted criteria
    quality_factors = [
        validation["has_quotes"],
        validation["quote_count"] >= 2,
        validation["has_speaker_attribution"],  # Now more flexible
        validation["length"] > 200
    ]
    
    validation["quality_score"] = sum(quality_factors) / len(quality_factors)
    
    return validation

def post_process_answer(answer: str) -> str:
    """Clean up and format the answer for better readability"""
    # Fix quote formatting
    answer = re.sub(r'"\s+', '"', answer)
    answer = re.sub(r'\s+"', '"', answer)
    
    # Ensure proper spacing after periods
    answer = re.sub(r'\.(?=[A-Z])', '. ', answer)
    
    return answer.strip()

def main():
    # Load transcript
    transcript_path = "C:\\Users\\kayla.dipaolo\\source\\repos\\AnthropicTesting\\Dillworth+phase+1+handover.txt"
    questions_path = "C:\\Users\\kayla.dipaolo\\source\\repos\\AnthropicTesting\\Handoff Questions.txt"
    output_path = "C:\\Users\\kayla.dipaolo\\source\\repos\\AnthropicTesting\\outputAnswersAnthropicImproved.txt"
    
    print(f"Loading transcript from: {transcript_path}")
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript_content = f.read()
    
    # Debug: Analyze transcript format first
    print("\nAnalyzing transcript format to identify speakers...")
    analyze_transcript_format(transcript_content)
    
    # Extract speakers for validation
    speakers = extract_speakers(transcript_content)
    print(f"\nConfirmed {len(speakers)} speakers in transcript:")
    for speaker in speakers:
        print(f"  - {speaker}")
    
    # Load questions
    print(f"\nLoading questions from: {questions_path}")
    with open(questions_path, "r", encoding="utf-8") as f:
        questions = [q.strip() for q in f.readlines() if q.strip()]
    print(f"Loaded {len(questions)} questions")
    
    # Output collection
    answers = []
    quality_scores = []
    
    # Process each question
    for idx, question in enumerate(questions, start=1):
        print(f"\nProcessing Question {idx}/{len(questions)}: {question[:60]}...")
        
        # Create enhanced prompt
        user_prompt = create_enhanced_prompt(transcript_content, question)
        
        try:
            # API call with optimized parameters
            response = client.messages.create(
                model="claude-3-opus-20240229",  # Use claude-3-sonnet-20240229 for cost savings
                system=system_prompt,
                max_tokens=2000,  # Reduced from 2500 for efficiency
                temperature=0.2,   # Lower temperature for more consistent, factual responses
                messages=[{"role": "user", "content": user_prompt}],
            )
            
            answer_text = response.content[0].text
            answer_text = post_process_answer(answer_text)
            
            # Validate answer quality
            validation = validate_answer(answer_text, speakers)
            quality_scores.append(validation["quality_score"])
            
            print(f"  ✓ Answer generated (Quality score: {validation['quality_score']:.2f})")
            print(f"    - Quotes: {validation['quote_count']}")
            print(f"    - Length: {validation['length']} chars")
            print(f"    - Has attribution: {validation['has_speaker_attribution']}")
            
            answers.append((question, answer_text))
            
            # Rate limiting
            time.sleep(1)  # Adjust based on your API rate limits
            
        except Exception as e:
            print(f"  ✗ Error processing question: {str(e)}")
            answers.append((question, f"Error: Could not process this question. {str(e)}"))
    
    # Save results with quality report
    print(f"\nSaving results to: {output_path}")
    with open(output_path, "w", encoding="utf-8") as f:
        # Write summary header
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        f.write(f"TRANSCRIPT ANALYSIS REPORT\n")
        f.write(f"Total Questions: {len(questions)}\n")
        f.write(f"Average Quality Score: {avg_quality:.2f}\n")
        f.write(f"Speakers Identified: {len(speakers)}\n")
        f.write(f"Generated by: Improved Flynn Construction Analyzer\n")
        f.write(f"{'='*80}\n\n")
        
        # Write each Q&A
        for question, answer in answers:
            f.write(f"Q: {question}\n")
            f.write(f"A: {answer}\n")
            f.write(f"\n{'='*80}\n\n")
    
    print(f"\n✅ Analysis complete! Results saved to: {output_path}")
    print(f"Average answer quality score: {avg_quality:.2f}")
    print(f"Total speakers identified: {len(speakers)}")

# Additional utility function for batch processing with better error handling
def analyze_with_retry(client, system_prompt: str, user_prompt: str, max_retries: int = 3) -> Optional[str]:
    """Analyze with retry logic for robustness"""
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-3-opus-20240229",
                system=system_prompt,
                max_tokens=2000,
                temperature=0.2,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return post_process_answer(response.content[0].text)
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"    Retry {attempt + 1}/{max_retries} after error: {str(e)}")
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise e
    return None

# Test function to debug speaker extraction
def test_speaker_extraction(transcript_path: str):
    """Test the speaker extraction to debug issues"""
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = f.read()
    
    print("TESTING SPEAKER EXTRACTION")
    print("=" * 60)
    
    # First analyze format
    analyze_transcript_format(transcript)
    
    # Extract speakers
    print("\nExtracting speakers with frequency filtering:")
    speakers = extract_speakers(transcript)
    print(f"\nFound {len(speakers)} confirmed speakers: {speakers}")
    
    return speakers

if __name__ == "__main__":
    main()