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

# Final two Anthropic prompt candidates
ANTHROPIC_FINAL_PROMPTS = {
    "structured_with_recommendations": """You are a Flynn Construction analyst reviewing handover meeting transcripts.

For EVERY answer, follow this exact structure:
1. DIRECT ANSWER: [One clear sentence answering the question]
2. EVIDENCE: [2-3 exact quotes with speaker names using "Speaker: 'quote'" format]
3. ADDITIONAL CONTEXT: [Any other relevant information from the transcript]
4. RECOMMENDATIONS: [For any unclear or missing information, provide specific actions: who to contact, what documents to request, or what questions to ask the GC/owner]""",
    
    "enhanced_role_based": """You are a senior project manager at Flynn Construction preparing your team for this project.

{transcript}

Analyze the handover meeting and provide actionable information:
- Present findings as clear statements explaining what was determined
- Support each point with evidence: "Speaker: 'exact quote'"
- Include relevant context that impacts execution
- End with specific recommendations for any information gaps or items needing clarification

Focus on what the construction team needs to execute successfully.

Question: {question}
Answer:"""
}

# System prompt for both
SYSTEM_PROMPT = """You are an expert transcript analyst for Flynn Construction, specializing in construction project handover meetings.

Key principles:
- Provide professional-level analysis (assume readers understand construction)
- Quote directly from the transcript to support all claims
- Synthesize information clearly before presenting evidence
- Only suggest follow-ups for genuinely unclear contract/spec items
- Keep responses concise but comprehensive"""

def evaluate_anthropic_answer(answer: str, question: str) -> dict:
    """Evaluate the quality of Anthropic's answer"""
    
    metrics = {
        # Basic counts
        "char_count": len(answer),
        "word_count": len(answer.split()),
        "quote_count": len(re.findall(r'"[^"]+?"', answer)),
        
        # Structure checks
        "has_direct_answer": "DIRECT ANSWER:" in answer,
        "has_evidence_section": "EVIDENCE:" in answer,
        "has_recommendations": "RECOMMENDATIONS:" in answer or "recommend" in answer.lower(),
        
        # Quality indicators
        "has_speaker_attribution": bool(re.search(r'\w+\s*:\s*["\']', answer)),
        "has_specific_actions": any(action in answer.lower() for action in 
                                   ["contact", "request", "obtain", "clarify", "confirm", "ask"]),
        "synthesis_before_quotes": False
    }
    
    # Check if there's substantial text before the first quote
    first_quote_pos = answer.find('"')
    if first_quote_pos > 100:  # At least 100 chars of context
        metrics["synthesis_before_quotes"] = True
    elif first_quote_pos == -1:  # No quotes found
        metrics["synthesis_before_quotes"] = True  # All synthesis
    
    # Check if recommendations are specific (not generic)
    if metrics["has_recommendations"]:
        generic_phrases = ["more information", "further details", "additional clarity"]
        specific_phrases = ["Grayback", "Brian Rich", "GC", "owner", "bid documents", "spec"]
        
        has_generic = any(phrase in answer.lower() for phrase in generic_phrases)
        has_specific = any(phrase in answer.lower() for phrase in specific_phrases)
        
        metrics["specific_recommendations"] = has_specific and not has_generic
    else:
        metrics["specific_recommendations"] = False
    
    # Overall quality score
    quality_components = []
    
    # For structured prompt
    if metrics["has_direct_answer"]:
        quality_components.extend([
            metrics["has_direct_answer"] * 0.2,
            metrics["has_evidence_section"] * 0.2,
            metrics["has_recommendations"] * 0.2,
            metrics["specific_recommendations"] * 0.2,
            min(metrics["quote_count"] / 3, 1) * 0.2
        ])
    else:
        # For role-based prompt
        quality_components.extend([
            metrics["synthesis_before_quotes"] * 0.3,
            metrics["has_speaker_attribution"] * 0.2,
            metrics["has_recommendations"] * 0.2,
            metrics["has_specific_actions"] * 0.2,
            min(metrics["quote_count"] / 3, 1) * 0.1
        ])
    
    metrics["quality_score"] = sum(quality_components)
    
    return metrics

def test_anthropic_prompts(transcript_path: str, test_questions: list):
    """Test both Anthropic prompt variations"""
    
    print("ANTHROPIC FINAL PROMPT COMPARISON")
    print("=" * 80)
    
    # Load transcript
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript_content = f.read()
    
    results = {}
    
    for q_idx, question in enumerate(test_questions, 1):
        print(f"\n\nQUESTION {q_idx}: {question}")
        print("-" * 80)
        
        question_results = {}
        
        for prompt_name, user_prompt_template in ANTHROPIC_FINAL_PROMPTS.items():
            print(f"\n{prompt_name.upper().replace('_', ' ')}:")
            
            # Format the user prompt
            if "{transcript}" in user_prompt_template:
                user_prompt = user_prompt_template.format(
                    transcript=transcript_content,
                    question=question
                )
            else:
                user_prompt = f"""Transcript: \"\"\"{transcript_content}\"\"\"

Question: {question}"""
            
            try:
                start_time = time.time()
                
                response = client.messages.create(
                    model="claude-3-opus-20240229",  # or claude-3.5-sonnet-20241022 for cost savings
                    system=SYSTEM_PROMPT,
                    max_tokens=2000,
                    temperature=0.2,  # Low for consistency
                    messages=[{"role": "user", "content": user_prompt}]
                )
                
                answer = response.content[0].text
                response_time = time.time() - start_time
                
                # Evaluate
                metrics = evaluate_anthropic_answer(answer, question)
                metrics["response_time"] = round(response_time, 2)
                
                question_results[prompt_name] = {
                    "answer": answer,
                    "metrics": metrics
                }
                
                # Display results
                print(f"\n  Quality Score: {metrics['quality_score']:.2f}")
                print(f"  Response Time: {metrics['response_time']}s")
                print(f"  Quotes: {metrics['quote_count']}")
                print(f"  Has Recommendations: {'✓' if metrics['has_recommendations'] else '✗'}")
                print(f"  Specific Actions: {'✓' if metrics['has_specific_actions'] else '✗'}")
                
                # Preview
                print(f"\n  Preview: {answer[:300]}...")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"  Error: {str(e)}")
                question_results[prompt_name] = {"error": str(e)}
        
        results[question] = question_results
    
    return results

def compare_results(results: dict):
    """Analyze and compare the results"""
    
    print("\n\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)
    
    # Calculate average scores
    prompt_scores = {name: [] for name in ANTHROPIC_FINAL_PROMPTS.keys()}
    
    for question, question_results in results.items():
        for prompt_name, result in question_results.items():
            if "metrics" in result:
                prompt_scores[prompt_name].append(result["metrics"]["quality_score"])
    
    # Print comparison
    print("\nAverage Quality Scores:")
    for prompt_name, scores in prompt_scores.items():
        if scores:
            avg_score = sum(scores) / len(scores)
            print(f"  {prompt_name}: {avg_score:.2f}")
    
    # Detailed comparison
    print("\n\nDETAILED COMPARISON:")
    
    for prompt_name in ANTHROPIC_FINAL_PROMPTS.keys():
        print(f"\n{prompt_name.upper()}:")
        
        total_quotes = 0
        has_recommendations = 0
        has_specific_actions = 0
        
        for question_results in results.values():
            if prompt_name in question_results and "metrics" in question_results[prompt_name]:
                m = question_results[prompt_name]["metrics"]
                total_quotes += m["quote_count"]
                has_recommendations += 1 if m["has_recommendations"] else 0
                has_specific_actions += 1 if m["has_specific_actions"] else 0
        
        num_questions = len(results)
        print(f"  Avg quotes per answer: {total_quotes / num_questions:.1f}")
        print(f"  Has recommendations: {has_recommendations}/{num_questions}")
        print(f"  Has specific actions: {has_specific_actions}/{num_questions}")

def save_comparison_results(results: dict, output_dir: str = "anthropic_comparison"):
    """Save detailed comparison results"""
    
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save full comparison
    comparison_file = f"{output_dir}/comparison_{timestamp}.json"
    with open(comparison_file, "w") as f:
        json.dump(results, f, indent=2)
    
    # Save readable comparison
    readable_file = f"{output_dir}/readable_comparison_{timestamp}.txt"
    with open(readable_file, "w", encoding="utf-8") as f:
        f.write("ANTHROPIC PROMPT COMPARISON\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("="*80 + "\n\n")
        
        for question, question_results in results.items():
            f.write(f"QUESTION: {question}\n")
            f.write("-"*80 + "\n\n")
            
            for prompt_name, result in question_results.items():
                f.write(f"{prompt_name.upper()}:\n")
                if "answer" in result:
                    f.write(result["answer"] + "\n")
                    f.write(f"\nMetrics: {json.dumps(result['metrics'], indent=2)}\n")
                else:
                    f.write(f"Error: {result.get('error', 'Unknown error')}\n")
                f.write("\n" + "-"*40 + "\n\n")
            
            f.write("="*80 + "\n\n")
    
    print(f"\nResults saved to:")
    print(f"  JSON: {comparison_file}")
    print(f"  Readable: {readable_file}")

def test_parameter_variations():
    """Test different temperature and model settings"""
    
    print("\n\nPARAMETER TESTING (Optional)")
    print("="*80)
    print("\nWould you like to test different parameters?")
    print("1. Temperature: 0.0 vs 0.2 vs 0.4")
    print("2. Model: Opus vs Sonnet 3.5")
    print("3. Skip parameter testing")
    
    # For now, we'll skip this in the automated version
    return None

def main():
    """Main function to run Anthropic comparison"""
    
    # Configuration
    transcript_path = "C:\\Users\\kayla.dipaolo\\source\\repos\\AnthropicTesting\\Dillworth+phase+1+handover.txt"
    
    # Test questions that highlight differences
    test_questions = [
        "What are the underlying risks associated with performing our work on this project?",
        "What are the payment terms?",
        "Do we need to bring any alternates to the attention of the client/customer before starting?",
        "Who is the customer for this project and describe our past working relationship, if any?",
        "Are there any contractual risks to note?"
    ]
    
    # Run comparison
    print("Testing Anthropic prompt variations...")
    results = test_anthropic_prompts(transcript_path, test_questions)
    
    # Compare results
    compare_results(results)
    
    # Save results
    save_comparison_results(results)
    
    # Recommendation
    print("\n\n" + "="*80)
    print("RECOMMENDATION:")
    print("="*80)
    print("\nBased on the comparison, review the readable output file to see which approach:")
    print("1. Provides clearer structure (if that's important to your team)")
    print("2. Gives more actionable recommendations")
    print("3. Balances completeness with conciseness")
    print("\nThen we can create the final production code for your chosen approach!")

if __name__ == "__main__":
    main()