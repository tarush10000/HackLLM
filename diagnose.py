#!/usr/bin/env python3
"""
Local System Vector Dimension Diagnostic and Fix
Run this directly on your local system
"""
import asyncio
import sys
import os

# Add your app directory to path
sys.path.append('app')  # Adjust this path if needed

async def quick_diagnosis_and_fix():
    """Quick diagnosis and fix for local system"""
    print("🔍 Local Vector Dimension Diagnostic")
    print("=" * 40)
    
    try:
        # Import your modules
        from vector_store import async_client, COLLECTION_NAME, VECTOR_DIM
        from embeddings import embed_chunks_async
        
        print(f"📊 Expected dimension: {VECTOR_DIM}")
        print(f"📋 Collection name: {COLLECTION_NAME}")
        
        # 1. Test embedding generation
        print(f"\n1️⃣ Testing embedding generation...")
        test_embeddings = await embed_chunks_async(["test text for dimension check"])
        
        if test_embeddings and test_embeddings[0]:
            actual_embedding_dim = len(test_embeddings[0])
            print(f"   ✅ Generated embedding dimension: {actual_embedding_dim}")
            
            if actual_embedding_dim != VECTOR_DIM:
                print(f"   ❌ MISMATCH: Generated {actual_embedding_dim} ≠ Expected {VECTOR_DIM}")
                print(f"   🔧 Need to update VECTOR_DIM to {actual_embedding_dim}")
                return False
        else:
            print(f"   ❌ Failed to generate test embedding")
            return False
        
        # 2. Check Qdrant collection
        print(f"\n2️⃣ Checking Qdrant collection...")
        client = await async_client.get_client()
        
        try:
            collection_info = client.get_collection(COLLECTION_NAME)
            collection_dim = collection_info.config.params.vectors.size
            points_count = collection_info.points_count
            
            print(f"   📐 Collection dimension: {collection_dim}")
            print(f"   🔢 Points in collection: {points_count}")
            
            if collection_dim != actual_embedding_dim:
                print(f"   ❌ DIMENSION MISMATCH: Collection {collection_dim} ≠ Embeddings {actual_embedding_dim}")
                
                # Offer to fix
                print(f"\n🔧 FIXING DIMENSION MISMATCH...")
                
                # Delete collection
                print(f"   🗑️ Deleting collection...")
                client.delete_collection(COLLECTION_NAME)
                
                # Recreate with correct dimension
                print(f"   🆕 Creating collection with dimension {actual_embedding_dim}...")
                from qdrant_client.models import VectorParams, Distance
                vector_config = VectorParams(size=actual_embedding_dim, distance=Distance.COSINE)
                client.create_collection(COLLECTION_NAME, vector_config)
                
                # Verify
                new_info = client.get_collection(COLLECTION_NAME)
                new_dim = new_info.config.params.vectors.size
                print(f"   ✅ Collection recreated with dimension: {new_dim}")
                
                print(f"\n🎉 FIXED! Now reprocess your document.")
                return True
                
            else:
                print(f"   ✅ Dimensions match perfectly")
                print(f"   🤔 Search issue might be something else...")
                
                # Check if there are actually points in the collection
                if points_count == 0:
                    print(f"   ⚠️ Collection is empty - no documents processed yet")
                else:
                    print(f"   🔍 Collection has {points_count} points but search returns 0")
                    print(f"   💡 This might be a search filter or document ID issue")
                
                return True
                
        except Exception as e:
            print(f"   ❌ Collection error: {e}")
            print(f"   🔧 Creating new collection...")
            
            from qdrant_client.models import VectorParams, Distance
            vector_config = VectorParams(size=actual_embedding_dim, distance=Distance.COSINE)
            client.create_collection(COLLECTION_NAME, vector_config)
            print(f"   ✅ Collection created with dimension {actual_embedding_dim}")
            return True
            
    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def check_document_in_qdrant():
    """Check if your specific document exists in Qdrant"""
    print(f"\n3️⃣ Checking for your document in Qdrant...")
    
    try:
        from vector_store import async_client, COLLECTION_NAME
        
        client = await async_client.get_client()
        
        # Get all points to see what's in there
        scroll_result = client.scroll(
            collection_name=COLLECTION_NAME, 
            limit=10, 
            with_payload=True
        )
        
        points = scroll_result[0]
        
        if points:
            print(f"   📋 Found {len(points)} points in collection:")
            for i, point in enumerate(points[:5]):  # Show first 5
                doc_id = point.payload.get('document_id', 'N/A')
                filename = point.payload.get('file_name', 'N/A')
                print(f"      {i+1}. Doc ID: {doc_id[:12]}... | File: {filename}")
            
            # Check for your specific document
            policy_points = [p for p in points if 'policy.pdf' in p.payload.get('file_name', '')]
            if policy_points:
                print(f"   ✅ Found {len(policy_points)} points for policy.pdf")
                doc_id = policy_points[0].payload.get('document_id')
                print(f"   📋 Document ID: {doc_id}")
                return doc_id
            else:
                print(f"   ❌ No points found for policy.pdf")
                return None
        else:
            print(f"   📭 Collection is empty")
            return None
            
    except Exception as e:
        print(f"   ❌ Error checking documents: {e}")
        return None

if __name__ == "__main__":
    async def main():
        success = await quick_diagnosis_and_fix()
        
        if success:
            doc_id = await check_document_in_qdrant()
            
            if doc_id:
                print(f"\n✅ SUMMARY:")
                print(f"   - Qdrant collection is properly configured")
                print(f"   - Your document exists with ID: {doc_id[:12]}...")
                print(f"   - Try your queries again!")
            else:
                print(f"\n⚠️ SUMMARY:")
                print(f"   - Qdrant collection is fixed")
                print(f"   - But no document found - reprocess your PDF")
        else:
            print(f"\n❌ FAILED - Manual intervention needed")
    
    asyncio.run(main())