# 🏗️ System Architecture - Ayurveda RAG

Complete technical architecture and design decisions for the Ayurveda RAG system.

## Table of Contents
1. [Overall Architecture](#overall-architecture)
2. [Data Flow](#data-flow)
3. [Component Details](#component-details)
4. [Technology Stack](#technology-stack)
5. [Design Patterns](#design-patterns)
6. [Performance Optimization](#performance-optimization)

---

## Overall Architecture

### Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     UI LAYER (Streamlit)                     │
│              (Web Interface for User Interaction)             │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   APPLICATION LAYER                          │
│  ┌─────────────────┬──────────────────┬─────────────────┐   │
│  │ RAG Pipeline    │  LLM Handler     │  Chat Manager   │   │
│  │ (pipeline.py)   │  (llm_handler.py)│  (app.py)       │   │
│  └─────────────────┴──────────────────┴─────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    RETRIEVAL LAYER                           │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │  BM25 Index  │  │ FAISS Vector │  │  Reranker       │   │
│  │  (Sparse)    │  │  (Dense)     │  │  (Cross-Encoder)│   │
│  └──────────────┴──┴──────────────┴──┴─────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    STORAGE LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │  FAISS Index │  │  Metadata    │  │  SQLite DB      │   │
│  │  (on Disk)   │  │  (JSON)      │  │  (Chat History) │   │
│  └──────────────┴──┴──────────────┴──┴─────────────────┘   │
└─────────────────────────────────────────────────────────────┘

External APIs (Optional):
  ┌──────────────────┐  ┌──────────────────┐
  │ Google Gemini    │  │ Ollama Local LLM │
  │ (Cloud-based)    │  │ (Self-hosted)    │
  └──────────────────┘  └──────────────────┘
```

---

## Data Flow

### Complete Query Processing Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│  1. USER QUERY                                               │
│     Example: "What is Agnimandya?"                          │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  2. TEXT NORMALIZATION (v2.0 only)                          │
│     Input:  "What is AGNIMĀNDYA?"                          │
│     Output: "What is agnimandya?"                           │
│     Process: IAST → ASCII, diacritic removal                │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  3. HYBRID SEARCH (Parallel execution)                      │
│                                                              │
│  ┌─────────────────────────────────────────┐               │
│  │ BM25 LEXICAL SEARCH (~10-20ms)          │               │
│  │ Tokenize query                          │               │
│  │ Calculate TF-IDF scores                 │               │
│  │ Return top-20 documents by keyword      │               │
│  │ Example matches: "Agnimandya", "agni"   │               │
│  └─────────────────────────────────────────┘               │
│                                                              │
│  ┌─────────────────────────────────────────┐               │
│  │ VECTOR SEMANTIC SEARCH (~30-50ms)       │               │
│  │ Encode query to 384-dim vector          │               │
│  │ FAISS similarity search (cosine)        │               │
│  │ Return top-20 semantically similar      │               │
│  │ Example matches: synonyms, paraphrases  │               │
│  └─────────────────────────────────────────┘               │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  4. RRF FUSION (~5ms)                                       │
│     Formula: Score = 1/(k + rank)  [k=60]                  │
│     - Combine BM25 and Vector ranks                         │
│     - Deduplicate results                                    │
│     - Merge 40 total results → 20 unique                    │
│     - Normalize scores to 0-1 range                         │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  5. RERANKING (~40-80ms)                                    │
│     - Cross-encoder takes top-20 + query                    │
│     - Scores each [query, document] pair                    │
│     - Outputs relevance 0.0-1.0                             │
│     - Keep only top-5                                       │
│     - Precision improvement: +10-20%                        │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  6. CONTEXT BUILDING                                        │
│     - Extract full document text for top-5                  │
│     - Include metadata (disease name, region)               │
│     - Format for LLM prompt                                 │
│     Final context ~1000-2000 tokens                         │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  7. LLM RESPONSE GENERATION (~2-5s)                         │
│     Primary: Google Gemini API                              │
│     ├─ Build prompt with context                           │
│     ├─ Set temperature=0.7, max_tokens=2000                │
│     ├─ Stream response                                      │
│     └─ Handle rate limits                                   │
│                                                              │
│     Fallback: Ollama Local (if Gemini fails)               │
│     ├─ HTTP POST to localhost:11434/api/generate           │
│     ├─ Use llama2 or mistral model                         │
│     └─ Stream response                                      │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  8. RESPONSE DISPLAY & STORAGE                              │
│     - Stream to Streamlit UI in real-time                   │
│     - Save to SQLite chat history                           │
│     - Store retrieved documents                             │
│     - Log processing metrics                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. BM25 Engine (Lexical Search)

**Purpose:** Keyword-based document retrieval

**How it works:**
```
Input: "AGNIDAGDHA burns treatment"

Step 1: Tokenization
  Tokens: ["agnidagdha", "burns", "treatment"]
  (Remove stopwords, lowercase)

Step 2: TF-IDF Calculation
  Doc 1: "AGNIDAGDHA is burns caused by heat"
    TF("agnidagdha"): 1, IDF("agnidagdha"): high (rare word)
    Score: high
  
  Doc 2: "The treatment of burns"
    TF("agnidagdha"): 0 (missing key term)
    Score: low

Step 3: Ranking
  Return documents sorted by BM25 score
```

**Advantages:**
- Fast (10-25ms)
- Exact matches work perfectly
- No training needed
- Interpretable
- Great for technical/medical terms

**Disadvantages:**
- Doesn't understand meaning
- Misses synonyms
- Sensitive to spelling variations

**Configuration:**
```python
BM25_TOP_K = 20  # Return top 20 results
k1 = 2.0         # Term frequency saturation
b = 0.75         # Document length normalization
```

---

### 2. Vector Search Engine (Semantic Search)

**Purpose:** Find semantically similar documents

**Model:** `sentence-transformers/all-MiniLM-L6-v2`

**Architecture:**
```
Input Text → Transformer Encoder → 384-dim Vector → FAISS Index
  ↓                ↓                    ↓               ↓
"What is      Pre-trained on      Normalized      Cosine
indigestion?" 1B sentence pairs   embeddings      similarity
```

**Model Details:**
- **Architecture:** Distilled BERT (12 layers)
- **Parameters:** ~110M
- **Training:** Siamese networks on sentence pairs
- **Dimensions:** 384
- **Speed:** ~1000 sentences/sec on CPU
- **Size:** ~90MB

**Why this model?**
- ✅ Lightweight (critical for 8GB RAM)
- ✅ Good semantic understanding
- ✅ Multilingual capable
- ✅ Open-source
- ❌ Not the largest (but good enough)

**Indexing Strategy:**
```
Knowledge Base Documents
       ↓
  Embedding
       ↓
  384-dim vectors
       ↓
  FAISS Index (IndexFlatIP)
       ↓
  Cosine Similarity Precomputed
```

**Query Process:**
1. Embed query to 384-dim vector
2. Compute cosine similarity with all document vectors
3. Return top-20 by similarity score

**Advantages:**
- Understands meaning
- Finds paraphrases
- Handles synonyms
- Captures context

**Disadvantages:**
- Slower than BM25 (30-50ms)
- May find false positives
- Requires vector storage

---

### 3. RRF Fusion (Reciprocal Rank Fusion)

**Purpose:** Combine BM25 and Vector results intelligently

**Algorithm:**
```
RRF_Score = Σ 1/(k + rank)

where:
- k = 60 (parameter, reduces rank impact)
- rank = position in sorted list (1-indexed)

Example with k=60:
  Rank 1: 1/61 = 0.01639
  Rank 2: 1/62 = 0.01613
  Rank 10: 1/70 = 0.01429
  Rank 20: 1/80 = 0.01250
```

**Process:**
```
BM25 Results              Vector Results
─────────────────        ──────────────────
1. Doc A (score: 45)     1. Doc B (score: 0.92)
2. Doc B (score: 42)     2. Doc C (score: 0.88)
3. Doc C (score: 38)     3. Doc A (score: 0.85)

                  ↓
            RRF Scoring
                  
Doc A: 1/61 + 1/63 = 0.01639 + 0.01587 = 0.03226
Doc B: 1/62 + 1/61 = 0.01613 + 0.01639 = 0.03252 ← Highest
Doc C: 1/63 + 1/62 = 0.01587 + 0.01613 = 0.03200

Final ranking: B > A > C (Doc B gets boost from both methods)
```

**Why RRF?**
- ✅ No hyperparameter tuning
- ✅ Fair to both methods
- ✅ Proven in information retrieval
- ✅ Handles different score distributions

---

### 4. Cross-Encoder Reranker

**Purpose:** Re-score candidates with query context for final precision

**Model:** `cross-encoder/ms-marco-MiniLM-L-6-v2`

**Architecture:**
```
Input: [Query, Document] pair
  ↓
Tokenize & concatenate
  ↓
Sentence-BERT with classification head
  ↓
Output: Relevance score 0.0-1.0
```

**Training Data:** Microsoft MARCO dataset (1M+ QA pairs)

**Process:**
```
Input: ("How to treat burns?", "Burns are treated with cool water and...") 
  ↓
Model scores relevance
  ↓
Output: 0.89 (highly relevant)

Input: ("How to treat burns?", "The history of ancient Rome...")
  ↓
Model scores relevance
  ↓
Output: 0.12 (not relevant)
```

**Performance:**
- **Speed:** 30-80ms for 20 candidates
- **Improvement:** +10-20% precision over hybrid search alone
- **Size:** ~250MB

---

### 5. LLM Handler (Gemini + Ollama)

**Primary: Google Gemini API**

**Model:** `gemini-2.0-flash`

**Advantages:**
- State-of-the-art quality
- Fast (1-2s per response)
- Free tier (15 req/min)
- Good for production

**Rate Limiting:**
```python
# Free tier
GEMINI_RATE_LIMIT = 15  # requests per minute

# Rate limiter implementation
if requests_in_last_minute >= 15:
    sleep(remaining_time_in_minute)
```

**Fallback: Ollama Local**

**Models Available:**
- llama2 (7B): Good balance
- mistral (7B): Fast
- neural-chat (7B): Chat-optimized
- dolphin-mixtral (22B): Larger, slower

**Advantages of Fallback:**
- ✅ Works offline
- ✅ No rate limits
- ✅ No API costs
- ✅ Complete privacy
- ❌ Slower responses
- ❌ Lower quality

**Fallback Strategy:**
```python
def generate(query, context):
    try:
        # Try primary
        return gemini.generate(query, context)
    except RateLimit or ServerError or NoInternet:
        # Fall back to secondary
        return ollama.generate(query, context)
    except AllFailed:
        # Return error message
        return "Unable to generate response"
```

---

### 6. SQLite Chat Database

**Purpose:** Persistent storage of conversation history

**Schema:**
```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    query TEXT,           -- User query
    response TEXT,        -- LLM response
    retrieved_docs TEXT,  -- JSON array of documents
    relevance_scores TEXT,-- JSON scores
    timestamp DATETIME,
    model_used TEXT,      -- 'gemini' or 'ollama'
    version TEXT          -- 'v1' or 'v2'
);
```

**Benefits:**
- Local storage (no cloud dependency)
- Query history tracking
- Similar query detection (v2)
- Response caching (optional)

---

## Technology Stack

### Core Technologies

| Layer | Technology | Purpose | Why? |
|-------|-----------|---------|------|
| **UI** | Streamlit 1.39 | Interactive web interface | Easy, Python-native, real-time updates |
| **Embeddings** | Sentence-Transformers 3.0 | Text to vectors | Lightweight, pre-trained, multilingual |
| **Vector Search** | FAISS 1.7 | Similarity search | CPU-optimized, in-memory, fast |
| **Lexical Search** | rank-bm25 0.2 | Keyword matching | Simple, fast, proven algorithm |
| **Reranking** | cross-encoder 0.2 | Precision scoring | Better than embedding similarity |
| **LLM (Cloud)** | Google Gemini API | Generation | Free tier, fast, high quality |
| **LLM (Local)** | Ollama | Offline fallback | No internet, no API key, private |
| **Database** | SQLite3 | Chat history | File-based, no setup, reliable |
| **Data Processing** | Pandas 2.1 | DataFrame ops | Industry standard |
| **HTTP** | Requests 2.31 | API calls | Simple, reliable |

### Dependency Tree

```
Streamlit
├── Requests (HTTP calls)
├── Sentence-Transformers
│   ├── PyTorch
│   ├── NLTK (tokenization)
│   └── Scikit-learn
├── FAISS
│   └── NumPy
├── Rank-BM25
└── SQLite3 (built-in)

Google Generative AI
└── Requests

Cross-Encoder
├── PyTorch
└── Sentence-Transformers
```

---

## Design Patterns

### 1. Strategy Pattern (LLM Selection)

```python
# Allows switching between different LLM strategies
class LLMProvider(ABC):
    @abstractmethod
    def generate(self): pass

class GeminiLLM(LLMProvider):
    def generate(self): ...  # Gemini strategy

class OllamaLLM(LLMProvider):
    def generate(self): ...  # Ollama strategy

# Client code doesn't care which LLM is used
llm_manager.generate(query)  # Automatic selection
```

### 2. Factory Pattern (Index Creation)

```python
# Factory creates appropriate retriever
class RAGPipeline:
    def __init__(self):
        self.bm25 = BM25Engine(documents)
        self.vector = VectorSearchEngine(documents)
        self.hybrid = HybridSearchEngine(bm25, vector)
```

### 3. Pipeline Pattern (Data Processing)

```
Raw Documents → Chunking → Indexing → Embedding → Storage

Each stage is independent, can be swapped or modified
```

### 4. Observer Pattern (UI Updates)

```python
# Streamlit UI observes LLM generation
for chunk in llm.generate_stream(query):
    st.write(chunk)  # Update UI as chunks arrive
```

---

## Performance Optimization

### Memory Optimization (8GB RAM)

**Model Selection:**
- ✅ MiniLM-L6 (384-dim, 90MB)
- ❌ MPNet (768-dim, 430MB)

**Batch Processing:**
```python
# Process documents in batches
for i in range(0, len(documents), batch_size):
    batch = documents[i:i+batch_size]
    embeddings = encoder.encode(batch)  # ~100MB per batch
```

**Index Compression:**
```python
# FAISS provides compression options
# Default: IndexFlatIP (full precision)
# Option: IndexIVFFlat (approximate, smaller)
```

### Speed Optimization

**Parallel Execution:**
```
BM25 search (10ms) ─┐
                   ├→ RRF Fusion (5ms) → Rerank (50ms)
Vector search (30ms) ┘
Total: ~65ms (vs 90ms sequential)
```

**Caching:**
```python
# Cache similar queries
if query_embedding in cache:
    return cached_results
else:
    results = hybrid_search(query)
    cache[query_embedding] = results
    return results
```

**Streaming:**
```python
# Stream LLM response for real-time UI
for chunk in llm.generate_stream(query):
    yield chunk  # Display immediately
```

### Disk I/O Optimization

**Single Index File:**
```
data/
├── faiss_index.bin  (1 file, fast loading)
├── bm25_index.pkl
└── metadata.json
```

**Avoid Multiple Loads:**
```python
# Load once at startup
rag = RAGPipeline()  # Load all indices

# Use same instance for all queries
results = rag.search(query1)
results = rag.search(query2)
```

---

## Scalability Considerations

### Current Scale
- **Documents:** 100-10,000
- **QPS:** 1-10 queries/second
- **Memory:** 4-8GB

### Scaling to 100K+ Documents

**Options:**
1. **Approximate Nearest Neighbor (ANN)**
   - FAISS IndexIVFFlat instead of IndexFlatIP
   - 10-100x faster, 1-2% accuracy loss

2. **Sharding**
   - Split documents across multiple indices
   - Search in parallel

3. **GPU Acceleration**
   - Use CUDA for embeddings
   - FAISS GPU index (needs GPU)

4. **Distributed Search**
   - Elasticsearch for keyword search
   - Pinecone/Weaviate for vector search

### Estimated Resources

| Scale | Embeddings Size | Index Size | RAM | Search Time |
|-------|-----------------|-----------|-----|-------------|
| 1K | 400MB | 50MB | 1GB | 10ms |
| 10K | 4GB | 500MB | 6GB | 15ms |
| 100K | 40GB | 5GB | 50GB | 25ms |
| 1M | 400GB | 50GB | 500GB | 50ms |

---

## Security Considerations

### API Key Management
```python
# .env (never commit)
GEMINI_API_KEY=xxx

# Loaded at runtime
api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)
```

### Data Privacy
- ✅ All indices stored locally
- ✅ Ollama option for no internet
- ✅ SQLite chat history (local)
- ⚠️  Gemini sends queries to cloud

### Rate Limiting
- Gemini: 15 req/min (automatic backoff)
- Ollama: Unlimited (local)

---

## Deployment Architectures

### Single-Machine (Current)
```
User → Streamlit UI → RAG Pipeline → LLM API
       (localhost:8501)   (local)    (cloud/local)
```

### Distributed
```
Users → Load Balancer → Multiple Streamlit instances
          → Shared FAISS/BM25 indices (NFS)
          → LLM API (cloud or multi-node local)
```

### Microservices
```
Streamlit UI (port 8501)
    ↓
RAG Service (port 8000)
    ├→ Search Service
    ├→ LLM Service
    └→ Database Service

(Each component scalable independently)
```

---

## Monitoring & Observability

### Metrics Tracked
- Query processing time (total, by stage)
- Retrieved document count
- Reranker score distribution
- LLM generation time
- LLM fallback rate
- Chat history size

### Logging
```python
logger.info(f"Search: {processing_time:.1f}ms, docs: {len(results)}")
logger.warning(f"Gemini rate limit, using Ollama fallback")
logger.error(f"Search failed: {error}")
```

### Debugging
```python
DEBUG_MODE = True
# Shows detailed steps, embedding generation, scoring info
```

---

## Future Improvements

### v2.0 (Current Development)
- Text normalization (IAST → ASCII)
- Similar query detection
- Response caching

### v3.0 (Planned)
- Fine-tuned reranker
- Custom embeddings for Ayurveda
- Multi-language support
- Knowledge graph integration

### v4.0 (Research)
- Retrieval feedback loop
- Active learning
- Few-shot in-context learning
- Explainability scoring

---

**This architecture is designed for:**
- ✅ 8GB RAM systems
- ✅ Offline operation capability
- ✅ Easy maintenance
- ✅ Clear separation of concerns
- ✅ Easy to extend and modify

