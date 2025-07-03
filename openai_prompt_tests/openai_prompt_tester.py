import os
import openai
import time
import json
from datetime import datetime
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Define prompt variations to test with your fine-tuned model
PROMPT_VARIATIONS = {
    "original": """Here is a construction-handover transcript:

{transcript}

Using only the information above, answer the following question clearly using quotes from the transcript to support your answers:
Q: {question}
A:""",
    
    "explicit_quotes": """Construction Handover Transcript:

{transcript}

INSTRUCTIONS: Answer the question using EXACT quotes from the transcript. Use format: Speaker Name: "exact quote"
Include 2-3 direct quotes. If information is not in the transcript, state "This was not mentioned in the transcript"

Question: {question}
Answer:""",
    
    "structured": """TRANSCRIPT:
{transcript}

Answer the following question using this EXACT structure:
1. DIRECT ANSWER: [One clear sentence]
2. EVIDENCE: [2-3 exact quotes with speaker names]  
3. ADDITIONAL CONTEXT: [Other relevant info]
4. MISSING INFO: [What was NOT discussed]

Question: {question}
Answer:""",
    
    "role_based": """You are reviewing this Flynn Construction handover meeting transcript:

{transcript}

As a senior project manager, provide clear, actionable information the construction team needs.
- Quote speakers exactly: "Name: 'quote'"
- Flag any concerns or follow-up items
- Be thorough - the team's success depends on these details

Question: {question}
Answer:""",
    
    "minimal": """{transcript}

Q: {question}
A:"""
}

def test_single_prompt_openai(prompt_template, transcript, question, model_name):
    """Test a single prompt variation with OpenAI"""
    
    # Format the prompt
    prompt = prompt_template.format(transcript=transcript, question=question)
    
    start_time = time.time()
    
    try:
        response = openai.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500,
            temperature=0.4,
        )
        
        answer = response.choices[0].message.content.strip()
        response_time = time.time() - start_time
        
        # Calculate simple metrics for comparison
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

def run_openai_prompt_test(transcript_path, test_questions, model_name, output_dir="openai_prompt_tests"):
    """Run all prompt variations on test questions"""
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Load transcript
    print(f"Loading transcript from: {transcript_path}")
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = f.read().strip()
    
    # Results storage
    all_results = {
        "test_date": datetime.now().isoformat(),
        "model": model_name,
        "questions": test_questions,
        "results": {}
    }
    
    # Test each question
    for q_idx, question in enumerate(test_questions, start=1):
        print(f"\n{'='*60}")
        print(f"Testing Question {q_idx}: {question}")
        print(f"{'='*60}")
        
        question_results = {}
        
        # Test each prompt variation
        for variation_name, prompt_template in PROMPT_VARIATIONS.items():
            print(f"\nTesting variation: {variation_name}")
            
            result = test_single_prompt_openai(prompt_template, transcript, question, model_name)
            question_results[variation_name] = result
            
            # Print summary
            metrics = result["metrics"]
            if "error" not in metrics:
                print(f"  - Response time: {metrics['response_time']}s")
                print(f"  - Quotes: {metrics['quote_count']}")
                print(f"  - Length: {metrics['word_count']} words")
                print(f"  - Has speaker names: {metrics['has_speaker_names']}")
            else:
                print(f"  - Error occurred")
            
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
    print("OPENAI PROMPT COMPARISON SUMMARY")
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

def quick_test():
    """Quick test with 3 key questions"""
    
    test_questions = [
        "Who is the customer for this project and describe our past working relationship, if any?",
        "What are the underlying risks associated with performing our work on this project?",
        "What is the project construction schedule (start and expected completion) for our scope?"
    ]
    
    transcript_path = "C:\\Users\\kayla.dipaolo\\source\\repos\\openAITesting\\Dillworth+phase+1+handover.txt"
    model_name = "ft:gpt-4o-2024-08-06:flynn:test-nine:BcuSbEPv"
    
    results = run_openai_prompt_test(transcript_path, test_questions, model_name)
    
    # Find best performing variation
    print("\n" + "="*80)
    print("RECOMMENDATION:")
    print("="*80)
    
    # Simple scoring based on quotes and speaker names
    best_variation = None
    best_score = 0
    
    for variation in PROMPT_VARIATIONS.keys():
        score = 0
        count = 0
        for question_results in results["results"].values():
            if variation in question_results:
                metrics = question_results[variation]["metrics"]
                if "error" not in metrics:
                    score += metrics.get("quote_count", 0) * 0.3
                    score += 10 if metrics.get("has_speaker_names") else 0
                    score += 5 if metrics.get("has_not_mentioned") else 0
                    count += 1
        
        avg_score = score / count if count > 0 else 0
        if avg_score > best_score:
            best_score = avg_score
            best_variation = variation
    
    print(f"\nBest performing prompt variation: '{best_variation}' (score: {best_score:.1f})")
    print("\nCheck the 'openai_prompt_tests' folder for detailed results!")
    print("\nNOTE: Since this is a fine-tuned model, it may respond well to simpler prompts")
    print("      compared to base models. Review the actual answers to confirm!")

if __name__ == "__main__":
    quick_test()