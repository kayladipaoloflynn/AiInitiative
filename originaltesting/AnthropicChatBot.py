import anthropic
import os

# 👉 Step 1: Set your Claude API key
client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")  # CHANGE THIS if needed
)

# 👉 Step 2: Prepare your transcript content
# Ideally this is extracted and cleaned from a PDF file ahead of time
with open("C:\\Users\\kayla.dipaolo\\source\\repos\\AnthropicTesting\\Dillworth+phase+1+handover.txt", "r", encoding="utf-8") as f:
    transcript_content = f.read()

# 👉 Step 3: Define your support system prompt
# Tailor this for your transcript reader support agent
system_prompt = (
    "You are an information extraction assistant for Flynn construction. You are used to help teams transfer projects from one department to another by answering specific questions"
    "about the project at hand so that all parties are up to date regarding the specifications. helping to analyze handover meeting transcripts contained in PDF documents."
    "Answer questions only using information explicitly stated in the transcript — do not make assumptions or fabricate answers."
    "For each answer:"
    "Provide a clear and concise response"
    "Support it with at least two direct quotes or paraphrased sentences from the transcript as evidence"
    "Ensure that your response is grammatically correct and free of errors"
)

# 👉 Step 4: User question (simulate a customer inquiry)
user_question = "Who was a part of the meeting?"

# 👉 Step 5: Combine the transcript and question
user_input = f"""
Transcript:
\"\"\"
{transcript_content}
\"\"\"

Question: {user_question}
"""

# 👉 Step 6: Call Claude API
response = client.messages.create(
    model="claude-3-opus-20240229",  # You can also try claude-3-sonnet or claude-3-haiku
    max_tokens=1000,
    temperature=0.7,
    system=system_prompt,
    messages=[
        {"role": "user", "content": user_input}
    ]
)

# 👉 Step 7: Output the result
print("Claude’s answer:\n")
print(response.content[0].text)
