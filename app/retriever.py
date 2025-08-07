"""
Enhanced retrieval with multiple strategies and ranking.
"""
import asyncio
from typing import List, Dict, Optional
from app.embeddings import embed_chunks_async
from app.vector_store import search_chunks_async
from app.parser import extract_question_intent_async

async def retrieve_top_chunks_async(query: str, doc_filter: Optional[str] = None, top_k: int = 15) -> List[Dict]:
    """
    Enhanced async retrieval with multiple strategies.
    """
    # Extract question intent for better retrieval
    intent = await extract_question_intent_async(query)
    
    # Generate embeddings for the query
    query_vectors = await embed_chunks_async([query])
    query_vector = query_vectors[0]
    
    if query_vector is None:
        return []
    
    # Adjust top_k based on question complexity
    adjusted_top_k = adjust_top_k_by_intent(intent, top_k)
    
    # Search chunks
    chunks = await search_chunks_async(
        query_vector, 
        filters={"document_id": doc_filter} if doc_filter else None, 
        top_k=adjusted_top_k
    )
    
    # Re-rank chunks based on intent
    ranked_chunks = await rerank_chunks_by_intent(chunks, intent, query)
    
    return ranked_chunks[:top_k]

def adjust_top_k_by_intent(intent: Dict, base_top_k: int) -> int:
    """Adjust retrieval count based on question intent"""
    if intent["question_type"] == "yes_no":
        return min(base_top_k, 10)  # Fewer chunks for yes/no questions
    elif intent["answer_type"] == "list":
        return min(base_top_k + 5, 25)  # More chunks for list questions
    else:
        return base_top_k

async def rerank_chunks_by_intent(chunks: List[Dict], intent: Dict, query: str) -> List[Dict]:
    """
    Re-rank chunks based on question intent and content relevance.
    """
    if not chunks:
        return chunks
    
    # Simple scoring based on content relevance
    scored_chunks = []
    
    for chunk in chunks:
        score = 0
        chunk_text = chunk.get("chunk", "").lower()
        
        # Boost score for key entities
        for entity in intent.get("key_entities", []):
            if entity.lower() in chunk_text:
                score += 2
        
        # Boost score for main topic
        topic = intent.get("main_topic", "")
        if topic in chunk_text:
            score += 3
        
        # Boost score for question-specific keywords
        if intent["question_type"] == "when" and any(word in chunk_text for word in ["period", "days", "months", "years"]):
            score += 2
        elif intent["question_type"] == "what" and any(word in chunk_text for word in ["means", "defined", "definition"]):
            score += 2
        
        chunk["relevance_score"] = score
        scored_chunks.append(chunk)
    
    # Sort by relevance score (descending) while maintaining vector similarity order for ties
    scored_chunks.sort(key=lambda x: (-x["relevance_score"], chunks.index(x)))
    
    return scored_chunks