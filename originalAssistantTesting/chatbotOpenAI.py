import openai
import time
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

transcript_path = "C:\\Users\\kayla.dipaolo\\source\\repos\\openAITesting\\Dillworth+phase+1+handover.txt"
questions_path = "C:\\Users\\kayla.dipaolo\\source\\repos\\openAITesting\\Handoff Questions.txt"
output_path = "openAIAnswers.txt"

# Load transcript
with open(transcript_path, "r", encoding="utf-8") as f:
    transcript_text = f.read()

# Load questions
with open(questions_path, "r", encoding="utf-8") as f:
    questions = [line.strip() for line in f if line.strip()]

# Combine transcript and questions into a single prompt
prompt = f"""Here is a transcript from a construction project handover meeting:

{transcript_text}

Now answer the following questions based on the transcript:
""" + "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

# Create Assistant
assistant = openai.beta.assistants.create(
    name="Transcript QA Assistant",
    instructions="You are an information extraction assistant for Flynn construction. "
                 "You help answer questions based on project handover transcripts. "
                 "Each answer should be accurate, clear, based on evidence in the transcript, and grammatically correct. Use the code interpreter to double check your answers and ensure you are correct."
                 "For each answer make it 3000 tokens and if you can use quotations from the transcript to support your answer.",
    tools=[{"type": "code_interpreter"}],
    model="gpt-3.5-turbo"
)

# Create thread and add message
thread = openai.beta.threads.create()
openai.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content=prompt
)

# Run assistant
run = openai.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant.id,
)

# Wait for completion
while True:
    run_status = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
    if run_status.status == "completed":
        break
    elif run_status.status == "failed":
        raise Exception("Assistant run failed.")
    time.sleep(1)

# Get messages
messages = openai.beta.threads.messages.list(thread_id=thread.id)

# Write to output file
with open(output_path, "w", encoding="utf-8") as out_file:
    for msg in reversed(messages.data):
        if msg.role == "assistant":
            response_text = msg.content[0].text.value
            out_file.write("Assistant's Response:\n\n")
            out_file.write(response_text)
            out_file.write("\n\n")
            break

print(f" Assistant's response saved to:\n{output_path}")