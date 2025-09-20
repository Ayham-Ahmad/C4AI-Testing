import logging
from typing import List, Tuple, Any

from langchain.prompts import ChatPromptTemplate
from langchain.load import dumps, loads
import LLM  # <-- keep your existing LLM wrapper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Constants
NUM_QUERY = 4
TOP_K = 30


def generate_query(question: str, num_query: int = NUM_QUERY) -> List[str]:
    """
    Generate multiple pseudo-queries for RAG.
    For tutorials/documents, queries should be variations of the user's question.
    """
    logging.info("Generating RAG queries for question: %s", question)

    template = (
        "You are a helpful assistant generating diverse retrieval queries for a tutorial/document Q&A system.\n"
        "The purpose is to help retrieve relevant tutorial snippets (like W3Schools code examples).\n\n"
        "Given the user's question, generate {num_query} different short queries that capture the intent "
        "but use varied wording or focus.\n\n"
        "Keep each query concise (max 15 words).\n"
        "Do not include explanations or numbering, just the queries.\n\n"
        "Question: {question}\n"
        "Queries:"
    )

    prompt = ChatPromptTemplate.from_template(template).format(
        question=question,
        num_query=num_query
    )
    raw_output = LLM.run_llm(prompt, question)

    raw_output = LLM.run_llm(prompt, question)

    # Ensure raw_output is string
    if not isinstance(raw_output, str):
        raw_output = "".join(raw_output)

    queries = [line.strip() for line in raw_output.splitlines() if line.strip()]
    return queries[:num_query]


def generate_hyde_document(question: str) -> str:
    """
    Generate a Hypothetical Document (HyDE) answer for the question.
    This acts like a synthetic tutorial/example to improve retrieval.
    """
    logging.info("Generating HyDE document for question: %s", question)

    template = (
        "You are a helpful assistant that writes a plausible tutorial-style explanation or code snippet "
        "that could answer the user's question.\n\n"
        "Question: {question}\n"
        "Hypothetical Answer:"
    )
    prompt = ChatPromptTemplate.from_template(template).format(question=question)
    return LLM.run_llm(prompt, question).strip()


def reciprocal_rank_fusion(
    ranked_lists: List[List[Any]],
    k: int = 5
) -> List[Tuple[Any, float]]:
    """
    Perform Reciprocal Rank Fusion on multiple ranked document lists.
    Returns a list of (document, fused_score) sorted by score descending.
    """
    scores = {}
    for results in ranked_lists:
        for rank, doc in enumerate(results):
            key = dumps(doc)
            scores.setdefault(key, 0.0)
            scores[key] += 1.0 / (rank + k)

    fused = [(loads(key), score) for key, score in scores.items()]
    fused.sort(key=lambda x: x[1], reverse=True)
    return fused


def rag_fusion_chain(question: str, retriever: Any, top_k: int = TOP_K) -> Tuple[str, List[str]]:
    """
    Execute a RAG fusion chain for tutorial chatbot:
    1. Generate diverse queries
    2. Retrieve documents per query
    3. Apply Reciprocal Rank Fusion (RRF)
    4. Return fused context and used queries
    """
    try:
        logging.info("Starting RAG fusion chain for question: %s", question)

        # Step 1: Generate retrieval queries
        queries = generate_query(question)
        logging.info("Generated queries: %s", queries)

        # Step 2: Retrieve documents per query
        ranked_lists = []
        for q in queries:
            try:
                results = retriever.invoke(q)
                ranked_lists.append(results)
            except Exception as err:
                logging.error("Retrieval error for '%s': %s", q, err)

        # Step 3: Fuse and rank
        fused = reciprocal_rank_fusion(ranked_lists)

        # Step 4: Extract top-K contents
        top_docs = [doc.page_content for doc, _ in fused[:top_k]]
        context = "\n\n".join(top_docs)

        return context, queries

    except Exception as e:
        logging.exception("Error in rag_fusion_chain: %s", e)
        return "", []
