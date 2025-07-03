import os
import time
import json
from datetime import datetime
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Define the two prompting approaches
PROMPT_VARIATIONS = {
    "structured": """### TASK: Construction Handover Transcript Analysis

**CONTEXT:**
You are analyzing a construction project handover transcript to extract specific information.

**TRANSCRIPT:**
{transcript}

**QUESTION:**
{question}

**REQUIRED RESPONSE FORMAT:**

#### 1. RELEVANT QUOTES
[List all direct quotes from the transcript that relate to the question]

#### 2. ANALYSIS
[Analyze what these quotes tell us about the question]

#### 3. GAPS OR MISSING INFORMATION
[Identify any information that would be helpful but is not in the transcript]

#### 4. FINAL ANSWER
[Provide a clear, comprehensive answer to the question based solely on the transcript]

**INSTRUCTIONS:**
- Use ONLY information from the transcript
- Include exact quotes with quotation marks
- If information is not available, clearly state "Not mentioned in the transcript"
- Be specific and thorough
- Organize your response using the format above

**RESPONSE:**""",
    
    "role_based": """You are an expert construction project manager specializing in handover documentation analysis. You have 20+ years of experience in construction management and are known for your attention to detail and ability to extract critical information from handover transcripts.

As a senior construction project manager, please analyze the following handover transcript and answer the question below. Use your expertise to identify relevant information and provide a comprehensive answer.

HANDOVER TRANSCRIPT:
{transcript}

QUESTION: {question}

Please provide:
1. Direct quotes from the transcript that answer the question
2. Your expert interpretation of this information
3. A professional summary that fully addresses the question

Answer:"""
}

def test_single_prompt(prompt_template, transcript, question, model_name):
    """Test a single prompt variation"""
    
    # Format the prompt
    prompt = prompt_template.format(transcript=transcript, question=question)
    
    start_time = time.time()
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=3000,
            # temperature removed - o4-mini only supports default
        )
        
        answer = response.choices[0].message.content.strip()
        response_time = time.time() - start_time
        
        # Analyze the answer
        metrics = {
            "response_time": round(response_time, 2),
            "quote_count": answer.count('"'),
            "word_count": len(answer.split()),
            "char_count": len(answer),
            "has_speaker_names": any(name in answer for name in ["Frank", "Kevin", "KEL", "Dariusz"]),
            "has_sections": any(section in answer for section in ["RELEVANT QUOTES", "ANALYSIS", "GAPS", "FINAL ANSWER", "Direct quotes", "interpretation", "summary"]),
            "has_not_mentioned": "not mentioned" in answer.lower() or "not specified" in answer.lower() or "not discussed" in answer.lower(),
            "has_missing_info": "missing" in answer.lower() or "gap" in answer.lower() or "need" in answer.lower()
        }
        
        return {
            "answer": answer,
            "metrics": metrics
        }
        
    except Exception as e:
        return {
            "answer": f"Error: {str(e)}",
            "metrics": {"error": True}
        }

def run_comparison_test(transcript_path, questions_path, model_name, output_dir="ReinforcementFineTuningPromptComparison"):
    """Run comparison test between structured and role-based prompts"""
    
    # Create output directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = f"{output_dir}_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Load inputs
    print(f"Loading transcript from: {transcript_path}")
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = f.read().strip()
    
    print(f"Loading questions from: {questions_path}")
    with open(questions_path, "r", encoding="utf-8") as f:
        questions = [line.strip() for line in f if line.strip()]
    
    print(f"Total questions to test: {len(questions)}")
    
    # Results storage
    all_results = {
        "test_date": timestamp,
        "model": model_name,
        "total_questions": len(questions),
        "results": {}
    }
    
    comparison_data = []
    
    # Test each question
    for q_idx, question in enumerate(questions, 1):
        print(f"\n{'='*80}")
        print(f"Testing Question {q_idx}/{len(questions)}: {question[:60]}...")
        print(f"{'='*80}")
        
        question_comparison = {
            "question_num": q_idx,
            "question": question,
            "answers": {}
        }
        
        # Test each prompt variation
        for variation_name, prompt_template in PROMPT_VARIATIONS.items():
            print(f"\n{variation_name.upper().replace('_', ' ')}:")
            
            # Get the answer
            result = test_single_prompt(prompt_template, transcript, question, model_name)
            
            answer = result["answer"]
            metrics = result["metrics"]
            
            # Store results
            question_comparison["answers"][variation_name] = {
                "answer": answer,
                "metrics": metrics
            }
            
            # Display preview and metrics
            print("\nAnswer Preview:")
            print(answer[:400] + "..." if len(answer) > 400 else answer)
            
            print(f"\nMetrics:")
            print(f"  - Response time: {metrics.get('response_time', 0)}s")
            print(f"  - Quotes: {metrics.get('quote_count', 0)}")
            print(f"  - Length: {metrics.get('word_count', 0)} words")
            print(f"  - Has speaker names: {metrics.get('has_speaker_names', False)}")
            print(f"  - Has structure/sections: {metrics.get('has_sections', False)}")
            print(f"  - Identifies gaps: {metrics.get('has_missing_info', False)}")
            
            # Save individual response
            filename = f"{output_dir}/q{q_idx:02d}_{variation_name}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"Question {q_idx}: {question}\n")
                f.write(f"Prompt Type: {variation_name}\n")
                f.write(f"Model: {model_name}\n")
                f.write(f"Metrics: {json.dumps(metrics, indent=2)}\n")
                f.write(f"\nFull Answer:\n{'='*60}\n")
                f.write(answer)
            
            time.sleep(1)  # Rate limiting
        
        comparison_data.append(question_comparison)
        all_results["results"][f"question_{q_idx}"] = question_comparison
    
    # Save comprehensive results as text
    results_file = f"{output_dir}/comparison_results.txt"
    with open(results_file, "w", encoding="utf-8") as f:
        f.write("COMPREHENSIVE COMPARISON RESULTS\n")
        f.write("="*80 + "\n")
        f.write(f"Test Date: {all_results['test_date']}\n")
        f.write(f"Model: {all_results['model']}\n")
        f.write(f"Total Questions: {all_results['total_questions']}\n")
        f.write("="*80 + "\n\n")
        
        for q_key, q_data in all_results['results'].items():
            f.write(f"\nQuestion {q_data['question_num']}: {q_data['question']}\n")
            f.write("-"*80 + "\n")
            
            for approach, data in q_data['answers'].items():
                f.write(f"\n{approach.upper()}:\n")
                f.write("Metrics:\n")
                for metric, value in data['metrics'].items():
                    f.write(f"  - {metric}: {value}\n")
                f.write("\nAnswer:\n")
                f.write(data['answer'] + "\n")
                f.write("-"*40 + "\n")
    
    # Create readable comparison report
    create_comparison_report(comparison_data, output_dir, model_name)
    
    # Print summary statistics
    print_comparison_summary(comparison_data)
    
    # Save best practices recommendations
    save_recommendations(comparison_data, output_dir)
    
    return all_results, comparison_data

def create_comparison_report(comparison_data, output_dir, model_name):
    """Create a readable side-by-side comparison report"""
    
    report_file = f"{output_dir}/readable_comparison.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("STRUCTURED vs ROLE-BASED PROMPT COMPARISON\n")
        f.write("="*80 + "\n")
        f.write(f"Model: {model_name}\n")
        f.write(f"Total Questions: {len(comparison_data)}\n")
        f.write("="*80 + "\n\n")
        
        for comp in comparison_data:
            f.write(f"QUESTION {comp['question_num']}: {comp['question']}\n")
            f.write("-"*80 + "\n\n")
            
            # Structured approach
            if "structured" in comp["answers"]:
                structured = comp["answers"]["structured"]
                f.write("STRUCTURED APPROACH:\n")
                f.write(f"Metrics: Quotes={structured['metrics'].get('quote_count', 0)}, ")
                f.write(f"Words={structured['metrics'].get('word_count', 0)}, ")
                f.write(f"Time={structured['metrics'].get('response_time', 0)}s\n\n")
                f.write(structured["answer"] + "\n\n")
            
            # Role-based approach
            if "role_based" in comp["answers"]:
                role_based = comp["answers"]["role_based"]
                f.write("ROLE-BASED APPROACH:\n")
                f.write(f"Metrics: Quotes={role_based['metrics'].get('quote_count', 0)}, ")
                f.write(f"Words={role_based['metrics'].get('word_count', 0)}, ")
                f.write(f"Time={role_based['metrics'].get('response_time', 0)}s\n\n")
                f.write(role_based["answer"] + "\n\n")
            
            f.write("="*80 + "\n\n")

def print_comparison_summary(comparison_data):
    """Print summary statistics comparing both approaches"""
    
    print("\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)
    
    # Calculate aggregate statistics
    stats = {
        "structured": {
            "total_quotes": 0,
            "total_words": 0,
            "total_time": 0,
            "speaker_count": 0,
            "section_count": 0,
            "gaps_count": 0,
            "count": 0
        },
        "role_based": {
            "total_quotes": 0,
            "total_words": 0,
            "total_time": 0,
            "speaker_count": 0,
            "section_count": 0,
            "gaps_count": 0,
            "count": 0
        }
    }
    
    for comp in comparison_data:
        for approach in ["structured", "role_based"]:
            if approach in comp["answers"]:
                metrics = comp["answers"][approach]["metrics"]
                if "error" not in metrics:
                    s = stats[approach]
                    s["total_quotes"] += metrics.get("quote_count", 0)
                    s["total_words"] += metrics.get("word_count", 0)
                    s["total_time"] += metrics.get("response_time", 0)
                    s["speaker_count"] += 1 if metrics.get("has_speaker_names") else 0
                    s["section_count"] += 1 if metrics.get("has_sections") else 0
                    s["gaps_count"] += 1 if metrics.get("has_missing_info") else 0
                    s["count"] += 1
    
    # Print comparison table
    print(f"\n{'Metric':<25} {'Structured':>15} {'Role-Based':>15}")
    print("-" * 55)
    
    for approach in ["structured", "role_based"]:
        s = stats[approach]
        if s["count"] > 0:
            if approach == "structured":
                continue  # Skip first iteration to print both side by side
    
    # Average quotes
    struct_avg_quotes = stats["structured"]["total_quotes"] / stats["structured"]["count"] if stats["structured"]["count"] > 0 else 0
    role_avg_quotes = stats["role_based"]["total_quotes"] / stats["role_based"]["count"] if stats["role_based"]["count"] > 0 else 0
    print(f"{'Average Quotes':<25} {struct_avg_quotes:>15.1f} {role_avg_quotes:>15.1f}")
    
    # Average words
    struct_avg_words = stats["structured"]["total_words"] / stats["structured"]["count"] if stats["structured"]["count"] > 0 else 0
    role_avg_words = stats["role_based"]["total_words"] / stats["role_based"]["count"] if stats["role_based"]["count"] > 0 else 0
    print(f"{'Average Word Count':<25} {struct_avg_words:>15.0f} {role_avg_words:>15.0f}")
    
    # Average response time
    struct_avg_time = stats["structured"]["total_time"] / stats["structured"]["count"] if stats["structured"]["count"] > 0 else 0
    role_avg_time = stats["role_based"]["total_time"] / stats["role_based"]["count"] if stats["role_based"]["count"] > 0 else 0
    print(f"{'Average Response Time':<25} {struct_avg_time:>14.1f}s {role_avg_time:>14.1f}s")
    
    # Has speaker names percentage
    struct_speaker_pct = (stats["structured"]["speaker_count"] / stats["structured"]["count"] * 100) if stats["structured"]["count"] > 0 else 0
    role_speaker_pct = (stats["role_based"]["speaker_count"] / stats["role_based"]["count"] * 100) if stats["role_based"]["count"] > 0 else 0
    print(f"{'Has Speaker Names':<25} {struct_speaker_pct:>14.0f}% {role_speaker_pct:>14.0f}%")
    
    # Has sections percentage
    struct_section_pct = (stats["structured"]["section_count"] / stats["structured"]["count"] * 100) if stats["structured"]["count"] > 0 else 0
    role_section_pct = (stats["role_based"]["section_count"] / stats["role_based"]["count"] * 100) if stats["role_based"]["count"] > 0 else 0
    print(f"{'Has Clear Sections':<25} {struct_section_pct:>14.0f}% {role_section_pct:>14.0f}%")
    
    # Identifies gaps percentage
    struct_gaps_pct = (stats["structured"]["gaps_count"] / stats["structured"]["count"] * 100) if stats["structured"]["count"] > 0 else 0
    role_gaps_pct = (stats["role_based"]["gaps_count"] / stats["role_based"]["count"] * 100) if stats["role_based"]["count"] > 0 else 0
    print(f"{'Identifies Gaps':<25} {struct_gaps_pct:>14.0f}% {role_gaps_pct:>14.0f}%")
    
    # Calculate overall scores
    struct_score = (struct_avg_quotes * 2) + (struct_speaker_pct / 10) + (struct_section_pct / 10) + (struct_gaps_pct / 10)
    role_score = (role_avg_quotes * 2) + (role_speaker_pct / 10) + (role_section_pct / 10) + (role_gaps_pct / 10)
    
    print("\n" + "-" * 55)
    print(f"{'Overall Score':<25} {struct_score:>15.1f} {role_score:>15.1f}")
    
    # Recommendation
    print("\n" + "="*80)
    print("RECOMMENDATION:")
    print("="*80)
    
    if struct_score > role_score:
        print(f"✓ STRUCTURED approach performs better (Score: {struct_score:.1f} vs {role_score:.1f})")
        print("  - More consistent quote extraction")
        print("  - Better organized responses")
        print("  - Clear identification of gaps")
    else:
        print(f"✓ ROLE-BASED approach performs better (Score: {role_score:.1f} vs {struct_score:.1f})")
        print("  - More natural language flow")
        print("  - Better contextual understanding")
        print("  - More comprehensive answers")

def save_recommendations(comparison_data, output_dir):
    """Save specific recommendations based on analysis"""
    
    rec_file = f"{output_dir}/recommendations.txt"
    with open(rec_file, "w", encoding="utf-8") as f:
        f.write("PROMPT ENGINEERING RECOMMENDATIONS\n")
        f.write("="*80 + "\n\n")
        
        f.write("Based on the comparison analysis, here are specific recommendations:\n\n")
        
        # Analyze patterns
        structured_better = []
        role_based_better = []
        
        for comp in comparison_data:
            if "structured" in comp["answers"] and "role_based" in comp["answers"]:
                s_metrics = comp["answers"]["structured"]["metrics"]
                r_metrics = comp["answers"]["role_based"]["metrics"]
                
                if "error" not in s_metrics and "error" not in r_metrics:
                    s_score = s_metrics.get("quote_count", 0) + (10 if s_metrics.get("has_sections") else 0)
                    r_score = r_metrics.get("quote_count", 0) + (10 if r_metrics.get("has_sections") else 0)
                    
                    if s_score > r_score:
                        structured_better.append(comp["question"])
                    else:
                        role_based_better.append(comp["question"])
        
        f.write("1. STRUCTURED APPROACH works better for:\n")
        for q in structured_better[:3]:  # Show top 3 examples
            f.write(f"   - {q}\n")
        
        f.write("\n2. ROLE-BASED APPROACH works better for:\n")
        for q in role_based_better[:3]:  # Show top 3 examples
            f.write(f"   - {q}\n")
        
        f.write("\n3. HYBRID APPROACH SUGGESTION:\n")
        f.write("Consider combining the best of both approaches:\n")
        f.write("- Use role-based framing for context\n")
        f.write("- Include structured sections for clarity\n")
        f.write("- Maintain requirement for exact quotes\n")
        f.write("- Add explicit gap identification\n")

def quick_test():
    """Run the comparison test"""
    
    transcript_path = "C:\\Users\\kayla.dipaolo\\source\\repos\\openAITesting\\Dillworth+phase+1+handover.txt"
    questions_path = "C:\\Users\\kayla.dipaolo\\source\\repos\\openAITesting\\Handoff Questions.txt"
    model_name = "ft:o4-mini-2025-04-16:flynn:test-eleven:BgYLe9DH"
    
    print("Starting Structured vs Role-Based Prompt Comparison...")
    print("This will test all questions with both approaches\n")
    
    results, comparison_data = run_comparison_test(transcript_path, questions_path, model_name)
    
    print(f"\n✓ Test complete! Check the output directory for detailed results.")
    print("\nKey files created:")
    print("  - comparison_results.txt (comprehensive data)")
    print("  - readable_comparison.txt (side-by-side comparison)")
    print("  - recommendations.txt (specific suggestions)")
    print("  - Individual response files for each question/approach")

if __name__ == "__main__":
    quick_test()