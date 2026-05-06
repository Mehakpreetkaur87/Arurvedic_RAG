"""
================================================================================
INITIALIZATION SCRIPT - Build Indices from Knowledge Base
================================================================================
Processes raw knowledge base files and builds all necessary indices:
- BM25 index (keyword search)
- FAISS vector index (semantic search)
- Metadata JSON (document info)
- SQLite database (chat history)

Steps:
1. Load knowledge base files (JSON + TXT)
2. Parse and chunk documents
3. Build BM25 index
4. Generate embeddings and build FAISS index
5. Save metadata
6. Initialize SQLite database

Prerequisites:
- Place knowledge base files in data/knowledge_base/ directory
- Supported formats: .json, .txt, .md

Usage:
    python scripts/initialize.py
    
Options:
    --rebuild: Force rebuild all indices
    --batch_size: Processing batch size (default: 16)
    --chunk_size: Characters per chunk (default: 800)

Author: RAG System
Version: 1.0
================================================================================
"""

import os
import sys
import json
import pickle
import logging
from pathlib import Path
from typing import List, Dict, Tuple
import argparse
import time
import google.generativeai as genai

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import RAG components
from pipeline import (
    BM25Engine, VectorSearchEngine, TextNormalizer,
    VECTOR_DB_PATH, METADATA_PATH, CHUNK_SIZE, CHUNK_OVERLAP,
    EMBEDDING_MODEL, DEBUG_MODE
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

KNOWLEDGE_BASE_PATH = Path("data/knowledge_base")
OUTPUT_DIR = Path(VECTOR_DB_PATH)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# DOCUMENT PROCESSING
# ============================================================================

class DocumentProcessor:
    """
    Process knowledge base files and create chunks for indexing.
    
    Supports:
    - JSON (structured with disease info)
    - TXT (unstructured text)
    - MD (markdown)
    
    Chunking strategy:
    - Split by character count
    - Overlap for context preservation
    - Preserve paragraph boundaries when possible
    """
    
    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        """
        Initialize document processor.
        
        Args:
            chunk_size: Characters per chunk
            chunk_overlap: Characters overlapped between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.documents = []
        self.metadata = []
    
    def load_knowledge_base(self) -> Tuple[List[str], List[Dict]]:
        """
        Load and process all knowledge base files.
        
        Process:
        1. Find all .json, .txt, .md files
        2. Parse based on format
        3. Create chunks
        4. Extract metadata
        
        Returns:
            Tuple of (documents_list, metadata_list)
        """
        
        logger.info(f"Loading knowledge base from: {KNOWLEDGE_BASE_PATH}")
        
        if not KNOWLEDGE_BASE_PATH.exists():
            logger.warning(f"Knowledge base path not found: {KNOWLEDGE_BASE_PATH}")
            logger.info("Creating sample knowledge base...")
            self._create_sample_kb()
        
        # Find all data files
        json_files = list(KNOWLEDGE_BASE_PATH.glob("*.json"))
        txt_files = list(KNOWLEDGE_BASE_PATH.glob("*.txt"))
        md_files = list(KNOWLEDGE_BASE_PATH.glob("*.md"))
        
        all_files = json_files + txt_files + md_files
        
        logger.info(f"Found {len(json_files)} JSON, {len(txt_files)} TXT, {len(md_files)} MD files")
        
        # Process each file
        for file_path in all_files:
            logger.info(f"Processing: {file_path.name}")
            
            if file_path.suffix == ".json":
                self._process_json(file_path)
            elif file_path.suffix in [".txt", ".md"]:
                self._process_text(file_path)
        
        logger.info(f"Total documents created: {len(self.documents)}")
        logger.info(f"Total metadata entries: {len(self.metadata)}")
        
        return self.documents, self.metadata
    
    def _process_json(self, file_path: Path):
        """Process JSON structured knowledge base."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle list of objects
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = [data]
            else:
                logger.warning(f"Unexpected JSON structure in {file_path}")
                return
            
            # Process each item
            for item in items:
                if not isinstance(item, dict):
                    continue
                
                # Extract disease title
                title = item.get('title', 'Unknown')
                title_dev = item.get('title_dev', '')
                
                # Build full text from disease fields
                text_parts = [
                    f"Title: {title}",
                    f"Sanskrit: {title_dev}",
                ]
                
                # Add all text fields
                for field in ['intro', 'symptoms', 'treatment', 'simple_preparations',
                             'compound_preparations', 'pathya', 'apathya']:
                    if field in item and item[field]:
                        text_parts.append(f"{field.upper()}: {item[field]}")
                
                # Add regional names
                if 'regional_names' in item:
                    regional = item['regional_names']
                    if isinstance(regional, dict):
                        region_str = ", ".join([f"{k}: {v}" for k, v in regional.items()])
                        text_parts.append(f"REGIONAL NAMES: {region_str}")
                
                full_text = "\n".join(text_parts)
                
                # Create chunks
                chunks = self._chunk_text(full_text)
                
                # Add to documents and metadata
                for chunk in chunks:
                    self.documents.append(chunk)
                    
                    # Metadata for each chunk
                    metadata = {
                        "source": file_path.name,
                        "disease_title": title,
                        "disease_title_dev": title_dev,
                        "type": "disease",
                        "id": item.get('id', 'unknown')
                    }
                    
                    if 'regional_names' in item:
                        metadata['regional_names'] = item['regional_names']
                    
                    self.metadata.append(metadata)
        
        except Exception as e:
            logger.error(f"Error processing JSON {file_path}: {e}")
    
    def _process_text(self, file_path: Path):
        """Process TXT/MD unstructured text."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Split into sections (separated by ==== or -----)
            sections = self._split_sections(text)
            
            for section in sections:
                # Create chunks from section
                chunks = self._chunk_text(section)
                
                for chunk in chunks:
                    self.documents.append(chunk)
                    
                    # Metadata
                    metadata = {
                        "source": file_path.name,
                        "type": "text"
                    }
                    self.metadata.append(metadata)
        
        except Exception as e:
            logger.error(f"Error processing TXT {file_path}: {e}")
    
    def _split_sections(self, text: str) -> List[str]:
        """Split text into sections by delimiters."""
        # Split by common delimiters
        sections = text.split('\n=====')
        sections = [s for s in sections if len(s.strip()) > 50]  # Filter small sections
        return sections
    
    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks of specified size.
        
        Strategy:
        1. Split by paragraph if possible
        2. Combine into chunks of CHUNK_SIZE
        3. Add overlap for context
        
        Args:
            text: Text to chunk
            
        Returns:
            List of chunks
        """
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            # Skip very short paragraphs
            if len(para.strip()) < 50:
                continue
            
            # If adding this paragraph exceeds chunk size, save current and start new
            if len(current_chunk) + len(para) > self.chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # Add overlap
                current_chunk = current_chunk[-self.chunk_overlap:] + "\n" + para
            else:
                current_chunk += "\n" + para if current_chunk else para
        
        # Add last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return [c for c in chunks if len(c.strip()) > 50]  # Filter very short chunks
    
    def _create_sample_kb(self):
        """Create sample knowledge base for testing."""
        KNOWLEDGE_BASE_PATH.mkdir(parents=True, exist_ok=True)
        
        sample_data = [
            {
                "id": "1",
                "title": "AGNIDAGDHA",
                "title_dev": "अग्निदग्ध",
                "regional_names": {
                    "Eng": "Burns and scalds",
                    "Hin": "Jalna",
                    "San": "Agnidagdha"
                },
                "intro": "Injury caused with the contact of excessive heat is known as Agnidagdha. According to the degree of the injury, burns are classified into four groups viz. Pluṣṭa, Durdagdha, Samyagdagdha and Atidagdha.",
                "symptoms": "1. Pluṣṭa: These are the simple burns where colour of the skin is considerably affected. 2. Durdagdha: The burns in which small or large vesicles appear with surrounding redness.",
                "treatment": "Cold water should not be applied on the burns and wherever indicated warm water may be used.",
                "simple_preparations": "1. Fresh juice (Svarasa) obtained from Ghṛtakumārī (aloe). 2. Mixture of Atasī Taila (linseed oil) and honey in equal parts.",
                "compound_preparations": "1. Atasyādi Lepa 2. Ṭaṅkaṇa Malhara"
            },
            {
                "id": "2",
                "title": "AGNIMANDYA",
                "title_dev": "अग्निमान्द्य",
                "regional_names": {
                    "Eng": "Dyspepsia",
                    "Hin": "Apacana",
                    "San": "Agnimandya"
                },
                "intro": "Agnimāndya is a condition in which food is not properly digested due to the diminished power of Jaṭharāgni (digestive juices).",
                "symptoms": "Indigestion, diminished appetite, loss of taste, salivation, sour eructation and heaviness in the abdomen.",
                "treatment": "In Agnimāndya such drugs and articles of diet should be given which increase the Agni and decrease Kapha.",
                "simple_preparations": "1. Śuṇṭhī (dried ginger) powder - 2 g., taken twice daily with warm water.",
                "compound_preparations": "1. Lavaṇabhāskara Cūrṇa 2. Hiṅgvāṣṭaka Cūrṇa"
            }
        ]
        
        output_file = KNOWLEDGE_BASE_PATH / "ayurveda_diseases.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Created sample knowledge base at: {output_file}")

# ============================================================================
# INDEX BUILDING
# ============================================================================

def build_indices(documents: List[str], metadata: List[Dict], rebuild: bool = False):
    """
    Build BM25 and FAISS indices.
    
    Args:
        documents: List of text documents
        metadata: List of metadata dictionaries
        rebuild: Force rebuild even if indices exist
    """
    
    logger.info("=" * 60)
    logger.info("BUILDING INDICES")
    logger.info("=" * 60)
    
    # Check if indices exist
    bm25_path = f"{VECTOR_DB_PATH}/bm25_index.pkl"
    faiss_path = f"{VECTOR_DB_PATH}/faiss_index.bin"
    
    if not rebuild and Path(bm25_path).exists() and Path(faiss_path).exists():
        logger.info("Indices already exist. Skipping build.")
        logger.info("Use --rebuild flag to force rebuild.")
        return
    
    # Build BM25 index
    logger.info("\n📊 Building BM25 Index...")
    start_time = time.time()
    
    bm25_engine = BM25Engine(documents)
    
    with open(bm25_path, 'wb') as f:
        pickle.dump({'num_docs': len(documents)}, f)
    
    bm25_time = time.time() - start_time
    logger.info(f"✅ BM25 index built in {bm25_time:.2f}s")
    
    # Build FAISS index
    logger.info("\n🔍 Building FAISS Vector Index...")
    logger.info(f"Embedding model: {EMBEDDING_MODEL}")
    
    start_time = time.time()
    
    vector_engine = VectorSearchEngine(documents)
    vector_engine.save_index(faiss_path)
    
    faiss_time = time.time() - start_time
    logger.info(f"✅ FAISS index built in {faiss_time:.2f}s")
    
    # Save metadata
    logger.info("\n💾 Saving Metadata...")
    
    metadata_to_save = {
        'documents': documents,
        'metadata': metadata,
        'created_at': time.time(),
        'num_documents': len(documents),
        'embedding_model': EMBEDDING_MODEL,
        'chunk_size': CHUNK_SIZE,
        'chunk_overlap': CHUNK_OVERLAP
    }
    
    with open(METADATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(metadata_to_save, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ Metadata saved to {METADATA_PATH}")
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("INDEX BUILDING SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Documents processed: {len(documents)}")
    logger.info(f"Metadata entries: {len(metadata)}")
    logger.info(f"BM25 build time: {bm25_time:.2f}s")
    logger.info(f"FAISS build time: {faiss_time:.2f}s")
    logger.info(f"Total time: {bm25_time + faiss_time:.2f}s")
    logger.info(f"BM25 index size: {Path(bm25_path).stat().st_size / 1024:.1f} KB")
    logger.info(f"FAISS index size: {Path(faiss_path).stat().st_size / 1024 / 1024:.1f} MB")
    logger.info("=" * 60)

# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_database():
    """Initialize SQLite database for chat history."""
    
    logger.info("\n📦 Initializing Database...")
    
    from pathlib import Path
    import sqlite3
    
    db_path = "data/chat_history.db"
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            response TEXT NOT NULL,
            retrieved_docs TEXT,
            relevance_scores TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            model_used TEXT,
            version TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    
    logger.info(f"✅ Database initialized at {db_path}")

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main initialization function."""
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Initialize RAG system indices")
    parser.add_argument('--rebuild', action='store_true', help='Force rebuild all indices')
    parser.add_argument('--batch_size', type=int, default=16, help='Processing batch size')
    parser.add_argument('--chunk_size', type=int, default=CHUNK_SIZE, help='Chunk size in characters')
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("AYURVEDA RAG SYSTEM - INITIALIZATION")
    logger.info("=" * 60)
    
    # Step 1: Process documents
    logger.info("\n📄 Loading and Processing Knowledge Base...")
    processor = DocumentProcessor(chunk_size=args.chunk_size)
    documents, metadata = processor.load_knowledge_base()
    
    if not documents:
        logger.error("No documents loaded. Check knowledge base path.")
        return False
    
    # Step 2: Build indices
    logger.info("\n🔧 Building Search Indices...")
    build_indices(documents, metadata, rebuild=args.rebuild)
    
    # Step 3: Initialize database
    logger.info("\n💾 Initializing Storage...")
    init_database()
    
    # Success
    logger.info("\n" + "=" * 60)
    logger.info("✅ INITIALIZATION COMPLETE!")
    logger.info("=" * 60)
    logger.info("\nNext steps:")
    logger.info("1. Set your GEMINI_API_KEY in .env (optional)")
    logger.info("2. Start Ollama (optional): ollama serve")
    logger.info("3. Run the application: streamlit run app.py")
    logger.info("=" * 60 + "\n")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
