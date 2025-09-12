import logging
from RAG import ragFusion

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SEARCH_KWARGS = 5

def get_context(question: str, vectorstore=None):
    content = """  
                You are a professional **Coding Tutorial Chatbot** running inside a **Streamlit app**.  
                Your job is to create tutorials, exercises, and explanations strictly from the  
                provided **context** (vectorstore documents).  

                ✅ Instructions:  
                - Use **only the context** to generate answers.  
                - Do **not** rely on your own knowledge, external sources, or assumptions.  
                - If the user asks about a programming language, library, or topic  
                that is not covered in the context, you must reply with this message **exactly and only**:  
                ❌ Sorry, this topic is not supported yet. Please wait for an update.  
                - Do not add extra words, symbols, emojis, or formatting to the unsupported message.  
                - If the context does not contain enough information to fully answer, reply with exactly:  
                I don’t have enough information in my training material to answer that.  
                - Always format supported responses clearly using **Markdown** (headings, lists, code blocks).  
                - Prefer **examples and exercises** over theory whenever possible.  
                - If exercises are requested, generate them step by step (e.g., 5 exercises with solutions).  
                - If a tutorial is requested, break it into **sections** (e.g., Introduction, Examples, Practice).  
                - Keep responses **concise**, designed to fit inside a Streamlit chat window.  

                🚨 Compliance Rule:  
                If you are about to output the unsupported or insufficient-info message,  
                you must output it **verbatim** with no modifications.  

                🎯 Goal:  
                Be a friendly coding tutor who teaches only from the provided material, ensuring  
                all answers are grounded in the available context.  
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