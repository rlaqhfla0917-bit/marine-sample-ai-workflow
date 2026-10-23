"""Local document search: TF-IDF, not production RAG."""
from dataclasses import dataclass
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

@dataclass
class Hit:
    source: str
    text: str
    score: float

def retrieve(query,docs_dir,top_k=3):
    files=sorted([*Path(docs_dir).glob("*.txt"),*Path(docs_dir).glob("*.md")])
    docs=[(f.name,f.read_text(encoding="utf-8")) for f in files]
    if not docs or not query.strip():
        return []
    v=TfidfVectorizer(analyzer="char",ngram_range=(2,4))
    m=v.fit_transform([text for _,text in docs]+[query])
    scores=cosine_similarity(m[-1],m[:-1]).ravel()
    indices=sorted(range(len(docs)),key=lambda i:scores[i],reverse=True)[:top_k]
    return [Hit(docs[i][0],docs[i][1][:1200],float(scores[i])) for i in indices if scores[i]>0]
