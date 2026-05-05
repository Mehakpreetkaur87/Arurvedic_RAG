"""
================================================================================
AYURVEDA RAG PIPELINE - Core Retrieval & Generation Logic
================================================================================
This module implements a complete RAG pipeline with:
- Hybrid search (BM25 + Vector/Semantic search)
- RRF fusion algorithm for combining results
- Cross-encoder reranking for precision
- Support for both v1 (basic) and v2 (with normalization) versions

Architecture:
    Query → Normalization(v2) → BM25 Search + Vector Search → 
    RRF Fusion → Reranking → Context Building → LLM Generation → Response

Memory efficient for 8GB RAM systems using:
    - CPU-only embeddings (sentence-transformers)
    - FAISS for vector similarity (in-memory, no external DB)
    - SQLite for chat history
    - Persistent JSON for metadata

Author: RAG System
Version: 1.0 (+ v2 experimental)
================================================================================
"""

import os
import json
import pickle
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import sqlite3
import logging
from pathlib import Path
from abc import ABC, abstractmethod
import unicodedata
import re

# Suppress warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# ============================================================================
# IMPORTS - Core Libraries
# ============================================================================
from rank_bm25 import BM25Okapi  # BM25 ranking algorithm
from sentence_transformers import SentenceTransformer  # Embeddings
from sentence_transformers import CrossEncoder  # Reranking
import faiss  # Vector similarity search
import nltk  # Natural language toolkit
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# Download required NLTK data (one-time)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables with defaults
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
RERANKER_MODEL = os.getenv('RERANKER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
DEVICE = os.getenv('DEVICE', 'cpu')

BM25_TOP_K = int(os.getenv('BM25_TOP_K', 20))
VECTOR_TOP_K = int(os.getenv('VECTOR_TOP_K', 20))
RERANK_TOP_K = int(os.getenv('RERANK_TOP_K', 5))
RRF_K = int(os.getenv('RRF_K', 60))
SIMILARITY_THRESHOLD = float(os.getenv('SIMILARITY_THRESHOLD', 0.3))

DB_PATH = os.getenv('DB_PATH', 'data/chat_history.db')
VECTOR_DB_PATH = os.getenv('VECTOR_DB_PATH', 'data/faiss_index')
METADATA_PATH = os.getenv('METADATA_PATH', 'data/metadata.json')

CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 800))
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', 200))

ENABLE_NORMALIZATION = os.getenv('ENABLE_NORMALIZATION', 'false').lower() == 'true'
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

# Create necessary directories
Path(VECTOR_DB_PATH).mkdir(parents=True, exist_ok=True)
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

# ============================================================================
# DATA MODELS - Type Definitions
# ============================================================================

@dataclass
class RetrievedDocument:
    """Represents a single retrieved document chunk."""
    id: str
    content: str
    score: float  # Combined score from hybrid search
    bm25_score: float
    vector_score: float
    reranker_score: Optional[float] = None
    metadata: Optional[Dict] = None
    
    def to_dict(self):
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SearchResult:
    """Result from hybrid search before LLM generation."""
    query: str
    documents: List[RetrievedDocument]
    processing_time_ms: float
    search_method: str = "hybrid"
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'query': self.query,
            'documents': [doc.to_dict() for doc in self.documents],
            'processing_time_ms': self.processing_time_ms,
            'search_method': self.search_method
        }


# ============================================================================
# TEXT NORMALIZATION - v2.0 Feature
# ============================================================================

class TextNormalizer:
    """
    Normalizes text to handle IAST transliteration variants.
    
    Example:
        "AGNIMĀNDYA" → "AGNIMANDYA"
        
    Used in v2.0 to handle disease names written differently.
    Preprocessing step to ensure terminology consistency.
    """
    
    # IAST diacritics mapping to ASCII equivalents
    IAST_MAP = {
        'ā': 'a', 'ī': 'i', 'ū': 'u', 'ē': 'e', 'ō': 'o',
        'ṛ': 'r', 'ḷ': 'l', 'ṁ': 'm', 'ṅ': 'n', 'ñ': 'n',
        'ṭ': 't', 'ḍ': 'd', 'ṇ': 'n', 'ś': 's', 'ṣ': 's',
        'h': 'h', 'ḥ': 'h',
        # Uppercase variants
        'Ā': 'A', 'Ī': 'I', 'Ū': 'U', 'Ē': 'E', 'Ō': 'O',
        'Ṛ': 'R', 'Ḷ': 'L', 'Ṁ': 'M', 'Ṅ': 'N', 'Ñ': 'N',
        'Ṭ': 'T', 'Ḍ': 'D', 'Ṇ': 'N', 'Ś': 'S', 'Ṣ': 'S',
    }
    
    @staticmethod
    def normalize(text: str) -> str:
        """
        Apply all normalization steps to text.
        
        Steps:
        1. Remove diacritics using Unicode NFD decomposition
        2. Map IAST-specific characters to ASCII
        3. Convert to lowercase for consistency
        4. Remove extra whitespace
        
        Args:
            text: Input text (may contain IAST characters)
            
        Returns:
            Normalized text (ASCII, lowercase)
        """
        if not ENABLE_NORMALIZATION:
            return text
        
        # Step 1: NFD decomposition - separates base char from diacritics
        # "ā" (single char) becomes "a" + combining macron
        # Then filter out combining characters
        nfd_text = unicodedata.normalize('NFD', text)
        ascii_text = nfd_text.encode('ASCII', 'ignore').decode('ASCII')
        
        # Step 2: Manual IAST mapping (for characters NFD doesn't handle)
        for iast_char, ascii_char in TextNormalizer.IAST_MAP.items():
            ascii_text = ascii_text.replace(iast_char, ascii_char)
        
        # Step 3: Lowercase
        ascii_text = ascii_text.lower()
        
        # Step 4: Clean whitespace
        ascii_text = ' '.join(ascii_text.split())
        
        return ascii_text
    
    @staticmethod
    def is_normalized(text: str) -> bool:
        """Check if text needs normalization (has diacritics)."""
        return any(ord(char) > 127 for char in text)


# ============================================================================
# RETRIEVAL ENGINES - BM25 and Vector Search
# ============================================================================

class BM25Engine:
    """
    BM25 (Best Match 25) - Keyword/Lexical search engine.
    
    What: Ranks documents by term frequency and inverse document frequency
    Why: Essential for exact terminology matching (medical terms, disease names)
    How: TF-IDF + BM25 probabilistic model
    
    Example:
        Query: "AGNIDAGDHA symptoms"
        → Matches documents with exact words "AGNIDAGDHA" and "symptoms"
        → High score if disease name appears in document
        
    Benefits:
        - Fast (10-30ms for typical queries)
        - Exact matches work well
        - No training required
        - Interpretable (word-level matching)
    """
    
    def __init__(self, documents: List[str]):
        """
        Initialize BM25 index.
        
        Args:
            documents: List of text documents to index
        """
        logger.info(f"Initializing BM25 with {len(documents)} documents")
        
        # Tokenize all documents (split into words, lowercase)
        self.documents = documents
        tokenized_docs = [self._tokenize(doc) for doc in documents]
        
        # Initialize BM25 model
        # Parameters: k1 (term frequency saturation), b (document length normalization)
        self.bm25 = BM25Okapi(tokenized_docs, k1=2.0, b=0.75)
        logger.info("BM25 initialization complete")
    
    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """
        Tokenize text for BM25.
        
        Steps:
        1. Lowercase conversion
        2. Word tokenization
        3. Remove stopwords
        4. Remove short tokens
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tokens
        """
        # Normalize text first (v2 feature)
        text = TextNormalizer.normalize(text)
        
        # Lowercase
        text = text.lower()
        
        # Tokenize
        tokens = word_tokenize(text)
        
        # Remove stopwords and short tokens
        stop_words = set(stopwords.words('english'))
        tokens = [t for t in tokens if len(t) > 2 and t not in stop_words]
        
        return tokens
    
    def search(self, query: str, top_k: int = 20) -> List[Tuple[int, float]]:
        """
        Search for documents matching query.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of (document_index, score) tuples, sorted by score
        """
        # Tokenize query same way as documents
        query_tokens = self._tokenize(query)
        
        # Get BM25 scores for all documents
        scores = self.bm25.get_scores(query_tokens)
        
        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        # Return (index, score) pairs
        results = [(int(idx), float(scores[idx])) for idx in top_indices]
        return results


class VectorSearchEngine:
    """
    Vector/Semantic Search using embeddings.
    
    What: Converts text to vectors (embeddings), finds semantically similar docs
    Why: Understands meaning, finds paraphrases, handles synonyms
    How: Pre-trained transformer model (sentence-transformers) + FAISS ANN
    
    Model: sentence-transformers/all-MiniLM-L6-v2
        - 384-dimensional embeddings
        - Trained on 1 billion sentence pairs
        - ~90MB download
        - Fast inference (1000 sent/sec on CPU)
    
    Example:
        Query: "How to treat digestive problems?"
        → Finds documents about "indigestion", "Agnimandya" (even without exact match)
        → Matches semantic meaning, not just keywords
    
    Benefits:
        - Understands meaning
        - Finds paraphrases and synonyms
        - Good for natural language queries
        - Works across languages (multilingual models)
    """
    
    def __init__(self, documents: List[str]):
        """
        Initialize vector search engine.
        
        Args:
            documents: List of documents to embed and index
        """
        logger.info(f"Initializing Vector Search with {len(documents)} documents")
        logger.info(f"Using embedding model: {EMBEDDING_MODEL}")
        
        self.documents = documents
        
        # Load embedding model
        # First run will download model (~500MB)
        logger.info("Loading embedding model (first run may take time)...")
        self.encoder = SentenceTransformer(EMBEDDING_MODEL, device=DEVICE)
        
        logger.info(f"Model loaded. Embedding {len(documents)} documents...")
        
        # Encode all documents to embeddings
        # Batch processing for memory efficiency
        batch_size = 32
        embeddings = []
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            # Normalize embeddings for cosine similarity
            batch_embeddings = self.encoder.encode(
                batch, 
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=DEBUG_MODE
            )
            embeddings.append(batch_embeddings)
        
        # Concatenate all embeddings
        self.embeddings = np.vstack(embeddings).astype('float32')
        
        logger.info(f"Created {self.embeddings.shape[0]} embeddings of dimension {self.embeddings.shape[1]}")
        
        # Create FAISS index
        # IndexFlatIP: Inner Product (=cosine for normalized vectors)
        dimension = self.embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(self.embeddings)
        
        logger.info(f"FAISS index created with {self.index.ntotal} vectors")
    
    def search(self, query: str, top_k: int = 20) -> List[Tuple[int, float]]:
        """
        Search for semantically similar documents.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of (document_index, score) tuples
        """
        # Normalize query text (v2)
        query = TextNormalizer.normalize(query)
        
        # Embed query
        query_embedding = self.encoder.encode(
            [query],
            normalize_embeddings=True,
            convert_to_numpy=True
        ).astype('float32')
        
        # Search in FAISS
        scores, indices = self.index.search(query_embedding, top_k)
        
        # Return (index, score) pairs
        results = [(int(idx), float(score)) for idx, score in zip(indices[0], scores[0])]
        return results
    
    def save_index(self, path: str):
        """Save FAISS index to disk."""
        faiss.write_index(self.index, path)
        logger.info(f"Vector index saved to {path}")
    
    @staticmethod
    def load_index(path: str) -> faiss.Index:
        """Load FAISS index from disk."""
        index = faiss.read_index(path)
        logger.info(f"Vector index loaded from {path}")
        return index


# ============================================================================
# HYBRID SEARCH - Combining BM25 + Vector Search
# ============================================================================

class HybridSearchEngine:
    """
    Hybrid Search - Combines lexical (BM25) and semantic (Vector) search.
    
    Rationale:
        - BM25: Catches exact matches, technical terms, acronyms
        - Vector: Finds semantic matches, paraphrases, synonyms
        - Combined: Best of both worlds
    
    Fusion Algorithm: RRF (Reciprocal Rank Fusion)
        
        Formula:
            RRF_score = Σ 1 / (k + rank)
            
        where:
            k = 60 (standard parameter, reduces impact of rank)
            rank = position in result list (1-indexed)
        
        Example with k=60:
            Rank 1: 1/(60+1) = 0.0164
            Rank 2: 1/(60+2) = 0.0159
            Rank 10: 1/(60+10) = 0.0137
            
        Why RRF:
            - No hyperparameter tuning needed
            - Works well across different result distributions
            - Proven in IR literature
            - Fair to both retrieval methods
    
    Benefit over single method:
        Eliminates false negatives from each approach:
        - Dense-only: Would miss "ORA-00942" (exact code match)
        - BM25-only: Would miss "database connection" (paraphrase)
        - Hybrid: Catches both
        
    Precision improvement: Typically +5-15% over single method
    """
    
    def __init__(self, bm25_engine: BM25Engine, vector_engine: VectorSearchEngine):
        """
        Initialize hybrid search with BM25 and Vector engines.
        
        Args:
            bm25_engine: BM25 lexical search engine
            vector_engine: Vector semantic search engine
        """
        self.bm25 = bm25_engine
        self.vector = vector_engine
        logger.info("Hybrid search engine initialized (BM25 + Vector + RRF)")
    
    def search(self, query: str, top_k: int = 5) -> Tuple[List[Dict], Dict]:
        """
        Perform hybrid search combining BM25 and Vector results.
        
        Pipeline:
        1. BM25 search: Get top-20 keyword matches
        2. Vector search: Get top-20 semantic matches
        3. RRF fusion: Combine and rank by reciprocal rank
        4. Normalization: Normalize scores to 0-1
        5. Deduplication: Remove duplicates, keep higher score
        
        Args:
            query: Search query
            top_k: Final number of results to return
            
        Returns:
            Tuple of (results_list, debug_info_dict)
        """
        logger.info(f"Hybrid search for: '{query}'")
        
        # Step 1: BM25 search
        bm25_results = self.bm25.search(query, top_k=BM25_TOP_K)
        logger.debug(f"BM25 returned {len(bm25_results)} results")
        
        # Step 2: Vector search
        vector_results = self.vector.search(query, top_k=VECTOR_TOP_K)
        logger.debug(f"Vector search returned {len(vector_results)} results")
        
        # Step 3: RRF Fusion
        # Create score dictionary using RRF formula
        rrf_scores = {}
        
        # Add BM25 scores with RRF calculation
        for rank, (doc_idx, score) in enumerate(bm25_results, start=1):
            rrf_score = 1.0 / (RRF_K + rank)
            if doc_idx not in rrf_scores:
                rrf_scores[doc_idx] = {'bm25': rrf_score, 'vector': 0.0, 'raw_bm25': score}
            else:
                rrf_scores[doc_idx]['bm25'] = rrf_score
                rrf_scores[doc_idx]['raw_bm25'] = score
        
        # Add Vector scores with RRF calculation
        for rank, (doc_idx, score) in enumerate(vector_results, start=1):
            rrf_score = 1.0 / (RRF_K + rank)
            if doc_idx not in rrf_scores:
                rrf_scores[doc_idx] = {'bm25': 0.0, 'vector': rrf_score, 'raw_vector': score}
            else:
                rrf_scores[doc_idx]['vector'] = rrf_score
                rrf_scores[doc_idx]['raw_vector'] = score
        
        logger.debug(f"RRF fusion produced {len(rrf_scores)} unique documents")
        
        # Step 4: Sort by combined RRF score and get top-k
        sorted_results = sorted(
            rrf_scores.items(),
            key=lambda x: x[1]['bm25'] + x[1]['vector'],
            reverse=True
        )[:top_k]
        
        # Step 5: Build result dictionaries with normalized scores
        # Normalize each score type to 0-1 range
        final_results = []
        
        # Get max scores for normalization
        all_bm25 = [v['bm25'] for v in rrf_scores.values()]
        all_vector = [v['vector'] for v in rrf_scores.values()]
        
        max_bm25 = max(all_bm25) if all_bm25 else 1.0
        max_vector = max(all_vector) if all_vector else 1.0
        
        for doc_idx, scores in sorted_results:
            # Normalize to 0-1 range (divide by max)
            bm25_norm = scores['bm25'] / max_bm25 if max_bm25 > 0 else 0.0
            vector_norm = scores['vector'] / max_vector if max_vector > 0 else 0.0
            combined = bm25_norm + vector_norm  # Combined normalized score
            
            result = {
                'doc_idx': int(doc_idx),
                'bm25_score': float(scores.get('raw_bm25', 0.0)),
                'vector_score': float(scores.get('raw_vector', 0.0)),
                'bm25_score_norm': float(bm25_norm),
                'vector_score_norm': float(vector_norm),
                'combined_score': float(combined)
            }
            
            # Only include if combined score above threshold
            if combined >= SIMILARITY_THRESHOLD:
                final_results.append(result)
        
        logger.info(f"Hybrid search returned {len(final_results)} results")
        
        # Debug info
        debug_info = {
            'bm25_count': len(bm25_results),
            'vector_count': len(vector_results),
            'fused_count': len(rrf_scores),
            'final_count': len(final_results)
        }
        
        return final_results, debug_info


# ============================================================================
# RERANKING - Cross-Encoder for Precision
# ============================================================================

class RerankerEngine:
    """
    Cross-Encoder Reranking - Improves precision of top results.
    
    What: Takes query + document pairs, outputs relevance score
    
    Why: Initial retrieval has false positives
        - BM25 matches keywords even if not relevant
        - Vector search can match on irrelevant semantic matches
        - Reranker re-scores with query context
    
    Model: cross-encoder/ms-marco-MiniLM-L-6-v2
        - Trained on Microsoft MARCO dataset (1M+ QA pairs)
        - Better for relevance scoring than semantic similarity
        - Input: [query, document] pairs
        - Output: Relevance score 0-1
    
    Impact:
        - Improves precision by 10-20% typically
        - Cost: ~30-80ms for reranking
        - Worth it for final top results
    
    Example:
        Input: 
            Query: "How to treat burns?"
            Doc1: "Burns are skin injuries from heat... [RELEVANT]"
            Doc2: "Burnt toast contains carbon compounds... [IRRELEVANT]"
        
        Output:
            Doc1: 0.92 (high relevance)
            Doc2: 0.15 (low relevance)
    """
    
    def __init__(self):
        """Initialize cross-encoder for reranking."""
        logger.info(f"Loading reranker model: {RERANKER_MODEL}")
        self.reranker = CrossEncoder(RERANKER_MODEL, device=DEVICE)
        logger.info("Reranker model loaded")
    
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """
        Rerank documents for given query.
        
        Args:
            query: Search query
            documents: List of documents to rerank
            top_k: Number of top results to return
            
        Returns:
            List of (document_index, score) tuples, sorted by score
        """
        logger.info(f"Reranking {len(documents)} documents")
        
        # Create query-document pairs
        pairs = [[query, doc] for doc in documents]
        
        # Score all pairs
        scores = self.reranker.predict(pairs)
        
        # Sort by score and get top-k
        ranked = sorted(
            enumerate(scores),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        return [(int(idx), float(score)) for idx, score in ranked]


# ============================================================================
# MAIN RAG PIPELINE
# ============================================================================

class RAGPipeline:
    """
    Complete RAG (Retrieval-Augmented Generation) Pipeline.
    
    Workflow:
    1. Load or initialize knowledge base indices
    2. Process user query
    3. Retrieve relevant documents (hybrid search)
    4. Rerank for precision
    5. Build context for LLM
    6. Generate response using LLM
    7. Store in chat history
    
    Supports both versions:
    - v1.0: No text normalization (current production)
    - v2.0: With text normalization (experimental)
    """
    
    def __init__(self, version: str = "v1"):
        """
        Initialize RAG pipeline.
        
        Args:
            version: Pipeline version ("v1" or "v2")
                - v1: Basic retrieval (no normalization)
                - v2: With text normalization (experimental)
        """
        self.version = version
        logger.info(f"Initializing RAG Pipeline v{version}")
        
        # Check if indices exist
        indices_exist = self._check_indices_exist()
        
        if not indices_exist:
            logger.warning("Indices not found. Please run scripts/initialize.py first")
            raise FileNotFoundError(
                "Vector indices not found. Run 'python scripts/initialize.py' to create them."
            )
        
        # Load indices and models
        self._load_indices()
        self._initialize_engines()
        
        logger.info(f"RAG Pipeline v{version} ready")
    
    def _check_indices_exist(self) -> bool:
        """Check if all required indices exist."""
        required_files = [
            f"{VECTOR_DB_PATH}/faiss_index.bin",
            f"{VECTOR_DB_PATH}/bm25_index.pkl",
            METADATA_PATH
        ]
        
        return all(Path(f).exists() for f in required_files)
    
    def _load_indices(self):
        """Load pre-built indices from disk."""
        logger.info("Loading indices from disk...")
        
        # Load documents and metadata
        with open(METADATA_PATH, 'r') as f:
            metadata = json.load(f)
        
        self.documents = metadata.get('documents', [])
        self.doc_metadata = metadata.get('metadata', [])
        
        logger.info(f"Loaded {len(self.documents)} documents")
        
        # Load BM25 index
        bm25_path = f"{VECTOR_DB_PATH}/bm25_index.pkl"
        with open(bm25_path, 'rb') as f:
            bm25_index_data = pickle.load(f)
        
        # Reconstruct BM25 engine from saved data
        self.bm25_engine = BM25Engine(self.documents)
        logger.info("BM25 index loaded")
        
        # Load FAISS index
        faiss_path = f"{VECTOR_DB_PATH}/faiss_index.bin"
        faiss_index = VectorSearchEngine.load_index(faiss_path)
        
        # Create vector engine with loaded index
        self.vector_engine = VectorSearchEngine.__new__(VectorSearchEngine)
        self.vector_engine.documents = self.documents
        self.vector_engine.index = faiss_index
        self.vector_engine.encoder = SentenceTransformer(EMBEDDING_MODEL, device=DEVICE)
        self.vector_engine.embeddings = None  # Not needed after index is loaded
        
        logger.info("FAISS index loaded")
    
    def _initialize_engines(self):
        """Initialize retrieval engines."""
        # Hybrid search
        self.hybrid_search = HybridSearchEngine(self.bm25_engine, self.vector_engine)
        
        # Reranking
        self.reranker = RerankerEngine()
        
        # Database
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for chat history."""
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create conversations table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                response TEXT NOT NULL,
                retrieved_docs TEXT,  -- JSON serialized
                relevance_scores TEXT,  -- JSON serialized
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                model_used TEXT,
                version TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def search(self, query: str) -> SearchResult:
        """
        Retrieve relevant documents for query.
        
        Pipeline:
        1. Normalize query (v2 only)
        2. Hybrid search (BM25 + Vector + RRF)
        3. Rerank results
        4. Build RetrievedDocument objects with metadata
        
        Args:
            query: User query
            
        Returns:
            SearchResult containing retrieved documents
        """
        import time
        start_time = time.time()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"SEARCH: {query}")
        logger.info(f"{'='*60}")
        
        # Step 1: Normalize query (v2 feature)
        normalized_query = TextNormalizer.normalize(query) if ENABLE_NORMALIZATION else query
        if normalized_query != query:
            logger.info(f"Normalized: '{query}' → '{normalized_query}'")
        
        # Step 2: Hybrid search
        hybrid_results, debug_info = self.hybrid_search.search(
            query, 
            top_k=RERANK_TOP_K
        )
        
        # Step 3: Extract documents for reranking
        doc_texts = [self.documents[r['doc_idx']] for r in hybrid_results]
        doc_indices = [r['doc_idx'] for r in hybrid_results]
        
        # Step 4: Rerank
        reranked = self.reranker.rerank(normalized_query, doc_texts, top_k=RERANK_TOP_K)
        
        # Step 5: Build RetrievedDocument objects
        retrieved_docs = []
        
        for rerank_idx, (orig_position, rerank_score) in enumerate(reranked):
            original_result = hybrid_results[orig_position]
            doc_idx = original_result['doc_idx']
            
            doc = RetrievedDocument(
                id=str(doc_idx),
                content=self.documents[doc_idx][:500],  # First 500 chars
                score=original_result['combined_score'],
                bm25_score=original_result['bm25_score'],
                vector_score=original_result['vector_score'],
                reranker_score=float(rerank_score),
                metadata=self.doc_metadata[doc_idx] if doc_idx < len(self.doc_metadata) else None
            )
            retrieved_docs.append(doc)
            
            logger.info(
                f"#{rerank_idx+1} | Score: {rerank_score:.3f} | "
                f"BM25: {original_result['bm25_score']:.2f} | "
                f"Vector: {original_result['vector_score']:.2f}"
            )
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000  # ms
        
        logger.info(f"Search completed in {processing_time:.1f}ms")
        
        return SearchResult(
            query=query,
            documents=retrieved_docs,
            processing_time_ms=processing_time
        )
    
    def save_to_db(
        self,
        query: str,
        response: str,
        search_result: SearchResult,
        model_used: str = "gemini"
    ):
        """
        Save conversation to SQLite database.
        
        Args:
            query: User query
            response: LLM response
            search_result: SearchResult object
            model_used: Which LLM generated response
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Serialize documents and scores
        docs_json = json.dumps([doc.to_dict() for doc in search_result.documents])
        
        cursor.execute('''
            INSERT INTO conversations (query, response, retrieved_docs, model_used, version)
            VALUES (?, ?, ?, ?, ?)
        ''', (query, response, docs_json, model_used, self.version))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Conversation saved to database")
    
    def get_context(self, search_result: SearchResult) -> str:
        """
        Build context string from retrieved documents for LLM.
        
        Format:
            [Doc 1]: <content>
            Relevance: <score>%
            
            [Doc 2]: <content>
            ...
        
        Args:
            search_result: SearchResult with retrieved documents
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for i, doc in enumerate(search_result.documents, 1):
            # Build full document text (not just preview)
            full_text = self.documents[int(doc.id)]
            
            # Format for LLM
            context_parts.append(
                f"[Document {i}]\n"
                f"Content: {full_text}\n"
                f"Relevance Score: {doc.reranker_score*100:.1f}%\n"
                f"---\n"
            )
        
        return "\n".join(context_parts)
    
    def get_chat_history(self, limit: int = 10) -> List[Dict]:
        """
        Retrieve chat history from database.
        
        Args:
            limit: Maximum number of conversations to retrieve
            
        Returns:
            List of conversation dictionaries
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT * FROM conversations ORDER BY timestamp DESC LIMIT ?',
            (limit,)
        )
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def clear_chat_history(self):
        """Clear all chat history."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM conversations')
        conn.commit()
        conn.close()
        logger.info("Chat history cleared")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_pipeline(version: str = "v1") -> RAGPipeline:
    """Get RAG pipeline instance."""
    return RAGPipeline(version=version)


if __name__ == "__main__":
    # Test the pipeline
    print("RAG Pipeline module loaded successfully")
    print(f"Configuration:")
    print(f"  Embedding Model: {EMBEDDING_MODEL}")
    print(f"  Reranker Model: {RERANKER_MODEL}")
    print(f"  BM25 Top-K: {BM25_TOP_K}")
    print(f"  Vector Top-K: {VECTOR_TOP_K}")
    print(f"  Rerank Top-K: {RERANK_TOP_K}")
    print(f"  Normalization Enabled: {ENABLE_NORMALIZATION}")
