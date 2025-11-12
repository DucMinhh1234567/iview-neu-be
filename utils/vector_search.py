"""
Vector search utility for pgvector semantic similarity search.
"""
from typing import List, Dict, Any, Optional
import json
import math
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from extensions.supabase_client import supabase

from config import EMBEDDING_MODEL, GEMINI_API_KEY, MAX_CHUNKS_PER_QUESTION


def query_similar_chunks(
    material_id: int,
    query: str,
    k: int = MAX_CHUNKS_PER_QUESTION,
    filter_dict: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Query pgvector for similar chunks using semantic search.
    
    Args:
        material_id: Material ID to search in
        query: Query text
        k: Number of results to return
        filter_dict: Optional metadata filters
        
    Returns:
        List of similar chunks with similarity scores
    """
    try:
        # Generate query embedding
        embeddings_model = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            google_api_key=GEMINI_API_KEY
        )
        query_embedding = embeddings_model.embed_query(query)
        
        # Build SQL query for pgvector
        # Use cosine distance operator <=>
        sql = f"""
        SELECT 
            id,
            material_id,
            chunk_text,
            chunk_index,
            metadata,
            1 - (embedding <=> %s::vector) as similarity
        FROM material_chunks
        WHERE material_id = %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """
        
        # Execute query using Supabase RPC or direct SQL
        # Note: Supabase-py might not support raw SQL directly
        # We'll need to use a different approach
        
        # Alternative: Use Supabase's vector search if available
        # Or use a custom RPC function in Supabase
        
        # For now, we'll fetch all chunks for the material and compute similarity in Python
        # This is not ideal but works for MVP
        # In production, create a PostgreSQL function for vector search
        
        # Fetch chunks from database
        chunks_response = supabase.table("material_chunks").select("*").eq("material_id", material_id).execute()
        
        if not chunks_response.data:
            return []
        
        # Compute cosine similarity in Python
        # Note: For production, consider creating a PostgreSQL function for vector search
        
        query_vec = query_embedding
        query_norm = math.sqrt(sum(x * x for x in query_vec))
        results = []
        
        for chunk in chunks_response.data:
            embedding = chunk.get("embedding")
            
            # Parse embedding if it's a string (JSON format from Supabase)
            # Supabase returns pgvector embeddings as JSON strings
            if isinstance(embedding, str):
                try:
                    embedding = json.loads(embedding)
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Warning: Failed to parse embedding for chunk {chunk.get('id')}: {e}")
                    continue
            
            if not embedding or not isinstance(embedding, list):
                continue
            
            # Cosine similarity
            dot_product = sum(a * b for a, b in zip(query_vec, embedding))
            chunk_norm = math.sqrt(sum(x * x for x in embedding))
            
            if chunk_norm == 0:
                similarity = 0.0
            else:
                similarity = dot_product / (query_norm * chunk_norm)
            
            results.append({
                "id": chunk["id"],
                "material_id": chunk["material_id"],
                "chunk_text": chunk["chunk_text"],
                "chunk_index": chunk["chunk_index"],
                "metadata": chunk.get("metadata", {}),
                "similarity": float(similarity)
            })
        
        # Sort by similarity and return top k
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:k]
        
    except Exception as e:
        print(f"Vector search error: {e}")
        # Fallback: return random chunks
        return get_random_chunks_fallback(material_id, k)


def get_random_chunks_fallback(material_id: int, k: int) -> List[Dict[str, Any]]:
    """
    Fallback: Get random chunks if vector search fails.
    
    Args:
        material_id: Material ID
        k: Number of chunks to return
        
    Returns:
        List of random chunks
    """
    try:
        chunks_response = supabase.table("material_chunks").select("*").eq("material_id", material_id).limit(k).execute()
        
        if not chunks_response.data:
            return []
        
        return [
            {
                "id": chunk["id"],
                "material_id": chunk["material_id"],
                "chunk_text": chunk["chunk_text"],
                "chunk_index": chunk["chunk_index"],
                "metadata": chunk.get("metadata", {}),
                "similarity": 0.0
            }
            for chunk in chunks_response.data
        ]
    except Exception as e:
        print(f"Fallback chunk retrieval error: {e}")
        return []


def search_for_question_generation(
    material_id: int,
    query: str = "general knowledge",
    k: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Search for chunks to use in question generation.
    
    Args:
        material_id: Material ID
        query: Search query (default: "general knowledge")
        k: Number of chunks (default: MAX_CHUNKS_PER_QUESTION * 2)
        
    Returns:
        List of relevant chunks
    """
    if k is None:
        k = MAX_CHUNKS_PER_QUESTION * 2
    
    return query_similar_chunks(material_id, query, k)

