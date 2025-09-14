import sys
import time
import streamlit as st
from langchain.prompts import ChatPromptTemplate
import os

import RAG
import LLM
from RAG import embedding, RAG

# Temporary torch workaround (fixes some HF models on Streamlit Cloud)
sys.modules.setdefault('torch.classes', type('FakeModule', (), {'__path__': []})())

# File paths
UNSUPPORTED_FILE = os.path.join("topics", "unsupported_topics.txt")

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "user_input" not in st.session_state:
    st.session_state.user_input = ""

if "pending_query" not in st.session_state:
    st.session_state.pending_query = None


@st.cache_resource
def load_vectorstore():
    return embedding.get_vectorstore(create_new_vectorstore=False)


vectorstore = load_vectorstore()

# --- Default fallbacks ---
def default_content():
    return 'This is a default content. If you see this, respond: "There is no content here".'


def default_context():
    return 'This is a default context. If you see this, respond: "There is no context here".'


def default_question():
    return 'This is a default question. If you see this, respond: "There is no question here".'


def default_history():
    return 'This is a default history. If you see this, respond: "There is no history here".'


# --- Prompt construction ---
def generate_prompt(
    content=default_content(),
    context=default_context(),
    question=default_question(),
    history=default_history(),
):
    template = """{content}

Context:
{context}

History:
{history}

Task: {question}
"""
    prompt = ChatPromptTemplate.from_template(template)
    return prompt.format(
        content=content, context=context, question=question, history=history
    )


# --- Log unsupported queries ---
def log_unsupported(query: str):
    normalized = query.lower().strip()
    with open(UNSUPPORTED_FILE, "a", encoding="utf-8") as f:
        f.write(normalized + "\n")


# --- Generate context and prompt for a query ---
def prepare_prompt(query):
    history = "\n".join(
        f"{msg['speaker']}: {msg['message']}"
        for msg in st.session_state.chat_history
        if msg["speaker"] in ("User", "Tutor")
    )
    context, content = RAG.get_context(query, vectorstore)
    final_prompt = generate_prompt(content, context, query, history)
    return final_prompt


# --- Chat handler ---
def handle_chat():
    query = st.session_state.user_input.strip()
    if not query:
        return

    # Store user query
    st.session_state.chat_history.append(
        {
            "speaker": "User",
            "message": query,
            "time": None,
        }
    )

    # mark for streaming in the main loop
    st.session_state.pending_query = query

    # clear input field
    st.session_state.user_input = ""


# --- UI ---
st.title("💻 Coding Tutor Chatbot")

# Chat history container
chat_container = st.container()
with chat_container:
    for msg in st.session_state.chat_history:
        if msg["speaker"] == "User":
            st.markdown(f"**🧑 You:** {msg['message']}")
        else:
            st.markdown(f"**🤖 Tutor:** {msg['message']}")
            if msg.get("time") is not None:
                st.markdown(f"_⏱️ Response Time: {msg['time']:.2f} seconds_")


# User input field
with st.empty():
    st.text_input(
        "Your message",
        key="user_input",
        placeholder="Ask me for exercises or tutorials (e.g., 'Make 5 exercises for Python beginners' or 'Make a Pandas tutorial')...",
        on_change=handle_chat,
        label_visibility="collapsed",
    )


# --- Streaming execution ---
if st.session_state.get("pending_query"):
    query = st.session_state.pending_query
    st.session_state.pending_query = None

    final_prompt = prepare_prompt(query)
    placeholder = chat_container.empty()

    response_text = ""
    start_time = time.time()
    error_msg = None

    try:
        # Stream response chunks from LLM
        for chunk in LLM.run_llm(final_prompt, query):
            response_text += chunk
            placeholder.markdown(f"**🤖 Tutor:** {response_text}")

    except Exception as e:
        error_msg = f"⚠️ Error generating response: {e}"

    finally:
        final_message = error_msg if error_msg else response_text
        response_time = None if error_msg else time.time() - start_time

        # Save to history
        st.session_state.chat_history.append(
            {
                "speaker": "Tutor",
                "message": final_message,
                "time": response_time,
            }
        )

        # Render final version (don’t empty the placeholder)
        if error_msg:
            placeholder.markdown(final_message)
        else:
            placeholder.markdown(
                f"**🤖 Tutor:** {final_message}\n\n_⏱️ Response Time: {response_time:.2f} seconds_"
            )

        # If unsupported message, log it
        unsupported_message = "❌ Sorry, this topic is not supported yet. Please wait for an update."
        if final_message.strip() == unsupported_message:
            log_unsupported(query)
