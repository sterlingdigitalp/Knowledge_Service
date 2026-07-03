"""Entity extraction stopwords and false-positive filters."""

from __future__ import annotations

# Capitalized words that are NOT entities (from degradation forensics)
ENTITY_FALSE_POSITIVES = frozenset({
    "rather", "like", "there", "welcome", "command", "however", "this", "that",
    "these", "those", "they", "them", "their", "here", "where", "when", "what",
    "which", "who", "how", "why", "because", "although", "though", "while",
    "since", "until", "after", "before", "during", "within", "without", "between",
    "among", "against", "toward", "towards", "into", "onto", "upon", "about",
    "above", "below", "under", "over", "through", "across", "along", "around",
    "behind", "beside", "beyond", "inside", "outside", "visit", "figure",
    "fourth", "sons", "spiel", "agents", "better", "getting", "look", "going",
    "really", "actually", "basically", "literally", "honestly", "obviously",
    "clearly", "simply", "maybe", "perhaps", "probably", "definitely",
    "certainly", "absolutely", "completely", "entirely", "totally", "mostly",
    "mainly", "primarily", "especially", "particularly", "specifically",
    "generally", "typically", "usually", "often", "sometimes", "never",
    "always", "everyone", "somebody", "someone", "anyone", "anything",
    "everything", "nothing", "something", "another", "other", "others",
    "first", "second", "third", "next", "last", "new", "old", "good", "great",
    "best", "worst", "big", "small", "large", "little", "much", "many", "few",
    "several", "various", "different", "similar", "same", "such", "very",
    "quite", "just", "only", "even", "still", "already", "yet", "again",
    "also", "too", "well", "right", "left", "back", "forward", "today",
    "tomorrow", "yesterday", "now", "then", "soon", "later", "earlier",
})

ENTITY_STOPWORDS = ENTITY_FALSE_POSITIVES | frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "as", "is", "was", "are", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "can", "not", "no", "so", "if", "it", "its", "we", "you", "i",
    "he", "she", "his", "her", "my", "your", "our", "me", "him", "us",
})