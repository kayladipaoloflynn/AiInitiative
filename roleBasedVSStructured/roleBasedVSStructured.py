import anthropic
import os
import time
import json
from datetime import datetime

# Set up the client
client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

# Your two finalist prompts
FINAL_PROMPTS = {
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
- Be thorough - your team's success depends on these details"""
}

def detailed_comparison(transcript_path, test_questions):
    """Run a detailed comparison of the two finalists"""
    
    # Load transcript
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = f.read()
    
    print("DETAILED COMPARISON: STRUCTURED vs ROLE-BASED")
    print("=" * 80)
    
    results = {"structured": [], "role_based": []}
    
    for q_idx, question in enumerate(test_questions, 1):
        print(f"\n\nQUESTION {q_idx}: {question}")
        print("-" * 80)
        
        for prompt_name, prompt in FINAL_PROMPTS.items():
            print(f"\n{prompt_name.upper()} APPROACH:")
            
            # Get the answer
            user_prompt = f"""Transcript: \"\"\"{transcript}\"\"\"

Question: {question}"""
            
            response = client.messages.create(
                model="claude-3-opus-20240229",
                system=prompt,
                max_tokens=2000,
                temperature=0.2,
                messages=[{"role": "user", "content": user_prompt}],
            )
            
            answer = response.content[0].text
            
            # Save for side-by-side review
            results[prompt_name].append({
                "question": question,
                "answer": answer
            })
            
            # Quick preview
            print(answer[:300] + "..." if len(answer) > 300 else answer)
            
            time.sleep(1)
    
    # Save full results for review
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    comparison_file = f"final_comparison_{timestamp}.json"
    
    with open(comparison_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n\nFull results saved to: {comparison_file}")
    
    return results

def quick_ab_test():
    """Quick A/B test focusing on specific differentiators"""
    
    # Test questions that highlight differences
    test_questions = [
        # Tests structure vs natural flow
        "What are the underlying risks associated with performing our work on this project?",
        
        # Tests actionability 
        "Do we need to bring any alternates to the attention of the client/customer before starting?",
        
        # Tests completeness
        "What is the project construction schedule (start and expected completion) for our scope?",
        
        # Tests "what's missing" identification
        "What are the payment terms?",
        
        # Tests follow-up flagging
        "Are there any contractual risks to note?"
    ]
    
    transcript_path = "C:\\Users\\kayla.dipaolo\\source\\repos\\AnthropicTesting\\Dillworth+phase+1+handover.txt"
    
    results = detailed_comparison(transcript_path, test_questions)
    
    # Interactive review
    print("\n\n" + "="*80)
    print("INTERACTIVE REVIEW - Which is better for each question?")
    print("="*80)
    
    scores = {"structured": 0, "role_based": 0}
    
    for idx in range(len(test_questions)):
        print(f"\n\nQUESTION: {test_questions[idx]}")
        print("\nSTRUCTURED Answer Preview:")
        print(results["structured"][idx]["answer"][:400] + "...")
        print("\nROLE-BASED Answer Preview:")
        print(results["role_based"][idx]["answer"][:400] + "...")
        
        print("\nWhich is better?")
        print("1 = Structured")
        print("2 = Role-based")
        print("3 = Tie")
        
        # For automated testing, let's analyze programmatically
        struct_answer = results["structured"][idx]["answer"]
        role_answer = results["role_based"][idx]["answer"]
        
        # Check which one has clearer sections
        struct_has_sections = all(marker in struct_answer for marker in ["DIRECT ANSWER:", "EVIDENCE:", "ADDITIONAL CONTEXT:", "MISSING INFO:"])
        role_has_quotes = struct_answer.count('"') >= 2
        
        print(f"\nAuto-analysis:")
        print(f"- Structured has clear sections: {struct_has_sections}")
        print(f"- Structured quotes: {struct_answer.count('"')}")
        print(f"- Role-based quotes: {role_answer.count('"')}")
        print(f"- Structured length: {len(struct_answer)} chars")
        print(f"- Role-based length: {len(role_answer)} chars")

def hybrid_prompt_test():
    """Test a hybrid approach combining the best of both"""
    
    hybrid_prompt = """You are a senior project manager at Flynn Construction reviewing handover meeting transcripts.
Your team needs clear, actionable information for project success.

For EVERY answer, follow this structure:
1. DIRECT ANSWER: One clear sentence answering the question
2. EVIDENCE: 2-3 exact quotes using "Speaker Name: 'quote'" format  
3. ADDITIONAL CONTEXT: Other relevant information from the transcript
4. ACTION ITEMS: Any concerns or items needing follow-up with the client
5. MISSING INFO: What was NOT discussed that the team should know

Focus on what the construction team needs to execute this project successfully."""

    print("\n\nTESTING HYBRID APPROACH (Best of Both)")
    print("=" * 80)
    
    # Test the hybrid on one key question
    test_question = "What are the underlying risks associated with performing our work on this project?"
    transcript_path = "C:\\Users\\kayla.dipaolo\\source\\repos\\AnthropicTesting\\Dillworth+phase+1+handover.txt"
    
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = f.read()
    
    user_prompt = f"""Transcript: \"\"\"{transcript}\"\"\"

Question: {test_question}"""
    
    response = client.messages.create(
        model="claude-3-opus-20240229",
        system=hybrid_prompt,
        max_tokens=2000,
        temperature=0.2,
        messages=[{"role": "user", "content": user_prompt}],
    )
    
    print("HYBRID RESULT:")
    print(response.content[0].text)

if __name__ == "__main__":
    # First, do the A/B comparison
    quick_ab_test()
    
    # Then test the hybrid approach
    print("\n\nPress Enter to test HYBRID approach...")
    input()
    hybrid_prompt_test()