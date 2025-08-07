# app/embeddings.py (Fixed version with correct vector format)
"""
Fixed async embedding generation with proper vector format.
"""
import asyncio
from typing import List, Optional
from app.gemini import GeminiClient
from dotenv import load_dotenv
import os

load_dotenv()

# Get API keys
api_keys_str = os.getenv("GOOGLE_API_KEY")
if not api_keys_str:
    raise ValueError("GOOGLE_API_KEY environment variable not set or empty.")

# Split and clean API keys
api_keys = [key.strip() for key in api_keys_str.split(",") if key.strip()]
client = GeminiClient(api_keys)

async def embed_chunks_async(chunks: List[str], batch_size: int = 5) -> List[Optional[List[float]]]:
    """
    Fixed async embedding generation that returns proper vector format.
    """
    if not chunks:
        print("No chunks provided for embedding")
        return []
    
    print(f"🔄 Generating embeddings for {len(chunks)} chunks...")
    embeddings = []
    
    # Process in smaller batches
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}")
        
        batch_tasks = [embed_single_chunk_async(chunk, idx + i) for idx, chunk in enumerate(batch)]
        batch_embeddings = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        for j, embedding in enumerate(batch_embeddings):
            if isinstance(embedding, Exception):
                print(f"❌ Error in batch embedding {i+j}: {embedding}")
                embeddings.append(None)
            elif embedding is None:
                print(f"⚠️ No embedding returned for chunk {i+j}")
                embeddings.append(None)
            else:
                print(f"✅ Generated embedding for chunk {i+j} (dimension: {len(embedding)})")
                embeddings.append(embedding)
        
        # Small delay between batches
        if i + batch_size < len(chunks):
            await asyncio.sleep(0.5)
    
    valid_embeddings = sum(1 for e in embeddings if e is not None)
    print(f"📊 Generated {valid_embeddings}/{len(chunks)} valid embeddings")
    
    return embeddings

async def embed_single_chunk_async(chunk: str, chunk_idx: int) -> Optional[List[float]]:
    """Embed a single chunk and return a flat list of floats"""
    if not chunk or len(chunk.strip()) < 5:
        print(f"⚠️ Chunk {chunk_idx} too short: '{chunk[:50]}...'")
        return None
    
    try:
        loop = asyncio.get_event_loop()
        raw_embedding = await loop.run_in_executor(None, client.embed_text, chunk)
        
        # Normalize the embedding to a flat list of floats
        normalized = normalize_embedding(raw_embedding)
        
        if normalized is not None:
            print(f"✅ Embedding generated for chunk {chunk_idx}, dimension: {len(normalized)}")
            return normalized
        else:
            print(f"❌ Failed to normalize embedding for chunk {chunk_idx}")
            return None
            
    except Exception as e:
        print(f"❌ Error embedding chunk {chunk_idx}: {e}")
        return None

def normalize_embedding(raw_embedding) -> Optional[List[float]]:
    """Normalize embedding to a flat list of floats"""
    if raw_embedding is None:
        return None
    
    # Handle list format
    if isinstance(raw_embedding, list):
        if len(raw_embedding) == 0:
            return None
        
        # If it's a nested list, take the first element
        if isinstance(raw_embedding[0], list):
            if len(raw_embedding[0]) > 0:
                embedding = raw_embedding[0]
            else:
                return None
        else:
            embedding = raw_embedding
        
        # Convert to flat list of floats
        try:
            normalized = [float(x) for x in embedding]
            if len(normalized) > 0:
                return normalized
        except (ValueError, TypeError) as e:
            print(f"Error converting embedding to floats: {e}")
            return None
    
    # Handle other formats
    elif hasattr(raw_embedding, 'embedding'):
        return normalize_embedding(raw_embedding.embedding)
    
    elif isinstance(raw_embedding, dict) and 'embedding' in raw_embedding:
        return normalize_embedding(raw_embedding['embedding'])
    
    print(f"Unknown embedding format: {type(raw_embedding)}")
    return None

# Test function
async def test_embeddings():
    """Test function to verify embeddings work correctly"""
    test_texts = ["This is a test sentence.", "Another test sentence for embedding."]
    embeddings = await embed_chunks_async(test_texts)
    
    success_count = 0
    for i, embedding in enumerate(embeddings):
        if embedding is not None:
            print(f"Test {i}: ✅ Success - dimension: {len(embedding)}")
            success_count += 1
        else:
            print(f"Test {i}: ❌ Failed")
    
    print(f"Test results: {success_count}/{len(test_texts)} successful")
    return success_count == len(test_texts)

if __name__ == "__main__":
    # Test embeddings when run directly
    asyncio.run(test_embeddings())