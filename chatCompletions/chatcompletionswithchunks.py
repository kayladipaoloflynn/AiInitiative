import os
import openai
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# === FILE PATHS ===
transcript_path = "C:\\Users\\kayla.dipaolo\\source\\repos\\openAITesting\\Dillworth+phase+1+handover.txt"
questions_path = "C:\\Users\\kayla.dipaolo\\source\\repos\\openAITesting\\Handoff Questions.txt"
output_path = "chatCompletionsAnswers.txt"

# === STEP 1: LOAD AND CHUNK TRANSCRIPT ===
loader = TextLoader(transcript_path)
documents = loader.load()

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_documents(documents)

# === STEP 2: EMBED CHUNKS INTO VECTOR STORE ===
embedding_model = OpenAIEmbeddings(openai_api_key=openai.api_key)
vectorstore = FAISS.from_documents(chunks, embedding_model)

# === STEP 3: SET UP RETRIEVAL-BASED QA CHAIN ===
llm = ChatOpenAI(model_name="gpt-4o", temperature=0, openai_api_key=openai.api_key)
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=vectorstore.as_retriever(search_type="similarity", k=4),
    return_source_documents=True
)

# === STEP 4: LOAD QUESTIONS AND ANSWER THEM ===
with open(questions_path, "r", encoding="utf-8") as f:
    questions = [line.strip() for line in f if line.strip()]

with open(output_path, "w", encoding="utf-8") as out_file:
    for i, question in enumerate(questions, 1):
        result = qa_chain.run(question)
        out_file.write(f"{i}. {question}\n")
        out_file.write(f"Answer: {result}\n\n")

print(f"✅ All answers written to: {output_path}")
