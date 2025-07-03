import os
import openai
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ─── [B] Read the full transcript into a single string ─────────────────────────────
with open("C:\\Users\\kayla.dipaolo\\source\\repos\\openAITesting\\Dillworth+phase+1+handover.txt", "r", encoding="utf-8") as f:
    transcript = f.read().strip()

# ─── [C] Read all questions into a list (one per line) ─────────────────────────────
with open("C:\\Users\\kayla.dipaolo\\source\\repos\\openAITesting\\Handoff Questions.txt", "r", encoding="utf-8") as f:
    questions = [line.strip() for line in f if line.strip()]

# ─── [D] Open a file to write all Q&A pairs ─────────────────────────────────────────
with open("C:\\Users\\kayla.dipaolo\\source\\repos\\openAITesting\\FineTunedDPO_Response.txt", "w", encoding="utf-8") as out_file:

    # Loop through each question (or you could batch them into one prompt if you trained that way)
    for i, q in enumerate(questions, start=1):
        # Format a prompt string for your fine-tuned model. 
        #    Adjust “PREFIX” and “SUFFIX” based on how you taught it to expect input.
        prompt = (
            "Here is a construction-handover transcript:\n\n"
            f"{transcript}\n\n"
            "Using only the information above, answer the following question clearly using quotes from the transcript to support your answers. At the end of each response provide a summary using your own knowledge as well as the transcript information to give a recap which fully answers the questions clearly and completely:\n"
            f"Q{i}: {q}\n"
            "A:"
        )

        # Call your fine-tuned model (replace "my-handover-qa-ft" with your actual fine-tune name).
        response = openai.chat.completions.create(
            model="ft:gpt-4o-2024-08-06:flynn:test-nine:BcuSbEPv",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,       # adjust if you want longer/shorter answers
            temperature=0.4,       # deterministic output
        )

        answer = response.choices[0].message.content.strip()
        out_file.write(f"{i}. {q}\nAnswer: {answer}\n\n")

print("✅ Done writing FineTuned_Responses.txt")
