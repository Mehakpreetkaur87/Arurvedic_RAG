# 🌿 Ayurveda RAG Chatbot - START HERE

Welcome! This is a **complete, production-ready Retrieval-Augmented Generation (RAG) system** for querying Ayurvedic medicine knowledge base.

---

## ⚡ Quick Start (5 minutes)

### 1️⃣ **Clone/Setup Project**
```bash
# Navigate to project directory
cd ayurveda-rag

# Create virtual environment
python -m venv venv

# Activate (choose your OS)
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 2️⃣ **Install Dependencies**
```bash
pip install -r requirements.txt
# This downloads ~2GB of ML models (be patient!)
```

### 3️⃣ **Configure**
```bash
# Copy example config
cp .env.example .env

# Edit .env with your settings:
# - Add GEMINI_API_KEY if you have one
# - Set PRIMARY_LLM (gemini or ollama)
```

### 4️⃣ **Initialize System**
```bash
# Build search indices
python scripts/initialize.py

# Creates FAISS indices, BM25 index, and database
```

### 5️⃣ **Run Application**
```bash
# Start Streamlit app
streamlit run app.py

# Opens at: http://localhost:8501
```

### 6️⃣ **Query!**
```
Type questions like:
- "What is Agnimandya?"
- "How to treat burns?"
- "Symptoms of indigestion?"
```

---

## 📖 Documentation Guide

Choose based on your role:

### 👤 **I just want to use it**
→ Read: **QUICK_START.md** (10-15 minutes)
- Step-by-step setup
- Example queries
- Basic troubleshooting

### 👨‍💻 **I want to understand the code**
→ Read: **ARCHITECTURE.md** (30 minutes)
- System architecture
- Component explanations
- Design decisions

### 🔧 **I want to configure/deploy it**
→ Read: **IMPLEMENTATION_SUMMARY.md** (20 minutes)
- Configuration options
- Performance tuning
- Deployment guide

### 📊 **I want to see the flow**
→ Read: **PIPELINE_FLOW.md** (15 minutes)
- Visual pipelines
- Timing breakdown
- Complete examples

### 📚 **I want everything**
→ Read: **README.md** (complete reference)
- Comprehensive guide (2000+ lines)
- All details covered
- Index of all topics

---

## 🎯 What This System Does

```
Your Question
    ↓
🔍 Smart Search (BM25 + Vector)
    ↓
⭐ Ranking & Reranking
    ↓
🤖 AI Response (Gemini or Ollama)
    ↓
💬 Answer + Sources + Scores
```

### Key Features
- ✅ **Hybrid Search**: Keyword + semantic matching
- ✅ **LLM Integration**: Google Gemini + Ollama fallback
- ✅ **Chat UI**: Real-time responses
- ✅ **Chat History**: SQLite database
- ✅ **Easy Config**: 70+ parameters via .env
- ✅ **Optimized**: Works great on 8GB RAM

---

## 📁 What You Get

```
📦 Complete RAG System
├── 🐍 Core Code (2800 lines)
│   ├── pipeline.py (RAG engine)
│   ├── llm_handler.py (LLM integration)
│   └── app.py (Streamlit UI)
│
├── 🧪 Test Scripts
│   ├── scripts/initialize.py (Build indices)
│   ├── scripts/test_query.py (CLI testing)
│   └── scripts/check_system.py (Health check)
│
├── 📚 Documentation (5000+ lines)
│   ├── README.md (comprehensive)
│   ├── QUICK_START.md (fast setup)
│   ├── ARCHITECTURE.md (technical)
│   ├── PIPELINE_FLOW.md (visual)
│   └── IMPLEMENTATION_SUMMARY.md (overview)
│
└── ⚙️ Configuration
    ├── .env.example (parameter template)
    ├── requirements.txt (dependencies)
    └── .gitignore (security)
```

---

## 🚀 Common Tasks

### Check if everything is installed
```bash
python scripts/check_system.py
```
Shows: ✅ Python | ✅ RAM | ✅ Dependencies | ✅ APIs

### Test without UI
```bash
python scripts/test_query.py "What is Agnimandya?"
```
Shows: Search results → LLM response

### View chat history
```bash
# Manually in app: Sidebar → Load History
# Or programmatically:
from pipeline import RAGPipeline
rag = RAGPipeline()
history = rag.get_chat_history(limit=10)
for conv in history:
    print(f"Q: {conv['query']}")
    print(f"A: {conv['response']}\n")
```

### Clear all data
```bash
# Delete indices and history
rm -rf data/
# Then rebuild
python scripts/initialize.py
```

---

## ⚙️ Configuration (Most Important)

Edit `.env` file (created from `.env.example`):

**Essential Options:**
```ini
# For cloud LLM (fast, needs API key)
GEMINI_API_KEY=your_key_from_makersuite.google.com
PRIMARY_LLM=gemini

# For local LLM (free, private, slower)
# First: ollama pull llama2
PRIMARY_LLM=ollama
OLLAMA_BASE_URL=http://localhost:11434

# General settings
DEVICE=cpu              # CPU for 8GB RAM
MAX_TOKENS=2000        # Response length
TEMPERATURE=0.7        # Creativity (0=deterministic, 1=random)
```

**Search Options:**
```ini
BM25_TOP_K=20          # Keyword search results
VECTOR_TOP_K=20        # Semantic search results
RERANK_TOP_K=5         # Final results (keep this small)
```

**Performance:**
```ini
CHUNK_SIZE=800         # Smaller = more chunks, slower
BATCH_SIZE=8           # Smaller = less memory
ENABLE_NORMALIZATION=false  # Set true for v2
DEBUG_MODE=false       # Set true for detailed logs
```

---

## 🆘 Quick Troubleshooting

### "Pipeline not initialized"
```bash
python scripts/initialize.py
# Takes 2-5 minutes first time
```

### "GEMINI_API_KEY invalid"
1. Go to https://makersuite.google.com/app/apikey
2. Create API key
3. Copy to `.env`: `GEMINI_API_KEY=...`

### "Ollama connection refused"
```bash
# In new terminal:
ollama serve

# Then in another terminal:
ollama pull llama2
```

### "Out of memory"
```ini
# In .env:
CHUNK_SIZE=400         # Reduce from 800
BATCH_SIZE=4           # Reduce from 8
DEVICE=cpu            # Ensure CPU not GPU
```

### "Slow responses"
- Use Gemini instead of Ollama (1.5s vs 3.5s)
- Lower MAX_TOKENS (less to generate)
- Close other applications

See **README.md** → Troubleshooting for more

---

## 💡 Understanding the System

### Simple Explanation
1. **You ask a question**
2. **System searches knowledge base** (BM25 + Vector)
3. **System reranks best results** (Cross-encoder)
4. **System builds context**
5. **AI generates answer** (Gemini or Ollama)
6. **You see response + sources**

### Technical Explanation
- **BM25**: Keyword matching (fast, exact)
- **Vector**: Semantic matching (slower, smarter)
- **RRF Fusion**: Combines both methods
- **Reranking**: Precision improvement (+10-20%)
- **LLM**: Generates final answer
- **Fallback**: If Gemini fails, uses Ollama

See **ARCHITECTURE.md** for full technical details

---

## 📊 Expected Performance

### Speed
| Operation | Time |
|-----------|------|
| Search | ~130ms |
| Rerank | ~50ms |
| LLM (Gemini) | 1-2s |
| LLM (Ollama) | 2-5s |
| **Total** | **2-6s** |

### Memory
| Component | Size |
|-----------|------|
| Python | ~200MB |
| Models | ~1.5GB |
| Indices | ~500MB |
| Buffer | ~5.8GB |
| **Total** | ~8GB |

---

## 🎓 Learning Path

**Day 1: Get Running**
1. Follow QUICK_START.md
2. Run `python scripts/initialize.py`
3. Run `streamlit run app.py`
4. Try some queries

**Day 2: Understand System**
1. Read ARCHITECTURE.md
2. Read code comments in pipeline.py
3. Try test_query.py for CLI testing

**Day 3: Customize**
1. Adjust .env parameters
2. Add your own knowledge base
3. Test performance
4. Tune for your data

**Day 4+: Deploy/Extend**
1. Read IMPLEMENTATION_SUMMARY.md
2. Set up production deployment
3. Add custom features
4. Monitor performance

---

## 🔧 Common Customizations

### Change LLM
```ini
# .env
PRIMARY_LLM=gemini      # Fast, cloud, paid
PRIMARY_LLM=ollama      # Slow, local, free
FALLBACK_LLM=ollama     # Fallback to this if primary fails
```

### Add Your Data
```bash
# Place files in:
data/knowledge_base/
├── ayurveda_diseases.json
├── ayurveda_remedies.json
└── ayurveda_texts.txt

# Then rebuild:
python scripts/initialize.py --rebuild
```

### Tune for Speed
```ini
# .env
BM25_TOP_K=10          # Reduce from 20
VECTOR_TOP_K=10        # Reduce from 20
MAX_TOKENS=1000        # Reduce from 2000
TEMPERATURE=0.8        # Increase from 0.7
```

### Tune for Quality
```ini
# .env
BM25_TOP_K=30          # Increase from 20
VECTOR_TOP_K=30        # Increase from 20
MAX_TOKENS=3000        # Increase from 2000
TEMPERATURE=0.5        # Decrease from 0.7
```

---

## 📞 Getting Help

### Documentation
- **README.md**: Full reference
- **QUICK_START.md**: Setup guide
- **ARCHITECTURE.md**: Technical details
- **PIPELINE_FLOW.md**: Visual examples
- Code comments: Explained in code

### Scripts
- **check_system.py**: Verify installation
- **test_query.py**: Test without UI
- **initialize.py**: Build indices

### Debug
```bash
# Verbose output
DEBUG_MODE=true streamlit run app.py

# or in .env:
DEBUG_MODE=true
```

---

## 🎉 You're All Set!

✅ Everything is ready to use
✅ Documentation is comprehensive  
✅ Code is well-commented
✅ Examples are included

### Next: Choose Your Path

- **👤 User**: Read QUICK_START.md → Run app
- **👨‍💻 Developer**: Read ARCHITECTURE.md → Review code
- **🔧 DevOps**: Read IMPLEMENTATION_SUMMARY.md → Deploy
- **🎓 Learner**: Read README.md → Learn everything

---

## 🚀 Start Now

```bash
# 1. Copy config
cp .env.example .env

# 2. Initialize
python scripts/initialize.py

# 3. Run
streamlit run app.py

# 4. Visit
# http://localhost:8501

# 5. Query!
# Type: "What is Agnimandya?"
```

---

## ✨ Key Features

- 🔍 **Hybrid Search** (BM25 + Vector)
- ⭐ **Reranking** (Precision improvement)
- 🤖 **AI Responses** (Gemini + Ollama)
- 💬 **Chat UI** (Streamlit)
- 💾 **History** (SQLite)
- ⚙️ **Configurable** (70+ options)
- 📚 **Documented** (5000+ lines)
- 🎓 **Learning** (Well-commented code)

---

**Questions?** Check documentation.  
**Ready?** Run `streamlit run app.py`  
**Enjoy!** 🌿

---

*For detailed information, read the README.md file*
*For quick setup, read the QUICK_START.md file*
*For technical details, read the ARCHITECTURE.md file*
