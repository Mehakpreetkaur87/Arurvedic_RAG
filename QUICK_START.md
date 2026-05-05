# 🚀 Quick Start Guide - Ayurveda RAG Chatbot

Complete setup instructions for running the Ayurveda RAG system on your 8GB RAM system.

## ⏱️ Estimated Setup Time: 10-15 minutes

---

## Step 1: Prerequisites Check ✅

**System Requirements:**
- RAM: 8GB minimum (16GB recommended)
- Disk: 10GB free
- Python: 3.9 or higher
- OS: Windows, macOS, or Linux

**Check Python version:**
```bash
python --version
# Should be Python 3.9 or higher
```

---

## Step 2: Clone/Setup Project 📁

```bash
# Create and navigate to project directory
mkdir ayurveda-rag
cd ayurveda-rag

# Clone the project files or copy them here
# git clone <repository-url>
```

---

## Step 3: Create Virtual Environment 🔒

This isolates dependencies and prevents conflicts.

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**On macOS/Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

**Verify activation:**
```bash
# You should see (venv) in your terminal
which python  # Should show path inside venv
```

---

## Step 4: Install Dependencies 📦

```bash
# First, upgrade pip
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt

# This downloads ~2GB of models on first run
# Be patient! It may take 5-10 minutes
```

**If you get memory errors:**
```bash
# Install with smaller batches
pip install --no-cache-dir -r requirements.txt
```

---

## Step 5: Configure Environment 🔑

```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your settings
```

**Edit `.env` file (important fields):**

```ini
# Option A: Use Google Gemini (Recommended for 8GB RAM)
GEMINI_API_KEY=your_api_key_here
PRIMARY_LLM=gemini
FALLBACK_LLM=ollama

# Option B: Use Ollama only (No internet required)
PRIMARY_LLM=ollama
FALLBACK_LLM=gemini
OLLAMA_BASE_URL=http://localhost:11434

# System optimization for 8GB RAM
DEVICE=cpu
CHUNK_SIZE=800
BATCH_SIZE=8
```

**Getting Google Gemini API Key (Free):**
1. Go to https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key
4. Paste into `.env` file

---

## Step 6: Prepare Knowledge Base 📚

```bash
# Create data directory
mkdir -p data/knowledge_base

# Add your Ayurveda data files here:
# - ayurveda_diseases.json (JSON format)
# - ayurveda_texts.txt (Text format)
```

**Sample file format (JSON):**
```json
[
  {
    "id": "1",
    "title": "AGNIDAGDHA",
    "title_dev": "अग्निदग्ध",
    "intro": "Injury caused with the contact of excessive heat...",
    "symptoms": "1. Pluṣṭa: Simple burns...",
    "treatment": "Cold water should not be applied..."
  }
]
```

---

## Step 7: Initialize System 🔧

This builds search indices and initializes the database.

```bash
# Run initialization (takes 2-5 minutes first time)
python scripts/initialize.py

# Output should show:
# ✅ BM25 index built
# ✅ FAISS index built
# ✅ Database initialized
```

**If errors occur:**
```bash
# Force rebuild
python scripts/initialize.py --rebuild

# Check logs
cat logs/initialize.log
```

---

## Step 8 (Optional): Setup Local LLM with Ollama 🤖

For offline capability and no API costs:

**Install Ollama:**
1. Download from https://ollama.ai
2. Install for your OS

**Download a model:**
```bash
# Terminal 1: Start Ollama service
ollama serve

# Terminal 2 (new window): Download model
ollama pull llama2
# or
ollama pull mistral

# Verify installation
curl http://localhost:11434/api/tags
```

**In your `.env`, ensure:**
```
PRIMARY_LLM=ollama
OLLAMA_BASE_URL=http://localhost:11434
```

---

## Step 9: Run Application 🎯

**Terminal 1: Start Streamlit UI**
```bash
streamlit run app.py

# Output should show:
#   You can now view your Streamlit app in your browser.
#   Local URL: http://localhost:8501
```

**Terminal 2 (Optional): Start Ollama**
```bash
ollama serve
```

**Open in Browser:**
```
http://localhost:8501
```

---

## ✅ Success Check List

You should see:

- [ ] Streamlit UI loads without errors
- [ ] Chat input field visible
- [ ] Sidebar shows "Pipeline: ✅ Ready"
- [ ] At least one LLM available (Gemini ✅ OR Ollama ✅)
- [ ] Can type and send a message

---

## 🧪 Test Queries

Try these queries to test the system:

```
1. "What is Agnimandya?"
2. "Tell me about burns treatment"
3. "What are simple home remedies for indigestion?"
4. "List symptoms of Agnidagdha"
5. "How to prepare Ashwagandha treatment?"
```

---

## 🐛 Troubleshooting

### ❌ "Pipeline not initialized"
```bash
# Run initialization
python scripts/initialize.py

# Check if data files exist
ls data/knowledge_base/
```

### ❌ "GEMINI_API_KEY invalid"
```bash
# Verify key is set
grep GEMINI_API_KEY .env

# Check it's not empty
cat .env | grep GEMINI_API_KEY
```

### ❌ "Ollama connection refused"
```bash
# Start Ollama in a new terminal
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

### ❌ "Out of Memory"
```bash
# Reduce chunk size in .env
CHUNK_SIZE=400
BATCH_SIZE=4

# Rebuild indices
python scripts/initialize.py --rebuild
```

### ❌ "Streamlit not updating"
```bash
# Clear cache and restart
streamlit cache clear
streamlit run app.py
```

### ❌ "Models downloading very slowly"
```bash
# Use smaller models (update in pipeline.py)
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L12-v1

# Then rebuild
python scripts/initialize.py --rebuild
```

---

## 📊 System Resource Usage

**Typical Memory Usage (8GB RAM):**
```
Python Runtime:           ~200 MB
Embedding Model (cache):  ~500 MB
FAISS Index:             ~500-1000 MB
Streamlit:               ~300 MB
Available for query:     ~5-6 GB
```

**Typical Query Times:**
- Search: ~300ms
- Reranking: ~50ms
- LLM Generation: ~2-5s
- **Total: ~2.5-6s per query**

---

## 🎓 Understanding the Pipeline

```
USER QUERY
    ↓
[SEARCH - 350ms]
├─ BM25 (Keyword) Search
├─ Vector (Semantic) Search
└─ RRF Fusion
    ↓
[RERANK - 50ms]
├─ Cross-Encoder scoring
└─ Top-5 results
    ↓
[LLM GENERATION - 2-5s]
├─ Primary: Google Gemini
├─ Fallback: Ollama
└─ Stream response
    ↓
USER SEES RESPONSE + STORED IN DB
```

---

## 🔒 Privacy & Security

- **Local files only:** All indices stored locally
- **Optional cloud:** Gemini API is optional (use Ollama for offline)
- **No data logging:** Conversations stored in local SQLite only
- **API keys:** Never commit `.env` to git (.gitignore prevents this)

---

## 📚 Next Steps

1. **Add your data:** Place Ayurveda documents in `data/knowledge_base/`
2. **Customize:** Edit `.env` for your preferences
3. **Deploy:** See `DEPLOYMENT.md` for production setup
4. **Integrate:** Use `pipeline.py` in your own applications

---

## 📖 Full Documentation

For detailed information, see:
- **README.md** - Complete project documentation
- **pipeline.py** - RAG pipeline (well-commented)
- **llm_handler.py** - LLM integration details
- **app.py** - Streamlit UI code

---

## ⚡ Quick Command Reference

```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Initialize system
python scripts/initialize.py

# Run application
streamlit run app.py

# View chat history
python scripts/view_history.py

# Clear all history
python scripts/clear_history.py

# Test single query
python scripts/test_query.py "What is Agnimandya?"

# Check system status
python scripts/check_system.py
```

---

## 🆘 Need Help?

**Common Issues:**
1. Check README.md Troubleshooting section
2. Verify .env configuration
3. Review logs in `logs/` directory
4. Check console output for error messages

**Contact:**
- Documentation: README.md
- Issues: Check GitHub issues
- Discussions: See CONTRIBUTING.md

---

## 🎉 You're All Set!

Your Ayurveda RAG Chatbot is ready!

```
Open: http://localhost:8501
Type: "What is Agnimandya?"
Get: Instant Ayurvedic wisdom! 🌿
```

---

**Happy Querying!** 🎯

*Estimated time to first successful query: 5-10 minutes after running `streamlit run app.py`*
