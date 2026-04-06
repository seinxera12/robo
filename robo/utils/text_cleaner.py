import re

def clean_for_tts(text, language):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r'[*_`#>\[\]\(\)]', '', text)
    text = re.sub(r'http\S+', '', text)

    if language != 'ja':
        text = re.sub(r'[^\x00-\x7F]+', '', text)

    return re.sub(r'\s+', ' ', text).strip()