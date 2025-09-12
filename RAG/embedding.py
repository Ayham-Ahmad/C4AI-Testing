import chromadb
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ===== CONFIG =====
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
SAVED_EMBED_PATH = os.getenv("SAVED_EMBED_PATH", "embedded")
DATA_PATH = os.getenv("DATA_PATH", "data/W3School_codes_only.txt")
COLLECTION_NAME = "w3school_codes"
# ==================

def embed(splits):
    logging.info("Embedding...")
    embedding = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    client = chromadb.PersistentClient(path=SAVED_EMBED_PATH)
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embedding,
        client=client,
        collection_name=COLLECTION_NAME,
        persist_directory=SAVED_EMBED_PATH,
    )
    logging.info(f"✅ Vector store created and persisted at: {SAVED_EMBED_PATH}")
    return vectorstore

def split(data):
    logging.info("Chunking...")
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=384,  # size of each chunk
        chunk_overlap=64,  # overlap between chunks
    )
    return text_splitter.split_documents(data)

def loader():
    logging.info("Loading data...")
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"{DATA_PATH} does not exist.")

    all_txt_docs = []
    if os.path.isfile(DATA_PATH) and DATA_PATH.endswith(".txt"):
        logging.info(f"Processing file: {DATA_PATH}")
        with open(DATA_PATH, "r", encoding="utf-8") as file:
            content = file.read()

        # Everything in one Document, chunking happens later
        metadata = {"source_file": os.path.basename(DATA_PATH)}
        all_txt_docs.append(Document(page_content=content, metadata=metadata))
    else:
        raise ValueError("Expected a .txt file path, but got something else.")

    return all_txt_docs

def get_vectorstore(create_new_vectorstore: bool = True):
    embedding = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    if not create_new_vectorstore:
        logging.info("Vectorstore found. Loading existing...")
        client = chromadb.PersistentClient(path=SAVED_EMBED_PATH)
        return Chroma(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding_function=embedding,
        )
    else:
        logging.info("No existing vectorstore found. Creating a new one...")
        data = loader()
        splits = split(data)
        return embed(splits)

if __name__ == "__main__":
    # Run once to create and persist vectorstore
    get_vectorstore(create_new_vectorstore=True)
