# 🔄 Complete Pipeline Flow Visualization

Detailed step-by-step walkthrough of the entire RAG system with timing and resource usage.

---

## 🎯 Query Processing Flow (Complete)

### Visual Pipeline

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           USER INPUT                                       │
│                    "What is AGNIMĀNDYA?"                                  │
└────────────────────────────┬───────────────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │ STEP 1: NORMALIZE  │ ◄─── v2.0 feature only
                    │ TEXT (v2)        │       Time: ~10-20ms
                    │                  │       Converts IAST → ASCII
                    └────────┬────────┘
                             │
                    Input:  "What is AGNIMĀNDYA?"
                    Output: "What is agnimandya?"
                             │
        ┌────────────────────┴────────────────────┐
        │                                         │
┌──────▼──────────┐                    ┌────────▼──────────┐
│  STEP 2A: BM25  │                    │  STEP 2B: VECTOR  │
│  LEXICAL SEARCH │ (Parallel)         │  SEMANTIC SEARCH  │
│   ~10-20ms      │                    │    ~30-50ms       │
│                 │                    │                   │
│ ┌─────────────┐ │                    │ ┌───────────────┐ │
│ │1. Tokenize  │ │                    │ │1. Embed query │ │
│ │   "agniman  │ │                    │ │   to vector   │ │
│ │    dya"     │ │                    │ │   (384-dim)   │ │
│ └────────┬────┘ │                    │ └───────┬───────┘ │
│          │      │                    │         │         │
│ ┌────────▼────┐ │                    │ ┌─────────────┐   │
│ │2. Calculate │ │                    │ │2. FAISS     │   │
│ │   TF-IDF    │ │                    │ │   similarity│   │
│ │   scores    │ │                    │ │   search    │   │
│ └────────┬────┘ │                    │ └─────┬───────┘   │
│          │      │                    │       │           │
│ ┌────────▼────┐ │                    │ ┌─────▼───────┐   │
│ │3. Return    │ │                    │ │3. Return    │   │
│ │   top-20    │ │                    │ │   top-20    │   │
│ │   docs      │ │                    │ │   docs      │   │
│ └────────┬────┘ │                    │ └─────┬───────┘   │
│          │      │                    │       │           │
└──────────┼──────┘                    └───────┼───────────┘
           │                                   │
           │     Results: 20 docs × 20 docs    │
           │     = 40 total results            │
           │                                   │
        ┌──────────────────────────────────────┐
        │  STEP 3: RRF FUSION (Merge Results)  │
        │  Time: ~5ms                          │
        │  40 results → 20 unique docs         │
        │                                      │
        │  Formula: 1/(k + rank)  [k=60]       │
        │  - Combine BM25 scores               │
        │  - Combine Vector scores             │
        │  - Normalize both to 0-1             │
        │  - Calculate combined score          │
        │  - Sort and deduplicate              │
        └──────────────────┬───────────────────┘
                           │
                    ┌──────▼──────┐
                    │ 20 Unique    │
                    │ Documents    │
                    │ with scores  │
                    └──────┬───────┘
                           │
        ┌──────────────────────────────────────┐
        │  STEP 4: RERANKING (Precision)       │
        │  Time: ~40-80ms                      │
        │  20 docs → 5 best docs               │
        │                                      │
        │  Model: cross-encoder/ms-marco       │
        │  Input: [query, doc] pairs           │
        │  Output: Relevance scores 0-1        │
        │                                      │
        │  Process:                            │
        │  1. Create 20 pairs                  │
        │  2. Score each pair                  │
        │  3. Sort by relevance                │
        │  4. Keep top 5                       │
        │  5. Improvement: +10-20% precision   │
        └──────────────────┬───────────────────┘
                           │
                    ┌──────▼────────┐
                    │ 5 Final Docs   │
                    │ High Quality    │
                    │ (Top Results)   │
                    └──────┬─────────┘
                           │
        ┌──────────────────────────────────────┐
        │  STEP 5: CONTEXT BUILDING            │
        │  Time: ~10ms                         │
        │                                      │
        │  Extract full documents              │
        │  Add metadata (disease, region)      │
        │  Format for LLM prompt               │
        │                                      │
        │  Output: Formatted context string    │
        │  Size: ~1000-2000 tokens             │
        └──────────────────┬───────────────────┘
                           │
        ┌──────────────────────────────────────┐
        │  STEP 6: LLM GENERATION              │
        │  Time: ~1-5s                         │
        │                                      │
        │  ┌─ PRIMARY: Gemini API              │
        │  │ ├─ Check rate limit               │
        │  │ ├─ Build prompt                   │
        │  │ ├─ Call API                       │
        │  │ └─ Stream response                │
        │  │   (1-2s)                          │
        │  │                                   │
        │  └─ FALLBACK: Ollama (if fails)      │
        │    ├─ Call local HTTP endpoint       │
        │    ├─ LLM processes query            │
        │    └─ Stream response                │
        │       (2-5s)                         │
        │                                      │
        │  Output: Natural language response   │
        │  Quality: Excellent (Gemini)         │
        │           Good (Ollama)              │
        │  Length: Up to 2000 tokens           │
        └──────────────────┬───────────────────┘
                           │
        ┌──────────────────────────────────────┐
        │  STEP 7: UI DISPLAY & STORAGE        │
        │  Time: Real-time (streaming)         │
        │                                      │
        │  Display to User:                    │
        │  ├─ Stream LLM response              │
        │  ├─ Show retrieved documents         │
        │  ├─ Display relevance scores         │
        │  └─ Show processing metrics          │
        │                                      │
        │  Save to Database:                   │
        │  ├─ Store query                      │
        │  ├─ Store response                   │
        │  ├─ Store documents used             │
        │  └─ Store timestamp                  │
        └──────────────────┬───────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────┐
│                    USER SEES RESPONSE                    │
│                                                          │
│  Response:                                              │
│  "Agnimandya is a condition where food is not properly │
│   digested due to diminished digestive power..."        │
│                                                          │
│  Sources: [Document 1, Document 2, ...]                │
│  Relevance: [92%, 87%, 84%, ...]                        │
│  Time: 2.5 - 6.0 seconds                               │
└──────────────────────────────────────────────────────────┘
```

---

## ⏱️ Detailed Timing Breakdown

### Per-Step Timing (on 8GB RAM, CPU)

```
┌─────────────────────────────────────────────────────────┐
│ OPERATION                              │ TIME    │ %    │
├─────────────────────────────────────────────────────────┤
│ Text Normalization (v2 only)           │ 10ms    │ 0.7% │
│ BM25 Search                            │ 15ms    │ 1.0% │
│ Vector Search                          │ 40ms    │ 2.7% │
│ RRF Fusion                             │ 5ms     │ 0.3% │
│ Reranking (20→5 docs)                  │ 60ms    │ 4.0% │
│ LLM Generation (Gemini)                │ 1500ms  │ 100% │ ◄─ Bottleneck
│ LLM Generation (Ollama)                │ 3500ms  │ 100% │ ◄─ Bottleneck
├─────────────────────────────────────────────────────────┤
│ TOTAL (with Gemini)                    │ 1.63s   │      │
│ TOTAL (with Ollama)                    │ 3.63s   │      │
├─────────────────────────────────────────────────────────┤
│ Network latency (if applicable)        │ 0-100ms │      │
│ UI rendering                           │ 20ms    │      │
└─────────────────────────────────────────────────────────┘
```

### Cumulative Timeline

```
Time (ms)    Operation                Progress
──────────────────────────────────────────────────────────
0ms          Start query
10ms         Normalize (v2)           ██
25ms         BM25 search complete     ███
65ms         Vector search complete   ████████
70ms         RRF fusion complete      ████████
130ms        Reranking complete       ████████████
1630ms       Gemini response ready    ████████████████████
3630ms       Ollama response ready    ████████████████████
              (or use whichever finished first)
```

---

## 🧠 Memory Usage During Processing

```
Timeline        Memory Usage         What's in RAM
──────────────────────────────────────────────────────
Startup:        ~2.0 GB
├─ Python:      200 MB
├─ Models:      1.5 GB (embeddings)
└─ Buffer:      300 MB

Query arrives:  ~2.1 GB
├─ Query str:   ~1 KB
└─ Buffer:      unchanged

Search phase:   ~2.5 GB
├─ BM25 index:  ~50 MB (always in RAM)
├─ Vector ops:  ~400 MB (FAISS + embeddings)
└─ Results:     ~10 MB

Reranking:      ~2.6 GB
├─ Top-20 docs: ~100 KB
├─ Cross-enc:   ~250 MB
└─ Scores:      ~10 KB

LLM phase:      ~2.1 GB
├─ Context:     ~50 KB
├─ LLM model:   1.0+ GB (Ollama)
│              or API call (Gemini)
└─ Buffer:      remaining

Response:       ~2.0 GB
├─ Full response: ~50 KB
└─ DB write:    ~10 KB

Final:          ~2.0 GB (ready for next query)
```

---

## 🔄 Query Examples with Full Flow

### Example 1: Simple Keyword Query

```
Query: "What is Agnidagdha?"

Step 1: Normalize (v2)
  Input:  "What is Agnidagdha?"
  Output: "What is agnidagdha?"
  Time: 0ms (already ASCII)

Step 2A: BM25 Search
  Tokenize: ["agnidagdha", "burns", "scalds"]
  Match: Disease "AGNIDAGDHA" has 100% token match
  Score: Very high (0.95)
  Time: 12ms

Step 2B: Vector Search
  Query vector: (384-dim, centered around "disease definition")
  Similarity: Matches docs about burn injuries
  Top doc score: 0.87 (high semantic match)
  Time: 38ms

Step 3: RRF Fusion
  Doc "AGNIDAGDHA":
    BM25: 0.95 → RRF 0.0164 (rank 1)
    Vector: 0.87 → RRF 0.0164 (rank 1)
    Combined: 0.0328 (tied for best)
  Time: 2ms

Step 4: Reranking (20→5)
  Cross-encoder scores:
    Doc 1 (AGNIDAGDHA): 0.96 ← High relevance
    Doc 2 (Burns): 0.89
    Doc 3 (Treatment): 0.88
    Doc 4 (Symptoms): 0.85
    Doc 5 (Preparations): 0.81
  Time: 45ms

Step 5: Context Building
  "Title: AGNIDAGDHA
   Sanskrit: अग्निदग्ध
   Definition: Injury caused by excessive heat...
   Symptoms: 1. Pluṣṭa: Simple burns
   Treatment: Cold water should not be applied..."
  Time: 5ms

Step 6: LLM Generation
  Gemini:
    "Agnidagdha is a classical Ayurvedic disease
     referring to burns and scalds caused by excessive heat.
     It is classified into four types based on severity..."
  Time: 1200ms

TOTAL: 1.31 seconds ✓ Fast response!
```

### Example 2: Complex Natural Language Query

```
Query: "AGNIMĀNDYA symptoms and treatment"  (with diacritics)

Step 1: Normalize (v2)
  Input:  "AGNIMĀNDYA symptoms and treatment"
  Output: "agnimandya symptoms and treatment"
  Time: 15ms (diacritics removed)

Step 2A: BM25 Search
  Tokenize: ["agnimandya", "symptom", "treatment"]
  Matches:
    - "AGNIMANDYA" doc: high (has disease + field match)
    - "Symptoms of Agnimandya": high (exact phrase)
    - "Treatment Guide": medium (has treatment)
  Time: 18ms

Step 2B: Vector Search
  Query embedding: Semantic meaning about "symptoms + treatment"
  Matches:
    - Clinical descriptions: high
    - Disease manifestations: high
    - Therapeutic approaches: medium-high
  Top score: 0.91
  Time: 42ms

Step 3: RRF Fusion
  Combined best docs about Agnimandya with treatment info
  20 unique docs selected
  Time: 3ms

Step 4: Reranking (20→5)
  Selects most relevant for combined query:
    Doc 1: Full "AGNIMANDYA" article (0.94)
    Doc 2: Symptoms section (0.92)
    Doc 3: Treatment options (0.89)
    Doc 4: Single drug remedies (0.87)
    Doc 5: Compound preparations (0.85)
  Time: 52ms

Step 5: Context Building
  Combines:
  - Definition
  - Detailed symptoms list
  - Treatment protocols
  - Ayurvedic preparations
  ~1800 tokens total
  Time: 8ms

Step 6: LLM Generation (Gemini)
  Produces comprehensive response covering:
  1. What is Agnimandya (definition)
  2. Key symptoms (list with explanations)
  3. Treatment approaches (different options)
  4. Specific preparations mentioned
  5. Lifestyle recommendations
  Time: 1800ms (longer response)

TOTAL: 1.94 seconds ✓ Still reasonable!
```

### Example 3: Gemini Fails, Ollama Fallback

```
Query: "Simple home remedy for indigestion"

[Search steps 1-5 same as above, 130ms total]

Step 6A: LLM Generation - Try Gemini
  Attempt: API call
  Rate Limit Error: "15 requests/min exceeded"
  Time: 100ms (fast failure detection)
  Action: Use fallback

Step 6B: LLM Generation - Use Ollama
  Switch to local Ollama
  Send prompt + context to localhost:11434
  Ollama processes query using llama2
  Generates response:
    "Common home remedies for indigestion include:
     1. Ginger tea...
     2. Fennel water..."
  Time: 3200ms (local processing)

Output:
  Response: [From Ollama]
  Label: "Generated by: Ollama (Gemini rate limited)"
  Quality: Still good, just slower

TOTAL: 3.43 seconds ✓ Fallback successful!
```

---

## 🎯 Performance Tuning Guide

### If Search is Slow (>200ms)

```
1. Reduce BM25_TOP_K
   BEFORE: BM25_TOP_K=20 (20ms)
   AFTER:  BM25_TOP_K=10 (12ms)
   Savings: ~8ms

2. Reduce VECTOR_TOP_K
   BEFORE: VECTOR_TOP_K=20 (40ms)
   AFTER:  VECTOR_TOP_K=10 (25ms)
   Savings: ~15ms

3. Use lighter embedding model
   BEFORE: all-MiniLM-L6-v2 (40ms)
   AFTER:  all-MiniLM-L12-v1 (35ms)
   Savings: ~5ms

4. Reduce FAISS search scope
   Use approximate index instead of exact
```

### If LLM Generation is Slow (>3s)

```
1. Use Gemini instead of Ollama
   Ollama:  3.5s (local, slow)
   Gemini:  1.5s (API, fast)
   Savings: ~2s

2. Lower MAX_TOKENS
   BEFORE: 2000 tokens (2.5s)
   AFTER:  1000 tokens (1.2s)
   Savings: ~1.3s

3. Use faster model with Ollama
   llama2:   3.5s
   mistral:  2.8s (faster)
   neural-chat: 2.5s (optimized)

4. Increase temperature (less thinking)
   BEFORE: 0.7 (careful answer)
   AFTER:  0.8 (faster, slight quality loss)
```

### If Memory is Low (<3GB free)

```
1. Reduce CHUNK_SIZE
   BEFORE: 800 characters
   AFTER:  400 characters
   Reduces index size by ~50%

2. Reduce embedding batch size
   BEFORE: 32 documents at once
   AFTER:  8 documents at once
   Spreads memory usage over time

3. Use approximate FAISS index
   Exact:  ~1GB for large corpus
   Approx: ~200MB for large corpus
   Savings: ~800MB

4. Close other applications
   Frees up 500MB-2GB depending on what's running
```

---

## 📊 End-to-End Timeline Visualization

### Typical Query (Gemini)

```
Time    |████████ Searching (130ms) ████████|
        |  ├─ Normalize (10ms)
        |  ├─ BM25 (15ms)
        |  ├─ Vector (40ms)
        |  ├─ RRF (5ms)
        |  └─ Rerank (60ms)
        |
        |████████████████████████████████████████ LLM Generation (1500ms)
        |  ├─ Build prompt (10ms)
        |  ├─ API call + streaming (1500ms)
        |  └─ Complete (20ms)
        |
        |████ Display & Store (30ms)
        
Total: ~1.66 seconds
```

### Typical Query (Ollama)

```
Time    |████████ Searching (130ms) ████████|
        |  └─ [Same as above]
        |
        |█████████████████████████████████████████████████████ LLM (3500ms)
        |  ├─ Local processing (3500ms)
        |
        |████ Display & Store (30ms)
        
Total: ~3.66 seconds
```

---

## 🔍 Monitoring & Debugging

### Enable Detailed Logging

```bash
# In .env
DEBUG_MODE=true
LOG_LEVEL=DEBUG

# Console output shows:
[10:30:45] Normalizing query...
[10:30:45] BM25 search: 15ms, 20 results
[10:30:45] Vector search: 38ms, 20 results
[10:30:45] RRF fusion: 2ms, 15 unique docs
[10:30:45] Reranking: 52ms, 5 final docs
[10:30:45] Building context: 8ms, 1847 tokens
[10:30:47] Gemini response: 1.8s, 256 tokens
```

### Profile Individual Steps

```python
import time

# Profile search
start = time.time()
results = rag.search(query)
print(f"Search time: {time.time() - start:.3f}s")

# Profile LLM
start = time.time()
response, model = llm.generate(query, context)
print(f"LLM time: {time.time() - start:.3f}s")
print(f"Model used: {model}")
```

---

## 🎓 Understanding the Bottleneck

**Key Finding:** LLM Generation is the bottleneck (80-90% of time)

### Why?
1. Network latency to Gemini API
2. Model processing time
3. Token generation (each token takes time)

### Solutions:
1. **Use Gemini (faster):** 1.5s vs 3.5s Ollama
2. **Lower max tokens:** Fewer tokens = faster
3. **Increase temperature:** Less careful, faster thinking
4. **Cache responses:** Don't regenerate for similar queries

### Trade-offs:
```
Speed vs Quality:
├─ Gemini + high tokens: Slow (2.5s) but best quality
├─ Gemini + medium tokens: Fast (1.5s) good quality
├─ Gemini + low tokens: Very fast (1.0s) lower quality
└─ Ollama: Slower (3.5s) but free & private

Speed vs Privacy:
├─ Gemini: Fast but data sent to Google
└─ Ollama: Slower but 100% local & private
```

---

**This visualization helps you understand:**
1. Where time is spent in the pipeline
2. What you can optimize for your needs
3. How fallback strategy works
4. Expected performance on 8GB RAM

For production deployment, monitor these metrics continuously and adjust parameters based on your actual usage patterns.

