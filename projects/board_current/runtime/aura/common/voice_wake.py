"""Audio-only wake intent. A wake word never proves personal identity."""
import re
from common.character_profile import selected_profile

DEFAULT_WORDS = selected_profile().wake_words


def wake_request(text, words=DEFAULT_WORDS):
    """Return the trailing request, '' for wake only, None for no wake.

    Names may prefix a request directly. Single-character interjections must
    stand alone or have an explicit punctuation/space boundary, so ordinary
    words such as 哎呀 do not activate a conversation.
    """
    if not isinstance(text, str):
        return None
    text = text.strip()
    for word in sorted(words, key=len, reverse=True):
        if not isinstance(word, str) or not word or not text.startswith(word):
            continue
        tail = text[len(word):]
        if len(word) == 1 and tail and not re.match(r'[\s，,。.!！?？、：:]', tail):
            continue
        return re.sub(r'^[\s，,。.!！?？、：:]+', '', tail).strip()
    return None
