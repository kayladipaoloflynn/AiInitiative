import anthropic
import os

# 👉 Step 1: Set your Claude API key
client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")  # CHANGE THIS if needed
)

# Load transcript
with open("C:\\Users\\kayla.dipaolo\\source\\repos\\AnthropicTesting\\Dillworth+phase+1+handover.txt", "r", encoding="utf-8") as f:
    transcript_content = f.read()

# Load questions
with open("C:\\Users\\kayla.dipaolo\\source\\repos\\AnthropicTesting\\Handoff Questions.txt", "r", encoding="utf-8") as f:
    questions = [q.strip() for q in f.readlines() if q.strip()]

# System prompt
system_prompt = (
    "You are an information extraction assistant for Flynn construction. You are helping to analyze handover meeting transcripts. "
    "For each answer, do the following:\n"
    "- Provide a clear and concise response\n"
    "- Support it with at least two direct quotes or paraphrased pieces of evidence from the transcript\n"
    "- Do not make assumptions — only use content from the transcript\n"
    "- Ensure the response is grammatically correct\n"
)

# Output collection
answers = []

# Loop through questions
for idx, question in enumerate(questions, start=1):
    print(f"Processing Question {idx}: {question}")

    user_prompt = f"""
Transcript:
\"\"\"{transcript_content}\"\"\"

Question: {question}
"""

    response = client.messages.create(
        model="claude-3-opus-20240229",
        system=system_prompt,
        max_tokens=2500,
        temperature=0.6,
        messages=[{"role": "user", "content": user_prompt}],
    )

    answer_text = response.content[0].text
    answers.append((question, answer_text))

# Save results to file
with open("C:\\Users\\kayla.dipaolo\\source\\repos\\AnthropicTesting\\outputAnswersAnthropic(3500).txt", "w", encoding="utf-8") as f:
    for question, answer in answers:
        f.write(f"Q: {question}\nA: {answer}\n\n{'='*80}\n\n")
