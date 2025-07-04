import anthropic
import os
import time
import json
from datetime import datetime
import re

# Set up Anthropic client
client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

# Enhanced role-based prompt (the winner)
ENHANCED_ROLE_BASED_PROMPT = """You are a senior project manager at Flynn Construction preparing your team for this project.

{transcript}

Analyze the handover meeting and provide actionable information:
- Present findings as clear statements explaining what was determined
- Support each point with evidence: "Speaker: 'exact quote'"
- Include relevant context that impacts execution
- End with specific recommendations for any information gaps or items needing clarification

Focus on what the construction team needs to execute successfully.

Question: {question}
Answer:"""

# System prompt
SYSTEM_PROMPT = """You are an expert transcript analyst for Flynn Construction, specializing in construction project handover meetings.

Key principles:
- Provide professional-level analysis (assume readers understand construction)
- Quote directly from the transcript to support all claims
- Synthesize information clearly before presenting evidence
- Only suggest follow-ups for genuinely unclear contract/spec items
- Keep responses concise but comprehensive"""

# Models to compare
MODELS = {
    "opus": "claude-3-opus-20240229",
    "sonnet": "claude-3-5-sonnet-20241022"  # Updated to correct model name
}

def evaluate_answer_quality(answer: str) -> dict:
    """Evaluate answer quality metrics"""
    
    metrics = {
        "char_count": len(answer),
        "word_count": len(answer.split()),
        "quote_count": len(re.findall(r'"[^"]+?"', answer)),
        "has_speaker_attribution": bool(re.search(r'\w+\s*:\s*["\']', answer)),
        "has_recommendations": "recommend" in answer.lower() or "clarif" in answer.lower(),
        "has_specific_actions": any(action in answer.lower() for action in 
                                   ["contact", "request", "obtain", "clarify", "confirm", "ask"]),
        "synthesis_before_quotes": False
    }
    
    # Check synthesis
    first_quote_pos = answer.find('"')
    if first_quote_pos > 100 or first_quote_pos == -1:
        metrics["synthesis_before_quotes"] = True
    
    # Quality score
    quality_score = (
        metrics["synthesis_before_quotes"] * 0.3 +
        metrics["has_speaker_attribution"] * 0.2 +
        metrics["has_recommendations"] * 0.2 +
        metrics["has_specific_actions"] * 0.2 +
        min(metrics["quote_count"] / 3, 1) * 0.1
    )
    metrics["quality_score"] = quality_score
    
    return metrics

def compare_models(transcript_path: str, test_questions: list):
    """Compare Opus vs Sonnet performance"""
    
    print("ANTHROPIC MODEL COMPARISON: OPUS vs SONNET 3.5")
    print("=" * 80)
    
    # Load transcript
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript_content = f.read()
    
    results = {
        "opus": [],
        "sonnet": [],
        "comparison": []
    }
    
    # Test each question with both models
    for q_idx, question in enumerate(test_questions, 1):
        print(f"\n\nQUESTION {q_idx}/{len(test_questions)}: {question[:60]}...")
        print("-" * 80)
        
        question_comparison = {
            "question": question,
            "models": {}
        }
        
        for model_name, model_id in MODELS.items():
            print(f"\n{model_name.upper()}:")
            
            # Format prompt
            user_prompt = ENHANCED_ROLE_BASED_PROMPT.format(
                transcript=transcript_content,
                question=question
            )
            
            try:
                start_time = time.time()
                
                response = client.messages.create(
                    model=model_id,
                    system=SYSTEM_PROMPT,
                    max_tokens=2000,
                    temperature=0.2,
                    messages=[{"role": "user", "content": user_prompt}]
                )
                
                answer = response.content[0].text
                response_time = time.time() - start_time
                
                # Evaluate
                metrics = evaluate_answer_quality(answer)
                metrics["response_time"] = round(response_time, 2)
                metrics["model"] = model_id
                
                # Calculate approximate cost (rough estimates)
                input_tokens = len(transcript_content) / 4 + len(question) / 4  # Rough estimate
                output_tokens = len(answer) / 4
                
                if model_name == "opus":
                    cost = (input_tokens * 15 + output_tokens * 75) / 1_000_000
                else:  # sonnet
                    cost = (input_tokens * 3 + output_tokens * 15) / 1_000_000
                
                metrics["estimated_cost"] = round(cost, 4)
                
                # Store results
                results[model_name].append({
                    "question": question,
                    "answer": answer,
                    "metrics": metrics
                })
                
                question_comparison["models"][model_name] = {
                    "answer": answer,
                    "metrics": metrics
                }
                
                # Display metrics
                print(f"  Quality Score: {metrics['quality_score']:.2f}")
                print(f"  Response Time: {metrics['response_time']:.1f}s")
                print(f"  Quotes: {metrics['quote_count']}")
                print(f"  Estimated Cost: ${metrics['estimated_cost']:.4f}")
                print(f"  Preview: {answer[:200]}...")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"  Error: {str(e)}")
                results[model_name].append({"error": str(e)})
        
        results["comparison"].append(question_comparison)
    
    return results

def analyze_comparison(results: dict):
    """Analyze and summarize the comparison"""
    
    print("\n\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)
    
    # Calculate averages for each model
    for model_name in ["opus", "sonnet"]:
        model_results = results[model_name]
        
        quality_scores = []
        response_times = []
        costs = []
        
        for result in model_results:
            if "metrics" in result:
                m = result["metrics"]
                quality_scores.append(m["quality_score"])
                response_times.append(m["response_time"])
                costs.append(m["estimated_cost"])
        
        if quality_scores:
            print(f"\n{model_name.upper()} AVERAGES:")
            print(f"  Quality Score: {sum(quality_scores)/len(quality_scores):.2f}")
            print(f"  Response Time: {sum(response_times)/len(response_times):.1f}s")
            print(f"  Cost per Question: ${sum(costs)/len(costs):.4f}")
            print(f"  Total Test Cost: ${sum(costs):.4f}")
    
    # Direct comparison
    print("\n\nDIRECT COMPARISON:")
    
    opus_better = 0
    sonnet_better = 0
    ties = 0
    
    for comp in results["comparison"]:
        if "opus" in comp["models"] and "sonnet" in comp["models"]:
            opus_score = comp["models"]["opus"]["metrics"]["quality_score"]
            sonnet_score = comp["models"]["sonnet"]["metrics"]["quality_score"]
            
            if opus_score > sonnet_score + 0.05:
                opus_better += 1
            elif sonnet_score > opus_score + 0.05:
                sonnet_better += 1
            else:
                ties += 1
    
    print(f"  Opus performed better: {opus_better} questions")
    print(f"  Sonnet performed better: {sonnet_better} questions")
    print(f"  Similar performance: {ties} questions")

def save_model_comparison(results: dict):
    """Save detailed comparison results"""
    
    output_dir = "anthropic_model_comparison"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save full results
    json_file = f"{output_dir}/model_comparison_{timestamp}.json"
    with open(json_file, "w") as f:
        json.dump(results, f, indent=2)
    
    # Save readable comparison
    readable_file = f"{output_dir}/readable_comparison_{timestamp}.txt"
    with open(readable_file, "w", encoding="utf-8") as f:
        f.write("ANTHROPIC MODEL COMPARISON: OPUS vs SONNET 3.5\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("="*80 + "\n\n")
        
        for comp in results["comparison"]:
            f.write(f"QUESTION: {comp['question']}\n")
            f.write("-"*80 + "\n\n")
            
            # Show Opus answer
            if "opus" in comp["models"]:
                f.write("CLAUDE 3 OPUS:\n")
                opus_data = comp["models"]["opus"]
                f.write(opus_data["answer"] + "\n")
                f.write(f"\nMetrics: Quality={opus_data['metrics']['quality_score']:.2f}, ")
                f.write(f"Time={opus_data['metrics']['response_time']}s, ")
                f.write(f"Cost=${opus_data['metrics']['estimated_cost']:.4f}\n")
            
            f.write("\n" + "-"*40 + "\n\n")
            
            # Show Sonnet answer
            if "sonnet" in comp["models"]:
                f.write("CLAUDE 3.5 SONNET:\n")
                sonnet_data = comp["models"]["sonnet"]
                f.write(sonnet_data["answer"] + "\n")
                f.write(f"\nMetrics: Quality={sonnet_data['metrics']['quality_score']:.2f}, ")
                f.write(f"Time={sonnet_data['metrics']['response_time']}s, ")
                f.write(f"Cost=${sonnet_data['metrics']['estimated_cost']:.4f}\n")
            
            f.write("\n" + "="*80 + "\n\n")
    
    print(f"\n\nResults saved to:")
    print(f"  JSON: {json_file}")
    print(f"  Readable: {readable_file}")

def create_final_production_code():
    """Create the final production code template"""
    
    production_code = '''import anthropic
import os
import time
from datetime import datetime

# Initialize Anthropic client
client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

# Configuration - UPDATE BASED ON YOUR TESTING RESULTS
MODEL = "claude-3-5-sonnet-20241022"  # or "claude-3-opus-20240229"
TEMPERATURE = 0.2
MAX_TOKENS = 2000

# Final prompts
SYSTEM_PROMPT = """You are an expert transcript analyst for Flynn Construction, specializing in construction project handover meetings.

Key principles:
- Provide professional-level analysis (assume readers understand construction)
- Quote directly from the transcript to support all claims
- Synthesize information clearly before presenting evidence
- Only suggest follow-ups for genuinely unclear contract/spec items
- Keep responses concise but comprehensive"""

USER_PROMPT_TEMPLATE = """You are a senior project manager at Flynn Construction preparing your team for this project.

{transcript}

Analyze the handover meeting and provide actionable information:
- Present findings as clear statements explaining what was determined
- Support each point with evidence: "Speaker: 'exact quote'"
- Include relevant context that impacts execution
- End with specific recommendations for any information gaps or items needing clarification

Focus on what the construction team needs to execute successfully.

Question: {question}
Answer:"""

def run_anthropic_analysis(transcript_path: str, questions_path: str, output_path: str = None):
    """Run the final Anthropic analysis"""
    
    # Load files
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = f.read()
    
    with open(questions_path, "r", encoding="utf-8") as f:
        questions = [line.strip() for line in f if line.strip()]
    
    # Output setup
    if not output_path:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"anthropic_analysis_{timestamp}.txt"
    
    print(f"Running Anthropic analysis...")
    print(f"Model: {MODEL}")
    print(f"Questions: {len(questions)}")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("FLYNN CONSTRUCTION - HANDOVER ANALYSIS\\n")
        f.write(f"Model: {MODEL}\\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\\n")
        f.write("="*80 + "\\n\\n")
        
        for idx, question in enumerate(questions, 1):
            print(f"\\rProcessing {idx}/{len(questions)}...", end="")
            
            user_prompt = USER_PROMPT_TEMPLATE.format(
                transcript=transcript,
                question=question
            )
            
            try:
                response = client.messages.create(
                    model=MODEL,
                    system=SYSTEM_PROMPT,
                    max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                    messages=[{"role": "user", "content": user_prompt}]
                )
                
                answer = response.content[0].text
                
                f.write(f"Q{idx}: {question}\\n")
                f.write(f"A: {answer}\\n\\n")
                f.write("="*80 + "\\n\\n")
                
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                print(f"\\nError on question {idx}: {str(e)}")
                f.write(f"ERROR: {str(e)}\\n\\n")
    
    print(f"\\nComplete! Results saved to: {output_path}")

if __name__ == "__main__":
    # Update these paths
    transcript_path = "path/to/transcript.txt"
    questions_path = "path/to/questions.txt"
    
    run_anthropic_analysis(transcript_path, questions_path)
'''
    
    # Save production code with UTF-8 encoding
    with open("anthropic_final_production.py", "w", encoding="utf-8") as f:
        f.write(production_code)
    
    print("\n\nProduction code template saved to: anthropic_final_production.py")
    print("Update the MODEL constant based on your comparison results!")

def main():
    """Run the complete model comparison"""
    
    # Configuration
    transcript_path = "C:\\Users\\kayla.dipaolo\\source\\repos\\AnthropicTesting\\Dillworth+phase+1+handover.txt"
    
    # Test questions
    test_questions = [
        "What are the underlying risks associated with performing our work on this project?",
        "Who is the customer for this project and describe our past working relationship, if any?",
        "What are the payment terms?",
        "Do we need to bring any alternates to the attention of the client/customer before starting?",
        "What is the project construction schedule (start and expected completion) for our scope?"
    ]
    
    print("Comparing Claude 3 Opus vs Claude 3.5 Sonnet...")
    print("This will help determine if you can save 80% on costs with similar quality.\n")
    
    # Run comparison
    results = compare_models(transcript_path, test_questions)
    
    # Analyze results
    analyze_comparison(results)
    
    # Save results
    save_model_comparison(results)
    
    # Create production code template
    create_final_production_code()
    
    print("\n\n" + "="*80)
    print("NEXT STEPS:")
    print("="*80)
    print("1. Review the readable comparison file")
    print("2. If Sonnet 3.5 quality is sufficient, you'll save ~80% on costs")
    print("3. Update the production code with your chosen model")
    print("4. You're ready to deploy!")

if __name__ == "__main__":
    main()