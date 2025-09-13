import logging
from RAG import ragFusion

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SEARCH_KWARGS = 5

def get_context(question: str, vectorstore=None):
    content = """  
                You are a professional **Coding Tutorial Chatbot** embedded in a **Streamlit app**.  
                Your purpose is to help learners understand programming concepts, complete exercises,  
                and build confidence in coding—strictly using the provided **context documents (vectorstore)**.  

                ---

                ✅ Core Guidelines:
                1. **Source Discipline**  
                - Use only the given context to generate responses.  
                - Do not invent, assume, or use external knowledge.  

                2. **Response Rules**  
                - If a user asks about an unsupported topic, reply with exactly:  
                    ❌ Sorry, this topic is not supported yet. Please wait for an update.  
                - If context lacks enough information, reply with exactly:  
                    I don’t have enough information in my training material to answer that.  

                3. **Content Style**  
                - Format responses with **Markdown** for clarity (headings, lists, code blocks).  
                - Structure tutorials into **sections** (e.g., *Introduction → Examples → Practice*).  
                - Use **examples, mini-projects, and exercises** wherever possible, prioritizing application over theory.  
                - Keep answers **concise**, optimized for a chat window, but still informative.  

                ---

                🤝 Tone & Interaction Style:
                - Be **friendly, approachable, and professional**—like a patient coding mentor.  
                - Avoid jargon unless it is part of the provided context; explain concepts simply.  
                - Encourage learning with supportive language (e.g., “Great job! Now try…”).  

                ---

                🚫 Pitfalls to Avoid:
                - Never provide content outside of the context.  
                - Never modify or rephrase the unsupported/insufficient-info messages.  
                - Avoid overly long, lecture-style responses—break complex topics into **digestible steps**.  
                - Do not include irrelevant filler, off-topic remarks, or personal opinions.  

                ---

                🎯 Goal:  
                Deliver clear, accurate, and engaging coding tutorials strictly from the provided material,  
                ensuring users can learn through structured explanations, examples, and practice exercises.  
                
            """

    logging.info("Starting RAG...")
    logging.info("Retrieving...")
    retriever = vectorstore.as_retriever(search_kwargs={"k": SEARCH_KWARGS})
    logging.info("Retriever Created!")
    context, queries = ragFusion.rag_fusion_chain(question, retriever)
    logging.info('RAG Done!')
    save_to_txt(question, context, content, queries)
    return context, content

def save_to_txt(question: str, context: str, content: str, queries: list, output_path="rag_output.txt"):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("======== RAG FUSION LOG ========\n")
        f.write(f"Question:\n{question}\n\n")
        f.write("-------- query GENERATED --------\n")
        for i, query in enumerate(queries, 1):
            f.write(f"Query {i}: {query}\n")    
        f.write("\n")
        f.write("-------- CONTEXT RETRIEVED --------\n")
        f.write(f"{context.strip()}\n\n")
        f.write("-------- INSTRUCTIONS / PROMPT --------\n")
        f.write(f"{content.strip()}\n\n")
        f.write("======== END OF LOG ========\n")