import anthropic
import os
import time
import json
from datetime import datetime

# Set up the client
client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

# Define prompt variations to test
PROMPT_VARIATIONS = {
    "original": """You are an information extraction assistant for Flynn construction. You are helping to analyze handover meeting transcripts. 
For each answer, do the following:
- Provide a clear and concise response
- Support it with at least two direct quotes or paraphrased pieces of evidence from the transcript
- Do not make assumptions — only use content from the transcript
- Ensure the response is grammatically correct""",
    
    "explicit_quotes": """You are an expert transcript analyst for Flynn Construction analyzing handover meetings.

REQUIREMENTS:
1. Quote EXACTLY from the transcript using this format: Speaker Name: "exact quote"
2. Include at least 2-3 direct quotes for every answer
3. If information is not in the transcript, explicitly state "This was not mentioned in the transcript"
4. Be comprehensive - include ALL relevant information discussed""",
    
    "structured": """You are a Flynn Construction analyst reviewing handover meeting transcripts.

For EVERY answer, follow this exact structure:
1. DIRECT ANSWER: [One clear sentence answering the question]
2. EVIDENCE: [2-3 exact quotes with speaker names]
3. ADDITIONAL CONTEXT: [Any other relevant information from the transcript]
4. MISSING INFO: [What was NOT discussed that might be important]""",
    
    "role_based": """You are a senior project manager at Flynn Construction preparing to take over this project. 
Your team needs clear, actionable information from this handover meeting.

When answering:
- Focus on what the construction team needs to know
- Quote speakers exactly: "Name stated: 'quote'"
- Flag any concerns or items needing follow-up
- Be thorough - your team's success depends on these details""",
    
    "evidence_first": """Analyze the Flynn Construction handover meeting transcript.

Answer format:
First, list ALL relevant quotes from the transcript about this topic.
Then, summarize what these quotes tell us.
Finally, note what information is missing or unclear.

Always use: Speaker Name: "exact quote" format."""
}

def test_single_prompt(prompt_variation, transcript, question, model="claude-3-opus-20240229"):
    """Test a single prompt variation"""
    
    user_prompt = f"""Transcript: \"\"\"{transcript}\"\"\"

Question: {question}"""
    
    start_time = time.time()
    
    try:
        response = client.messages.create(
            model=model,
            system=prompt_variation,
            max_tokens=2000,
            temperature=0.2,
            messages=[{"role": "user", "content": user_prompt}],
        )
        
        answer = response.content[0].text
        response_time = time.time() - start_time
        
        # Calculate simple metrics
        quote_count = answer.count('"')
        word_count = len(answer.split())
        has_speaker_names = any(name in answer for name in ["Frank", "Kevin", "KEL", "Dariusz"])
        
        return {
            "answer": answer,
            "metrics": {
                "response_time": round(response_time, 2),
                "quote_count": quote_count,
                "word_count": word_count,
                "char_count": len(answer),
                "has_speaker_names": has_speaker_names,
                "has_not_mentioned": "not mentioned" in answer.lower() or "not specified" in answer.lower()
            }
        }
        
    except Exception as e:
        return {
            "answer": f"Error: {str(e)}",
            "metrics": {"error": True}
        }

def run_prompt_test(transcript_path, test_questions, output_dir="prompt_tests"):
    """Run all prompt variations on test questions"""
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Load transcript
    print(f"Loading transcript from: {transcript_path}")
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = f.read()
    
    # Results storage
    all_results = {
        "test_date": datetime.now().isoformat(),
        "questions": test_questions,
        "results": {}
    }
    
    # Test each question
    for q_idx, question in enumerate(test_questions, 1):
        print(f"\n{'='*60}")
        print(f"Testing Question {q_idx}: {question}")
        print(f"{'='*60}")
        
        question_results = {}
        
        # Test each prompt variation
        for variation_name, prompt in PROMPT_VARIATIONS.items():
            print(f"\nTesting variation: {variation_name}")
            
            result = test_single_prompt(prompt, transcript, question)
            question_results[variation_name] = result
            
            # Print summary
            metrics = result["metrics"]
            print(f"  - Response time: {metrics.get('response_time', 'N/A')}s")
            print(f"  - Quotes: {metrics.get('quote_count', 0)}")
            print(f"  - Length: {metrics.get('word_count', 0)} words")
            print(f"  - Has speaker names: {metrics.get('has_speaker_names', False)}")
            
            # Save individual result
            filename = f"{output_dir}/q{q_idx}_{variation_name}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"Question: {question}\n")
                f.write(f"Prompt Variation: {variation_name}\n")
                f.write(f"Metrics: {json.dumps(metrics, indent=2)}\n")
                f.write(f"\nAnswer:\n{result['answer']}")
            
            # Rate limiting
            time.sleep(1)
        
        all_results["results"][question] = question_results
    
    # Save summary results
    summary_file = f"{output_dir}/test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    
    # Print comparison summary
    print_comparison_summary(all_results)
    
    return all_results

def print_comparison_summary(results):
    """Print a summary comparison of all prompts"""
    
    print("\n" + "="*80)
    print("PROMPT COMPARISON SUMMARY")
    print("="*80)
    
    # Calculate average metrics for each prompt variation
    variation_stats = {}
    
    for question, question_results in results["results"].items():
        for variation, result in question_results.items():
            if variation not in variation_stats:
                variation_stats[variation] = {
                    "total_quotes": 0,
                    "total_words": 0,
                    "total_time": 0,
                    "speaker_count": 0,
                    "not_mentioned_count": 0,
                    "count": 0
                }
            
            metrics = result["metrics"]
            if "error" not in metrics:
                stats = variation_stats[variation]
                stats["total_quotes"] += metrics.get("quote_count", 0)
                stats["total_words"] += metrics.get("word_count", 0)
                stats["total_time"] += metrics.get("response_time", 0)
                stats["speaker_count"] += 1 if metrics.get("has_speaker_names") else 0
                stats["not_mentioned_count"] += 1 if metrics.get("has_not_mentioned") else 0
                stats["count"] += 1
    
    # Print summary table
    print(f"\n{'Variation':<20} {'Avg Quotes':<12} {'Avg Words':<12} {'Avg Time':<10} {'Has Names':<10} {'Notes Missing':<10}")
    print("-" * 80)
    
    for variation, stats in variation_stats.items():
        if stats["count"] > 0:
            avg_quotes = stats["total_quotes"] / stats["count"]
            avg_words = stats["total_words"] / stats["count"]
            avg_time = stats["total_time"] / stats["count"]
            name_pct = (stats["speaker_count"] / stats["count"]) * 100
            missing_pct = (stats["not_mentioned_count"] / stats["count"]) * 100
            
            print(f"{variation:<20} {avg_quotes:<12.1f} {avg_words:<12.0f} {avg_time:<10.1f} {name_pct:<10.0f}% {missing_pct:<10.0f}%")

# Quick start function
def quick_test():
    """Quick test with 3 key questions"""
    
    test_questions = [
        "Who is the customer for this project and describe our past working relationship, if any?",
        "What are the underlying risks associated with performing our work on this project?",
        "What is the project construction schedule (start and expected completion) for our scope?"
    ]
    
    transcript_path = "C:\\Users\\kayla.dipaolo\\source\\repos\\AnthropicTesting\\Dillworth+phase+1+handover.txt"
    
    results = run_prompt_test(transcript_path, test_questions)
    
    # Find best performing variation
    print("\n" + "="*80)
    print("RECOMMENDATION:")
    print("="*80)
    
    # Simple scoring: quotes + speaker names + acknowledges missing info
    best_variation = None
    best_score = 0
    
    for variation in PROMPT_VARIATIONS.keys():
        score = 0
        count = 0
        for question_results in results["results"].values():
            if variation in question_results:
                metrics = question_results[variation]["metrics"]
                if "error" not in metrics:
                    score += metrics.get("quote_count", 0) * 0.3  # Quotes are important
                    score += 10 if metrics.get("has_speaker_names") else 0
                    score += 5 if metrics.get("has_not_mentioned") else 0
                    count += 1
        
        avg_score = score / count if count > 0 else 0
        if avg_score > best_score:
            best_score = avg_score
            best_variation = variation
    
    print(f"\nBest performing prompt: '{best_variation}' (score: {best_score:.1f})")
    print("\nCheck the 'prompt_tests' folder for detailed results!")

if __name__ == "__main__":
    quick_test()