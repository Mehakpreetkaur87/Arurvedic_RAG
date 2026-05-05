"""
================================================================================
SYSTEM CHECK SCRIPT - Verify RAG System Status
================================================================================
Check all components of the RAG system are properly configured.

Usage:
    python scripts/check_system.py

Output:
    ✅ - Component working
    ⚠️  - Component available but not configured
    ❌ - Component not available
    
Author: RAG System
================================================================================
"""

import os
import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()


def check_python_version():
    """Check Python version."""
    import sys
    version = sys.version_info
    required = (3, 9)
    
    if (version.major, version.minor) >= required:
        return "✅", f"Python {version.major}.{version.minor}.{version.micro}"
    else:
        return "❌", f"Python {version.major}.{version.minor} (need 3.9+)"


def check_dependencies():
    """Check if all dependencies are installed."""
    dependencies = [
        'streamlit', 'sentence_transformers', 'faiss',
        'rank_bm25', 'google.generativeai', 'requests'
    ]
    
    status = "✅"
    missing = []
    
    for dep in dependencies:
        try:
            __import__(dep.replace('.', '/'))
        except ImportError:
            missing.append(dep)
            status = "❌"
    
    if missing:
        return status, f"Missing: {', '.join(missing)}"
    else:
        return status, "All dependencies installed"


def check_environment():
    """Check environment configuration."""
    
    checks = {
        "GEMINI_API_KEY": os.getenv('GEMINI_API_KEY'),
        "PRIMARY_LLM": os.getenv('PRIMARY_LLM', 'gemini'),
        "FALLBACK_LLM": os.getenv('FALLBACK_LLM', 'ollama'),
        "DEVICE": os.getenv('DEVICE', 'cpu'),
    }
    
    missing = [k for k, v in checks.items() if not v]
    
    if missing:
        return "⚠️ ", f"Missing: {', '.join(missing)}"
    else:
        return "✅", "All environment variables set"


def check_files():
    """Check if necessary files exist."""
    
    required_files = {
        '.env': '.env configuration file',
        'requirements.txt': 'Dependencies file',
        'pipeline.py': 'RAG pipeline module',
        'llm_handler.py': 'LLM handler module',
        'app.py': 'Streamlit application',
        'scripts/initialize.py': 'Initialization script',
    }
    
    missing = []
    for file_path, description in required_files.items():
        if not Path(file_path).exists():
            missing.append(f"{file_path}")
    
    if missing:
        return "❌", f"Missing: {', '.join(missing)}"
    else:
        return "✅", "All files present"


def check_indices():
    """Check if indices are built."""
    
    index_files = {
        'data/faiss_index/faiss_index.bin': 'FAISS vector index',
        'data/faiss_index/bm25_index.pkl': 'BM25 keyword index',
        'data/metadata.json': 'Metadata file',
    }
    
    missing = []
    for file_path, description in index_files.items():
        if not Path(file_path).exists():
            missing.append(description)
    
    if missing:
        return "❌", f"Missing: {', '.join(missing)}. Run: python scripts/initialize.py"
    else:
        return "✅", "All indices built"


def check_database():
    """Check if database exists."""
    
    db_path = Path('data/chat_history.db')
    
    if db_path.exists():
        size_mb = db_path.stat().st_size / 1024 / 1024
        return "✅", f"Database exists ({size_mb:.2f} MB)"
    else:
        return "⚠️ ", "Database not yet created (will be created on first run)"


def check_gemini():
    """Check Google Gemini API availability."""
    
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        return "⚠️ ", "GEMINI_API_KEY not set"
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        # Try a simple call
        response = model.generate_content("Test", stream=False)
        if response.text:
            return "✅", "Connected and working"
        else:
            return "⚠️ ", "Connected but no response"
    except Exception as e:
        return "❌", f"Error: {str(e)[:50]}"


def check_ollama():
    """Check Ollama local LLM availability."""
    
    ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    
    try:
        import requests
        response = requests.get(f"{ollama_url}/api/tags", timeout=3)
        
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            
            if models:
                model_names = [m['name'] for m in models]
                return "✅", f"Running. Models: {', '.join(model_names[:2])}"
            else:
                return "⚠️ ", "Running but no models. Run: ollama pull llama2"
        else:
            return "❌", f"Status {response.status_code}"
    
    except requests.exceptions.ConnectionError:
        return "❌", f"Not running at {ollama_url}"
    except Exception as e:
        return "❌", f"Error: {str(e)[:40]}"


def check_knowledge_base():
    """Check knowledge base files."""
    
    kb_path = Path('data/knowledge_base')
    
    if not kb_path.exists():
        return "❌", "data/knowledge_base/ directory not found"
    
    files = list(kb_path.glob("*"))
    
    if not files:
        return "⚠️ ", "Directory empty. Add JSON/TXT files and run initialize.py"
    else:
        return "✅", f"Found {len(files)} files"


def check_memory():
    """Check available system memory."""
    
    try:
        import psutil
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)
        total_gb = memory.total / (1024**3)
        
        if available_gb >= 4:
            return "✅", f"{available_gb:.1f}GB available (of {total_gb:.1f}GB total)"
        elif available_gb >= 2:
            return "⚠️ ", f"{available_gb:.1f}GB available (minimum 4GB recommended)"
        else:
            return "❌", f"Only {available_gb:.1f}GB available (need at least 2GB)"
    except ImportError:
        return "⚠️ ", "psutil not installed (memory check skipped)"
    except Exception as e:
        return "⚠️ ", f"Error checking memory: {e}"


def check_disk_space():
    """Check available disk space."""
    
    try:
        import shutil
        disk = shutil.disk_usage('/')
        available_gb = disk.free / (1024**3)
        
        if available_gb >= 5:
            return "✅", f"{available_gb:.1f}GB available"
        elif available_gb >= 2:
            return "⚠️ ", f"{available_gb:.1f}GB available (5GB recommended)"
        else:
            return "❌", f"Only {available_gb:.1f}GB available"
    except Exception as e:
        return "⚠️ ", f"Error checking disk: {e}"


def print_header(text):
    """Print formatted header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}")


def print_check(name, status, detail):
    """Print a single check result."""
    print(f"{status} {name:.<45} {detail}")


def main():
    """Main function."""
    
    print_header("AYURVEDA RAG SYSTEM - STATUS CHECK")
    
    # System
    print_header("SYSTEM REQUIREMENTS")
    
    status, detail = check_python_version()
    print_check("Python Version", status, detail)
    
    status, detail = check_memory()
    print_check("RAM Available", status, detail)
    
    status, detail = check_disk_space()
    print_check("Disk Space", status, detail)
    
    # Files
    print_header("PROJECT FILES")
    
    status, detail = check_files()
    print_check("Core Files", status, detail)
    
    status, detail = check_dependencies()
    print_check("Python Dependencies", status, detail)
    
    status, detail = check_environment()
    print_check("Environment Config", status, detail)
    
    # Indices
    print_header("RAG PIPELINE COMPONENTS")
    
    status, detail = check_knowledge_base()
    print_check("Knowledge Base", status, detail)
    
    status, detail = check_indices()
    print_check("Search Indices", status, detail)
    
    status, detail = check_database()
    print_check("Chat Database", status, detail)
    
    # LLMs
    print_header("LLM AVAILABILITY")
    
    status, detail = check_gemini()
    print_check("Google Gemini", status, detail)
    
    status, detail = check_ollama()
    print_check("Ollama Local", status, detail)
    
    # Summary
    print_header("SUMMARY")
    
    print("""
✅ All systems operational
⚠️  Some optional components not configured
❌ Critical component missing

NEXT STEPS:
1. If indices missing: python scripts/initialize.py
2. If Gemini needed: Set GEMINI_API_KEY in .env
3. If Ollama needed: Run 'ollama serve' in another terminal
4. Then run: streamlit run app.py
    """)
    
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
