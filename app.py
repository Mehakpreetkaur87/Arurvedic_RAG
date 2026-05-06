"""
================================================================================
AYURVEDA RAG CHATBOT - Streamlit Interactive UI
================================================================================
Interactive web-based chatbot interface for querying Ayurvedic knowledge base.

Features:
- Real-time chat interface with message history
- Retrieved document sources display
- Relevance scoring visualization
- Settings panel for parameter tuning
- Query history management
- Export conversation option
- Similar query detection

Technology Stack:
- Streamlit: Interactive web UI
- Streamlit Chat: Enhanced chat components
- RAG Pipeline: Retrieval & generation
- SQLite: Chat history persistence

Architecture:
    User Input → RAG Search → LLM Generation → Streamlit Display → History Storage

Usage:
    streamlit run app.py
    
    Then open: http://localhost:8501

Author: RAG System
Version: 1.0
================================================================================
"""

import streamlit as st
import logging
import json
import time
from datetime import datetime
from typing import List, Dict
import sqlite3

# Import RAG components
from pipeline import RAGPipeline, SearchResult, TextNormalizer
from llm_handler import get_llm_manager

# ============================================================================
# CONFIGURATION
# ============================================================================

# Page configuration (must be first Streamlit command)
st.set_page_config(
    page_title="Ayurveda RAG Chatbot",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# STREAMLIT THEMING & STYLING
# ============================================================================

# Custom CSS for better UI
st.markdown("""
    <style>
    /* Main container */
    .main {
        padding-top: 2rem;
    }
    
    /* Chat message styling */
    .stChatMessage {
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    /* User message */
    .stChatMessage[data-role="user"] {
        background-color: #e8f4f8;
        border-left: 4px solid #0066cc;
    }
    
    /* Assistant message */
    .stChatMessage[data-role="assistant"] {
        background-color: #f0f8f0;
        border-left: 4px solid #009900;
    }
    
    /* Document cards */
    .doc-card {
        background-color: #f9f9f9;
        border-left: 4px solid #ff9900;
        padding: 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    
    /* Metric styling */
    .metric-card {
        background-color: #f0f0f0;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.2rem 0;
    }
    
    /* Title styling */
    h1 {
        color: #1f4788;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    h2 {
        color: #2d5a2d;
        border-bottom: 2px solid #d4af37;
        padding-bottom: 0.5rem;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    
    /* Expander styling */
    .stExpander {
        border: 1px solid #ddd;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def init_session_state():
    """Initialize Streamlit session state variables."""
    
    # Chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # RAG Pipeline
    if "rag_pipeline" not in st.session_state:
        try:
            st.session_state.rag_pipeline = RAGPipeline(version="v1")
            st.session_state.pipeline_ready = True
        except FileNotFoundError:
            st.session_state.pipeline_ready = False
            logger.error("RAG Pipeline not initialized. Run scripts/initialize.py")
    
    # LLM Manager
    if "llm_manager" not in st.session_state:
        st.session_state.llm_manager = get_llm_manager()
    
    # UI State
    if "show_settings" not in st.session_state:
        st.session_state.show_settings = False
    
    if "show_history" not in st.session_state:
        st.session_state.show_history = False
    
    # Parameters
    if "temperature" not in st.session_state:
        st.session_state.temperature = 0.7
    
    if "top_k" not in st.session_state:
        st.session_state.top_k = 5
    
    if "version" not in st.session_state:
        st.session_state.version = "v1"

# Initialize session state
init_session_state()

# ============================================================================
# SIDEBAR - Settings & Controls
# ============================================================================

def render_sidebar():
    """Render sidebar with settings and controls."""
    
    with st.sidebar:
        st.title("⚙️ Settings")
        
        # Version selection
        version = st.radio(
            "Pipeline Version",
            ["v1", "v2"],
            help="v1: Basic retrieval\nv2: With text normalization (experimental)"
        )
        st.session_state.version = version
        
        # Temperature slider
        st.session_state.temperature = st.slider(
            "Temperature (Creativity)",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.temperature,
            step=0.1,
            help="0.0 = Deterministic\n0.7 = Balanced\n1.0 = Creative"
        )
        
        # Top-K slider
        st.session_state.top_k = st.slider(
            "Retrieved Documents",
            min_value=3,
            max_value=10,
            value=st.session_state.top_k,
            step=1,
            help="Number of documents to use as context for LLM"
        )
        
        st.divider()
        
        # System status
        st.subheader("📊 System Status")
        
        col1, col2 = st.columns(2)
        
        with col1:
            rag_status = "✅ Ready" if st.session_state.pipeline_ready else "❌ Not Ready"
            st.metric("Pipeline", rag_status)
        
        with col2:
            gemini_status = "✅" if st.session_state.llm_manager.gemini.is_available() else "❌"
            st.metric("Gemini", gemini_status)
        
        col1, col2 = st.columns(2)
        
        with col1:
            ollama_status = "✅" if st.session_state.llm_manager.ollama.is_available() else "❌"
            st.metric("Ollama", ollama_status)
        
        with col2:
            msgs = len(st.session_state.messages)
            st.metric("Messages", msgs)
        
        st.divider()
        
        # Chat history controls
        st.subheader("💬 Chat Controls")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Clear Chat"):
                st.session_state.messages = []
                if st.session_state.pipeline_ready:
                    st.session_state.rag_pipeline.clear_chat_history()
                st.rerun()
        
        with col2:
            if st.button("📥 Load History"):
                st.session_state.show_history = not st.session_state.show_history
                st.rerun()
        
        st.divider()
        
        # Info section
        st.subheader("ℹ️ Information")
        
        with st.expander("About This App"):
            st.markdown("""
            **Ayurveda RAG Chatbot**
            
            A retrieval-augmented generation system for Ayurvedic medicine knowledge base.
            
            **Features:**
            - Hybrid search (BM25 + Vector)
            - Reranking for precision
            - LLM-powered responses
            - Chat history
            - Multiple LLM support
            
            **Technologies:**
            - Sentence Transformers (embeddings)
            - FAISS (vector search)
            - Google Gemini API
            - Ollama (local fallback)
            """)
        
        with st.expander("Keyboard Shortcuts"):
            st.markdown("""
            - **Enter**: Send message
            - **Ctrl+A**: Select all
            - **Escape**: Close dialogs
            """)

# ============================================================================
# MAIN CHAT INTERFACE
# ============================================================================

def render_chat_interface():
    """Render main chat interface."""
    
    # Title
    st.markdown("""
    <h1> Ayurveda RAG Chatbot</h1>
    <p style="text-align: center; color: gray;">
    Ask questions about Ayurvedic medicine, treatments, and remedies
    </p>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # Check if pipeline is ready
    if not st.session_state.pipeline_ready:
        st.error(
            "⚠️ RAG Pipeline not initialized!\n\n"
            "Please run the initialization script:\n"
            "```bash\npython scripts/initialize.py\n```"
        )
        return
    
    # Check if any LLM is available
    if not (st.session_state.llm_manager.gemini.is_available() or 
            st.session_state.llm_manager.ollama.is_available()):
        st.error(
            "⚠️ No LLM systems available!\n\n"
            "Please:\n"
            "1. Set GEMINI_API_KEY in .env (for Google Gemini), OR\n"
            "2. Run `ollama serve` (for local LLM)"
        )
        return
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Show metadata if available
            if "metadata" in message:
                with st.expander("📊 Details"):
                    st.json(message["metadata"])
    
    # Chat input
    if prompt := st.chat_input("Ask your question about Ayurveda..."):
        
        # Add user message to history
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            # Status placeholders
            status_placeholder = st.empty()
            response_placeholder = st.empty()
            metadata_placeholder = st.empty()
            
            try:
                # Step 1: Search
                with status_placeholder.container():
                    st.info("🔍 Searching knowledge base...")
                
                search_result = st.session_state.rag_pipeline.search(prompt)
                
                # Step 2: Show retrieved documents
                with status_placeholder.container():
                    st.info(f"📚 Retrieved {len(search_result.documents)} documents in {search_result.processing_time_ms:.1f}ms")
                
                # Display retrieved documents
                # with st.expander(f"📄 Retrieved Sources ({len(search_result.documents)})"):
                #     for i, doc in enumerate(search_result.documents, 1):
                #         st.markdown(f"**Document {i}** (Relevance: {doc.reranker_score*100:.1f}%)")
                        
                #         # Show document content preview
                #         # preview = self.documents[int(doc.id)][:300] + "..."
                #         preview = st.session_state.rag_pipeline.documents[int(doc.id)][:300] + "..."
                #         st.caption(preview)
                        
                #         # Scores
                #         col1, col2, col3 = st.columns(3)
                #         col1.metric("BM25", f"{doc.bm25_score:.2f}")
                #         col2.metric("Vector", f"{doc.vector_score:.2f}")
                #         col3.metric("Rerank", f"{doc.reranker_score:.2f}")
                #         st.divider()
                
                #changed code:
                with st.expander(f"📄 Retrieved Sources ({len(search_result.documents)})"):
                    for i, doc in enumerate(search_result.documents, 1):
                        st.markdown(f"**Document {i}** (Relevance: {doc.reranker_score*100:.1f}%)")
                        st.caption(doc.content[:300] + "...")

                        col1, col2, col3 = st.columns(3)
                        col1.metric("BM25", f"{doc.bm25_score:.2f}")
                        col2.metric("Vector", f"{doc.vector_score:.2f}")
                        col3.metric("Rerank", f"{doc.reranker_score:.2f}")
                        st.divider()




                
                # Step 3: Generate response
                with status_placeholder.container():
                    st.info("🤖 Generating response...")
                
                # Build context
                context = st.session_state.rag_pipeline.get_context(search_result)
                
                # Generate with streaming
                full_response = ""
                
                for chunk in st.session_state.llm_manager.generate_stream(prompt, context):
                    full_response += chunk
                    response_placeholder.markdown(full_response)
                
                # Clear status
                status_placeholder.empty()
                
                # Save to database
                st.session_state.rag_pipeline.save_to_db(
                    prompt,
                    full_response,
                    search_result,
                    model_used="gemini" if st.session_state.llm_manager.gemini.is_available() else "ollama"
                )
                
                # Add to message history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_response,
                    "metadata": {
                        "search_time_ms": search_result.processing_time_ms,
                        "documents_retrieved": len(search_result.documents),
                        "version": st.session_state.version
                    }
                })
                
                # Show success
                st.success("✅ Response generated and saved to history")
            
            except Exception as e:
                logger.error(f"Error generating response: {e}")
                status_placeholder.error(f"❌ Error: {str(e)}")
                response_placeholder.empty()

# ============================================================================
# HISTORY VIEW
# ============================================================================

def render_history():
    """Render chat history panel."""
    
    if st.session_state.show_history and st.session_state.pipeline_ready:
        st.subheader("📜 Chat History")
        
        # Load from database
        history = st.session_state.rag_pipeline.get_chat_history(limit=20)
        
        if history:
            for i, conv in enumerate(reversed(history)):
                with st.expander(f"**{conv['query'][:50]}...** - {conv['timestamp']}", expanded=False):
                # with st.expander(f"**{conv[1][:50]}...** - {conv[5]}", expanded=False):
                    
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown("**Query:**")
                        st.text(conv['query'])
                        
                        st.markdown("**Response:**")
                        st.text(conv['response'][:500] + "...")
                    
                    with col2:
                        st.markdown("**Time:**")
                        st.text(conv['timestamp'])
                        
                        if st.button(f"Load #{i}", key=f"load_{i}"):
                            st.session_state.messages.append({
                                "role": "user",
                                "content": conv[1]
                            })
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": conv[2]
                            })
                            st.rerun()
        else:
            st.info("No chat history yet")

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    """Main application entry point."""
    
    # Render sidebar
    render_sidebar()
    
    # Render main interface
    render_chat_interface()
    
    # Render history if requested
    render_history()

# Run app
if __name__ == "__main__":
    main()
