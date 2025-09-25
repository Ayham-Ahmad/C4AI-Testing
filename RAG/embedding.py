import os
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
SAVED_EMBED_PATH = os.getenv("SAVED_EMBED_PATH", "data/embeddedV1")
DATA_PATH = os.getenv("DATA_PATH", "data/W3_Tutorials_All_txt")
COLLECTION_NAME = "w3school_codes"
# ==================


def embed(splits):
    msg = "Embedding..."
    logging.info(msg)
    print(msg)

    embedding = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    client = chromadb.PersistentClient(path=SAVED_EMBED_PATH)
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embedding,
        client=client,
        collection_name=COLLECTION_NAME,
        persist_directory=SAVED_EMBED_PATH,
    )

    msg = f"✅ Vector store created and persisted at: {SAVED_EMBED_PATH}"
    logging.info(msg)
    print(msg)
    return vectorstore


def split(data):
    msg = "Chunking..."
    logging.info(msg)
    print(msg)

    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=384,
        chunk_overlap=64,
    )
    return text_splitter.split_documents(data)


def loader():
    msg = "Loading TXT data..."
    logging.info(msg)
    print(msg)

    data_path = Path(DATA_PATH)

    if not data_path.exists():
        raise FileNotFoundError(f"{DATA_PATH} does not exist.")

    all_docs = []

    # Iterate over TXT files
    for txt_file in data_path.glob("*.txt"):
        try:
            with open(txt_file, "r", encoding="utf-8") as f:
                text = f.read().strip()

            if not text:
                continue

            metadata = {"source_file": txt_file.name}
            all_docs.append(Document(page_content=text, metadata=metadata))

            msg = f"✅ Processed {txt_file.name}, total docs so far: {len(all_docs)}"
            logging.info(msg)
            print(msg)

        except Exception as e:
            msg = f"❌ Failed to process {txt_file.name}: {e}"
            logging.error(msg)
            print(msg)

    return all_docs


def get_vectorstore(create_new_vectorstore: bool = True):
    embedding = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    if not create_new_vectorstore:
        msg = "Vectorstore found. Loading existing..."
        logging.info(msg)
        print(msg)

        client = chromadb.PersistentClient(path=SAVED_EMBED_PATH)
        return Chroma(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding_function=embedding,
        )
    else:
        msg = "No existing vectorstore found. Creating a new one..."
        logging.info(msg)
        print(msg)

        data = loader()
        splits = split(data)
        return embed(splits)


if __name__ == "__main__":
    # Run once to create and persist vectorstore
    get_vectorstore(create_new_vectorstore=True)
