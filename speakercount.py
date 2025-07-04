from collections import Counter
import re
from docx import Document

def count_turns_in_transcript(docx_path):
    """
    Reads a .docx transcript and returns a Counter mapping
    speaker names to the number of times they spoke.
    """
    # Match lines like “Name   0:13” → capture “Name”
    header_re = re.compile(r'^(.+?)\s+\d{1,2}:\d{2}')
    counts = Counter()

    doc = Document(docx_path)
    for para in doc.paragraphs:
        text = para.text.strip()
        m = header_re.match(text)
        if m:
            speaker = m.group(1)
            counts[speaker] += 1

    return counts

if __name__ == "__main__":
    # ←– Hard-code your .docx full path here:
    transcript_file ="C:\\Users\\kayla.dipaolo\\OneDrive - Flynn Group of Companies\\AI Initiative\\provo river water treatment\\Provo River Water Treatment Turnover.docx"
    counts = count_turns_in_transcript(transcript_file)
    for speaker, turns in counts.most_common():
        print(f"{speaker}: {turns}")
