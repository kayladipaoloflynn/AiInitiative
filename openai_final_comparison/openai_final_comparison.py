import os
import openai
import time
import json
from datetime import datetime
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Your two finalist prompts with modified structured version
FINAL_PROMPTS = {
    "structured_with_suggestions": """TRANSCRIPT:
{transcript}

Answer the following question using this EXACT structure:
1. DIRECT ANSWER: [One clear sentence answering the question]
2. EVIDENCE: [2-3 exact quotes with speaker names]  
3. ADDITIONAL CONTEXT: [Other relevant information from the transcript]
4. RECOMMENDATIONS: [If any information is missing or unclear, suggest specific actions to obtain it, such as who to contact, what documents to request, or what questions to ask]

Question: {question}
Answer:""",
    
    "role_based": """You are reviewing this Flynn Construction handover meeting transcript:

{transcript}

As a senior project manager, provide clear, actionable information the construction team needs.
- Quote speakers exactly: "Name: 'quote'"
- Flag any concerns or follow-up items
- Be thorough - the team's success depends on these details

Question: {question}
Answer:"""
}

def test_prompt_variation(prompt_template, transcript, question, model_name):
    """Test a single prompt variation"""
    
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
        
        # Analyze the answer
        metrics = {
            "response_time": round(response_time, 2),
            "quote_count": answer.count('"'),
            "word_count": len(answer.split()),
            "char_count": len(answer),
            "has_speaker_names": any(name in answer for name in ["Frank", "Kevin", "KEL", "Dariusz"]),
            "has_sections": all(section in answer for section in ["DIRECT ANSWER:", "EVIDENCE:", "ADDITIONAL CONTEXT:", "RECOMMENDATIONS:"]),
            "has_recommendations": "recommend" in answer.lower() or "suggest" in answer.lower() or "should" in answer.lower(),
            "has_action_items": "contact" in answer.lower() or "request" in answer.lower() or "ask" in answer.lower() or "follow up" in answer.lower()
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

def detailed_comparison(transcript_path, test_questions, model_name):
    """Run a detailed comparison of structured vs role-based prompts"""
    
    # Load transcript
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = f.read().strip()
    
    print("DETAILED COMPARISON: STRUCTURED (with suggestions) vs ROLE-BASED")
    print("=" * 80)
    
    results = {"structured_with_suggestions": [], "role_based": []}
    comparison_data = []
    
    for q_idx, question in enumerate(test_questions, 1):
        print(f"\n\nQUESTION {q_idx}: {question}")
        print("-" * 80)
        
        question_comparison = {
            "question": question,
            "answers": {}
        }
        
        for prompt_name, prompt_template in FINAL_PROMPTS.items():
            print(f"\n{prompt_name.upper().replace('_', ' ')}:")
            
            # Get the answer
            result = test_prompt_variation(prompt_template, transcript, question, model_name)
            
            answer = result["answer"]
            metrics = result["metrics"]
            
            # Store results
            results[prompt_name].append({
                "question": question,
                "answer": answer,
                "metrics": metrics
            })
            
            question_comparison["answers"][prompt_name] = {
                "answer": answer,
                "metrics": metrics
            }
            
            # Display preview and metrics
            print("\nAnswer Preview:")
            print(answer[:400] + "..." if len(answer) > 400 else answer)
            
            print(f"\nMetrics:")
            print(f"  - Quotes: {metrics.get('quote_count', 0)}")
            print(f"  - Length: {metrics.get('word_count', 0)} words")
            print(f"  - Has speaker names: {metrics.get('has_speaker_names', False)}")
            
            if prompt_name == "structured_with_suggestions":
                print(f"  - Has all sections: {metrics.get('has_sections', False)}")
                print(f"  - Has recommendations: {metrics.get('has_recommendations', False)}")
                print(f"  - Has action items: {metrics.get('has_action_items', False)}")
            
            time.sleep(1)
        
        comparison_data.append(question_comparison)
    
    # Save detailed comparison
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = "openai_final_comparison"
    os.makedirs(output_dir, exist_ok=True)
    
    # Save JSON results
    comparison_file = f"{output_dir}/comparison_{timestamp}.json"
    with open(comparison_file, "w", encoding="utf-8") as f:
        json.dump({
            "test_date": timestamp,
            "model": model_name,
            "comparisons": comparison_data
        }, f, indent=2)
    
    # Save readable comparison
    readable_file = f"{output_dir}/readable_comparison_{timestamp}.txt"
    with open(readable_file, "w", encoding="utf-8") as f:
        f.write("STRUCTURED vs ROLE-BASED COMPARISON\n")
        f.write("="*80 + "\n\n")
        
        for comp in comparison_data:
            f.write(f"QUESTION: {comp['question']}\n")
            f.write("-"*80 + "\n\n")
            
            f.write("STRUCTURED WITH SUGGESTIONS:\n")
            f.write(comp['answers']['structured_with_suggestions']['answer'] + "\n\n")
            
            f.write("ROLE-BASED:\n")
            f.write(comp['answers']['role_based']['answer'] + "\n\n")
            f.write("="*80 + "\n\n")
    
    print(f"\n\nResults saved to:")
    print(f"  - JSON: {comparison_file}")
    print(f"  - Readable: {readable_file}")
    
    return results, comparison_data

def analyze_recommendations(results):
    """Analyze the quality of recommendations in structured answers"""
    
    print("\n\nRECOMMENDATION ANALYSIS")
    print("="*80)
    
    structured_answers = results["structured_with_suggestions"]
    
    recommendation_quality = []
    
    for item in structured_answers:
        answer = item["answer"]
        question = item["question"]
        
        # Extract recommendations section if it exists
        if "RECOMMENDATIONS:" in answer:
            rec_start = answer.find("RECOMMENDATIONS:")
            rec_section = answer[rec_start:].split("\n")[0:5]  # Get first few lines
            rec_text = "\n".join(rec_section)
            
            # Check quality indicators
            has_specific_actions = any(word in rec_text.lower() for word in 
                                     ["contact", "request", "obtain", "clarify", "confirm", "ask"])
            has_who_to_contact = any(word in rec_text for word in 
                                   ["manager", "client", "customer", "Grayback", "superintendent"])
            has_what_to_ask = "?" in rec_text or any(word in rec_text.lower() for word in 
                                                    ["whether", "if", "what", "when", "how"])
            
            quality_score = sum([has_specific_actions, has_who_to_contact, has_what_to_ask]) / 3
            
            recommendation_quality.append({
                "question": question[:60] + "...",
                "has_recommendations": True,
                "quality_score": quality_score,
                "sample": rec_text[:200] + "..."
            })
        else:
            recommendation_quality.append({
                "question": question[:60] + "...",
                "has_recommendations": False,
                "quality_score": 0
            })
    
    # Print analysis
    for rec in recommendation_quality:
        print(f"\nQuestion: {rec['question']}")
        if rec['has_recommendations']:
            print(f"Quality Score: {rec['quality_score']:.1%}")
            print(f"Sample: {rec['sample']}")
        else:
            print("No recommendations section found")
    
    avg_quality = sum(r['quality_score'] for r in recommendation_quality) / len(recommendation_quality)
    print(f"\n\nAverage Recommendation Quality: {avg_quality:.1%}")

def create_hybrid_prompt():
    """Create a hybrid prompt combining best of both"""
    
    hybrid = """You are a senior project manager at Flynn Construction reviewing this handover meeting transcript:

{transcript}

Provide clear, actionable information using this structure:
1. DIRECT ANSWER: One clear sentence answering the question
2. EVIDENCE: 2-3 exact quotes using "Speaker Name: 'quote'" format
3. ADDITIONAL CONTEXT: Other relevant information the construction team needs
4. ACTION ITEMS: If any information is missing or needs clarification, provide specific recommendations:
   - Who to contact (name and role)
   - What documents to request
   - Specific questions to ask
   - Timeline for follow-up

Focus on what will help the construction team execute successfully.

Question: {question}
Answer:"""
    
    return hybrid

def quick_test():
    """Quick test comparing structured vs role-based"""
    
    test_questions = [
        "Who is the customer for this project and describe our past working relationship, if any?",
        "What are the underlying risks associated with performing our work on this project?",
        "What are the payment terms?",
        "Do we need to bring any alternates to the attention of the client/customer before starting?",
        "Are there any contractual risks to note?"
    ]
    
    transcript_path = "C:\\Users\\kayla.dipaolo\\source\\repos\\openAITesting\\Dillworth+phase+1+handover.txt"
    model_name = "ft:gpt-4o-2024-08-06:flynn:test-nine:BcuSbEPv"
    
    # Run comparison
    results, comparison_data = detailed_comparison(transcript_path, test_questions, model_name)
    
    # Analyze recommendations
    analyze_recommendations(results)
    
    # Test hybrid if desired
    print("\n\nWould you like to test a HYBRID approach? (combines structure + PM perspective)")
    print("Check the output files first to see if you need it.")
    
    # Save the hybrid prompt for reference
    with open("openai_final_comparison/hybrid_prompt.txt", "w") as f:
        f.write("HYBRID PROMPT (Best of Both Worlds):\n\n")
        f.write(create_hybrid_prompt())

if __name__ == "__main__":
    quick_test()