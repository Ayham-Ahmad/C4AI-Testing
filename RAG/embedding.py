import os
import json
import logging
import chromadb
from pathlib import Path
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ===== CONFIG =====
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
SAVED_EMBED_PATH = os.getenv("SAVED_EMBED_PATH", "embeddedV2")
DATA_PATH = os.getenv("DATA_PATH", "W3_Tutorials_done")  # folder containing JSON files
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
        chunk_size=384,
        chunk_overlap=64,
    )
    return text_splitter.split_documents(data)


def loader():
    logging.info("Loading JSON data...")
    data_path = Path(DATA_PATH)

    if not data_path.exists():
        raise FileNotFoundError(f"{DATA_PATH} does not exist.")

    all_docs = []

    # Iterate over JSON files
    for json_file in data_path.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            language = data.get("language", "UNKNOWN")
            tutorials = data.get("tutorials", [])

            for tutorial in tutorials:
                title = tutorial.get("title", "UNTITLED")
                codes = tutorial.get("code", [])

                for code in codes:
                    text = code.get("text", "").strip()
                    if not text:
                        continue

                    # Prepare clean content for embedding
                    page_content = f"{language}\n{title}\n{text}"
                    metadata = {
                        "source_file": json_file.name,
                        "language": language,
                        "title": title,
                    }

                    all_docs.append(Document(page_content=page_content, metadata=metadata))

            logging.info(f"✅ Processed {json_file.name}, found {len(all_docs)} docs so far.")

        except Exception as e:
            logging.error(f"❌ Failed to process {json_file.name}: {e}")

    return all_docs


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
