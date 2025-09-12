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
if 'chat_history' not in st.session_state: 
    st.session_state.chat_history = [] 

if 'user_input' not in st.session_state: 
    st.session_state.user_input = "" 

@st.cache_resource 
def load_vectorstore(): 
    return embedding.get_vectorstore(create_new_vectorstore=False) 

vectorstore = load_vectorstore() 

# --- Default fallbacks --- 
def defualtContent(): 
    return "This is a defualt content, if you read this just return \"There is no content here\" whatever you are asked for." 
def defualtContext(): 
    return "This is a defualt context, if you read this just return \"There is no context here\" whatever you are asked for." 
def defualtQuestion(): 
    return "This is a defualt question, if you read this just return \"There is no question here\" whatever you are asked for." 
def defualtHistory(): 
    return "This is a defualt history, if you read this just return \"There is no history here\" whatever you are asked for." 

# --- Prompt construction --- 
def generate_prompt(content=defualtContent(), context=defualtContext(), question=defualtQuestion(), history=defualtHistory()): 
    template = """{content} 

    Context: 
    {context} 

    History: 
    {history} 

    Task: {question} 
    """ 
    prompt = ChatPromptTemplate.from_template(template) 
    return prompt.format(content=content, context=context, question=question, history=history) 

# --- Log unsupported queries ---
def log_unsupported(query: str):
    normalized = query.lower().strip()
    with open(UNSUPPORTED_FILE, "a", encoding="utf-8") as f:
        f.write(normalized + "\n")

# --- Response generation --- 
def generate_response(query): 
    history = "\n".join( 
        f"{msg['speaker']}: {msg['message']}" 
        for msg in st.session_state.chat_history 
        if msg['speaker'] in ('User', 'Tutor') 
    ) 
    
    context, content = RAG.get_context(query, vectorstore) 
    final_prompt = generate_prompt(content, context, query, history) 
    response = LLM.LLM(final_prompt, query) 

    # If LLM says unsupported → log query
    unsupported_message = "❌ Sorry, this topic is not supported yet. Please wait for an update."
    if response.strip() == unsupported_message:
        log_unsupported(query)

    return response 

# --- Main chat handler --- 
def handle_chat(): 
    query = st.session_state.user_input.strip() 
    if not query: 
        return 

    # Store user query 
    st.session_state.chat_history.append({ 
        "speaker": "User", 
        "message": query, 
        "time": None 
    }) 

    start_time = time.time() 
    response = generate_response(query) 
    response_time = time.time() - start_time 

    # Save bot response with timer 
    st.session_state.chat_history.append({ 
        "speaker": "Tutor", 
        "message": response, 
        "time": response_time 
    }) 

    st.session_state.user_input = "" 

# --- UI --- 
st.title("💻 Coding Tutor Chatbot") 

# Chat history display 
with st.container(): 
    for msg in st.session_state.chat_history: 
        if msg["speaker"] == "User": 
            st.markdown(f"**🧑 You:** {msg['message']}") 
        else: 
            st.markdown(f"**🤖 Tutor:** {msg['message']}") 
            if msg['time'] is not None: 
                st.markdown(f"_⏱️ Response Time: {msg['time']:.2f} seconds_") 

# User input field 
with st.empty(): 
    st.text_input( 
        "Your message", 
        key="user_input", 
        placeholder="Ask me for exercises or tutorials (e.g., 'Make 5 exercises for Python beginners' or 'Make a Pandas tutorial')...", 
        on_change=handle_chat, 
        label_visibility="collapsed" 
    ) 
