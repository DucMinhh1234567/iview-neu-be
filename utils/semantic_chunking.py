"""
Semantic chunking utility using LangChain.
Handles text splitting and embedding generation for pgvector storage.
"""
import re
from typing import List, Dict, Any, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from config import EMBEDDING_MODEL, GEMINI_API_KEY


def get_current_chapter(text: str) -> Optional[str]:
    """
    Detect chapter heading in text.
    
    Args:
        text: Text to search for chapter heading
        
    Returns:
        Chapter heading string or None
    """
    pattern = r"""(?imx)
        ^\s*                                   # đầu dòng, có thể có khoảng trắng
        (?:chương|chuong|chapter)              # hỗ trợ cả tiếng Việt và tiếng Anh
        [\s.:;\-–—_]*                          # các ký tự ngăn cách
        (?:[ivxlcdm]+|\d+(?:[\.,]\d+)?)?       # số La Mã hoặc số thường (nếu có)
        [\s.:;\-–—_]*                          # ngăn cách thêm
        [^\n]*                                 # tiêu đề (nếu có)
    """
    match = re.search(pattern, text)
    return match.group().strip() if match else None


def clean_text_keep_printable(text: str) -> str:
    """
    Clean text by removing control characters and normalizing whitespace.
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text
    """
    import unicodedata
    
    cleaned = []
    for ch in text:
        if unicodedata.category(ch).startswith('C'):
            continue
        cleaned.append(ch)
    
    text = "".join(cleaned)
    text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    # Normalize multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def chunk_text_semantic(
    text: str,
    material_id: int,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[Dict[str, Any]]:
    """
    Chunk text using semantic-aware splitting.
    
    Args:
        text: Text to chunk
        material_id: Material ID for metadata
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of chunk dictionaries with metadata
    """
    # Clean text first
    cleaned_text = clean_text_keep_printable(text)
    
    # Use RecursiveCharacterTextSplitter for semantic chunking
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    chunks = text_splitter.split_text(cleaned_text)
    
    # Process chunks with metadata
    result_chunks = []
    current_offset = 0
    current_chapter = None
    
    for i, chunk_text in enumerate(chunks):
        # Detect chapter heading
        chapter = get_current_chapter(chunk_text)
        if chapter:
            current_chapter = chapter
        
        # Calculate offsets
        start_offset = current_offset
        end_offset = current_offset + len(chunk_text)
        
        result_chunks.append({
            "text": chunk_text,
            "chunk_index": i,
            "material_id": material_id,
            "chapter": current_chapter,
            "start_offset": start_offset,
            "end_offset": end_offset,
            "metadata": {
                "material_id": material_id,
                "chapter": current_chapter,
                "start_offset": start_offset,
                "end_offset": end_offset,
                "chunk_index": i
            }
        })
        
        current_offset = end_offset - chunk_overlap  # Account for overlap
    
    return result_chunks


def generate_embeddings(chunks: List[Dict[str, Any]]) -> List[List[float]]:
    """
    Generate embeddings for chunks using Gemini.
    
    Args:
        chunks: List of chunk dictionaries with 'text'
        
    Returns:
        List of embedding vectors
    """
    # Initialize embeddings
    embeddings_model = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=GEMINI_API_KEY
    )
    
    # Extract text from chunks
    texts = [chunk["text"] for chunk in chunks]
    
    # Generate embeddings
    embeddings = embeddings_model.embed_documents(texts)
    
    return embeddings


def process_material_semantic(
    text: str,
    material_id: int
) -> List[Dict[str, Any]]:
    """
    Main function to process material with semantic chunking.
    
    Args:
        text: Raw material text
        material_id: Material ID
        
    Returns:
        List of processed chunks with embeddings
    """
    # Chunk text semantically
    chunks = chunk_text_semantic(text, material_id)
    
    # Generate embeddings
    embeddings = generate_embeddings(chunks)
    
    # Add embeddings to chunks
    for i, chunk in enumerate(chunks):
        chunk["embedding"] = embeddings[i] if i < len(embeddings) else None
    
    return chunks

