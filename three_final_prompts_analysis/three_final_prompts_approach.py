import os
import openai
import time
import json
import re
from datetime import datetime
from collections import Counter
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Final prompt structures for OpenAI
OPENAI_FINAL_PROMPTS = {
    "professional_synthesis": """You are a senior PM at Flynn Construction analyzing this handover transcript:

{transcript}

For the question below, provide a professional analysis that:
1. Synthesizes findings into clear statements (not just listing quotes)
2. Supports each finding with evidence: "Speaker: 'exact quote'"
3. Concludes with specific items requiring clarification if applicable

Write naturally - combine related points and explain implications where helpful.

Question: {question}
Answer:""",

    "structured_professional": """Flynn Construction Handover Analysis:

{transcript}

Analyze the above transcript and answer the following question with:
- Clear synthesis of what was discussed (with context)
- Supporting quotes: "Speaker: 'exact quote'" integrated naturally
- Brief "Items requiring clarification:" section if gaps exist

Question: {question}
Answer:""",

    "enhanced_final": """As a senior project manager at Flynn Construction, analyze this handover transcript:

{transcript}

Provide a comprehensive answer that construction teams can act on:
- Present findings as clear paragraphs explaining what was determined
- Support key points with quotes: "Speaker: 'exact quote'"
- For complex topics, explain implications briefly
- End with "Items requiring clarification with [relevant party]:" if needed

Keep the tone professional and avoid over-explaining basic concepts.

Question: {question}
Answer:"""
}

def extract_speakers(transcript: str) -> list:
    """Extract confirmed speakers from transcript"""
    speaker_pattern = r'^([A-Za-z][A-Za-z\s\-\(\)]+?)(?:\s*-\s*\d{1,2}:\d{2})'
    potential_speakers = []
    
    for line in transcript.split('\n'):
        line = line.strip()
        if line:
            match = re.match(speaker_pattern, line)
            if match:
                speaker = match.group(1).strip()
                if 2 < len(speaker) < 50:
                    potential_speakers.append(speaker)
    
    speaker_counts = Counter(potential_speakers)
    confirmed_speakers = [s for s, count in speaker_counts.items() if count >= 3]
    
    return confirmed_speakers[:10] if len(confirmed_speakers) > 10 else confirmed_speakers

def evaluate_openai_answer(answer: str, question: str, expected_elements: dict = None) -> dict:
    """Evaluate the quality of OpenAI's answer"""
    
    metrics = {
        # Basic counts
        "char_count": len(answer),
        "word_count": len(answer.split()),
        "paragraph_count": len([p for p in answer.split('\n\n') if p.strip()]),
        "quote_count": len(re.findall(r'"[^"]+?"', answer)),
        
        # Quality indicators
        "has_synthesis": False,  # Check if it's more than just quotes
        "has_context_before_quotes": False,
        "has_clarification_section": False,
        "has_speaker_attribution": False,
        "professional_language": False
    }
    
    # Check for synthesis (paragraphs with both explanation and quotes)
    paragraphs = [p for p in answer.split('\n\n') if p.strip()]
    synthesis_paragraphs = 0
    for para in paragraphs:
        if len(para) > 100 and '"' in para:  # Has both content and quotes
            synthesis_paragraphs += 1
    
    metrics["has_synthesis"] = synthesis_paragraphs >= 1
    metrics["synthesis_score"] = synthesis_paragraphs / max(len(paragraphs), 1)
    
    # Check for context before quotes
    first_quote = answer.find('"')
    metrics["has_context_before_quotes"] = first_quote > 50 if first_quote > -1 else True
    
    # Check for clarification section
    clarification_keywords = ["requiring clarification", "items requiring", "need to confirm", 
                             "follow up with", "clarify with"]
    metrics["has_clarification_section"] = any(kw in answer.lower() for kw in clarification_keywords)
    
    # Check for speaker attribution
    attribution_patterns = [r'\b\w+\s+(?:stated|mentioned|noted|confirmed|said):', 
                           r'"[^"]+?".*?-\s*\w+']
    metrics["has_speaker_attribution"] = any(re.search(p, answer) for p in attribution_patterns)
    
    # Check professional language (avoiding overly simple explanations)
    simple_phrases = ["this means that", "in other words", "basically", "simply put"]
    metrics["professional_language"] = not any(phrase in answer.lower() for phrase in simple_phrases)
    
    # Completeness check if expected elements provided
    if expected_elements and question in expected_elements:
        found = sum(1 for elem in expected_elements[question] if elem.lower() in answer.lower())
        metrics["completeness_score"] = found / len(expected_elements[question])
    else:
        metrics["completeness_score"] = None
    
    # Overall quality score
    quality_components = [
        metrics["has_synthesis"] * 0.3,
        metrics["has_context_before_quotes"] * 0.2,
        metrics["has_speaker_attribution"] * 0.2,
        metrics["professional_language"] * 0.1,
        metrics["has_clarification_section"] * 0.1 if "?" in question else 0,
        min(metrics["quote_count"] / 3, 1) * 0.1  # Normalize quote count
    ]
    
    metrics["quality_score"] = sum(quality_components)
    
    return metrics

def test_openai_prompts(transcript_path: str, test_questions: list, model_name: str):
    """Test all prompt variations and compare"""
    
    print("TESTING FINAL OPENAI PROMPT STRUCTURES")
    print("=" * 80)
    
    # Load transcript
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = f.read().strip()
    
    # Extract speakers for reference
    speakers = extract_speakers(transcript)
    print(f"Detected {len(speakers)} speakers in transcript")
    
    results = {}
    
    for question in test_questions:
        print(f"\n\nTESTING: {question}")
        print("-" * 80)
        
        question_results = {}
        
        for prompt_name, prompt_template in OPENAI_FINAL_PROMPTS.items():
            print(f"\n{prompt_name}:")
            
            prompt = prompt_template.format(transcript=transcript, question=question)
            
            try:
                start_time = time.time()
                
                response = openai.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2500,
                    temperature=0.4,
                )
                
                answer = response.choices[0].message.content.strip()
                response_time = time.time() - start_time
                
                # Evaluate answer
                metrics = evaluate_openai_answer(answer, question)
                metrics["response_time"] = round(response_time, 2)
                
                # Store results
                question_results[prompt_name] = {
                    "answer": answer,
                    "metrics": metrics
                }
                
                # Display summary
                print(f"  Quality Score: {metrics['quality_score']:.2f}")
                print(f"  Synthesis: {'✓' if metrics['has_synthesis'] else '✗'}")
                print(f"  Context before quotes: {'✓' if metrics['has_context_before_quotes'] else '✗'}")
                print(f"  Professional: {'✓' if metrics['professional_language'] else '✗'}")
                print(f"  Has clarifications: {'✓' if metrics['has_clarification_section'] else '✗'}")
                
                # Show preview
                print(f"\n  Preview: {answer[:200]}...")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"  Error: {str(e)}")
                question_results[prompt_name] = {"error": str(e)}
        
        results[question] = question_results
    
    return results

def select_best_prompt(results: dict) -> str:
    """Analyze results and recommend best prompt"""
    
    print("\n\n" + "="*80)
    print("PROMPT COMPARISON SUMMARY")
    print("="*80)
    
    prompt_scores = {}
    
    for prompt_name in OPENAI_FINAL_PROMPTS.keys():
        scores = []
        for question_results in results.values():
            if prompt_name in question_results and "metrics" in question_results[prompt_name]:
                scores.append(question_results[prompt_name]["metrics"]["quality_score"])
        
        if scores:
            avg_score = sum(scores) / len(scores)
            prompt_scores[prompt_name] = avg_score
            print(f"\n{prompt_name}:")
            print(f"  Average Quality Score: {avg_score:.2f}")
    
    best_prompt = max(prompt_scores, key=prompt_scores.get)
    print(f"\n✅ RECOMMENDED: {best_prompt}")
    
    return best_prompt

def run_final_analysis(transcript_path: str, questions_path: str, model_name: str, prompt_name: str):
    """Run the selected prompt on all questions"""
    
    print(f"\nRUNNING FULL ANALYSIS WITH: {prompt_name}")
    print("="*80)
    
    # Load files
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = f.read().strip()
    
    with open(questions_path, "r", encoding="utf-8") as f:
        questions = [line.strip() for line in f if line.strip()]
    
    prompt_template = OPENAI_FINAL_PROMPTS[prompt_name]
    
    # Output setup
    output_dir = "three_final_prompts_analysis"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"{output_dir}/final_analysis_{timestamp}.txt"
    metrics_file = f"{output_dir}/metrics_{timestamp}.json"
    
    all_results = []
    all_metrics = []
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("FLYNN CONSTRUCTION - OPENAI ANALYSIS\n")
        f.write(f"Model: {model_name}\n")
        f.write(f"Prompt: {prompt_name}\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("="*80 + "\n\n")
        
        for idx, question in enumerate(questions, 1):
            print(f"\rProcessing {idx}/{len(questions)}...", end="")
            
            prompt = prompt_template.format(transcript=transcript, question=question)
            
            try:
                response = openai.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2500,
                    temperature=0.4,
                )
                
                answer = response.choices[0].message.content.strip()
                metrics = evaluate_openai_answer(answer, question)
                
                # Write to file
                f.write(f"{idx}. {question}\n\n")
                f.write(f"{answer}\n\n")
                f.write("-"*80 + "\n\n")
                
                all_results.append({"question": question, "answer": answer})
                all_metrics.append({"question": question, "metrics": metrics})
                
                time.sleep(0.5)
                
            except Exception as e:
                print(f"\nError on question {idx}: {str(e)}")
                f.write(f"ERROR: {str(e)}\n\n")
    
    # Save metrics
    with open(metrics_file, "w") as f:
        json.dump({
            "prompt_used": prompt_name,
            "model": model_name,
            "timestamp": timestamp,
            "metrics": all_metrics
        }, f, indent=2)
    
    print(f"\n\n✅ Analysis complete!")
    print(f"   Results: {output_file}")
    print(f"   Metrics: {metrics_file}")
    
    # Show summary stats
    avg_quality = sum(m["metrics"]["quality_score"] for m in all_metrics) / len(all_metrics)
    print(f"\nAverage Quality Score: {avg_quality:.2f}")

def main():
    """Main function to run the complete OpenAI testing"""
    
    # Configuration
    transcript_path = "C:\\Users\\kayla.dipaolo\\source\\repos\\openAITesting\\Dillworth+phase+1+handover.txt"
    questions_path = "C:\\Users\\kayla.dipaolo\\source\\repos\\openAITesting\\Handoff Questions.txt"
    model_name = "ft:gpt-4o-2024-08-06:flynn:test-nine:BcuSbEPv"
    
    # Test questions for prompt selection
    test_questions = [
        "What are the underlying risks associated with performing our work on this project?",
        "Who is the customer for this project and describe our past working relationship, if any?",
        "What are the payment terms?",
        "Do we need to bring any alternates to the attention of the client/customer before starting?"
    ]
    
    # Step 1: Test all prompts
    print("Step 1: Testing prompt variations...")
    results = test_openai_prompts(transcript_path, test_questions, model_name)
    
    # Step 2: Select best prompt
    print("\nStep 2: Selecting best prompt...")
    best_prompt = select_best_prompt(results)
    
    # Step 3: Ask user confirmation
    print(f"\nProceed with full analysis using '{best_prompt}'? (y/n)")
    print("Auto-proceeding in 5 seconds...")
    time.sleep(5)
    
    # Step 4: Run full analysis
    run_final_analysis(transcript_path, questions_path, model_name, best_prompt)

if __name__ == "__main__":
    main()