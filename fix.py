#!/usr/bin/env python3
"""
Simple manual fix for Qdrant collection issues
Bypasses the client compatibility issues
"""
import requests
import json

def manual_qdrant_fix():
    """Manual fix using HTTP API directly"""
    print("🔧 Manual Qdrant Fix")
    print("=" * 30)
    
    # Qdrant HTTP API endpoints
    base_url = "http://localhost:6333"
    collection_name = "document_chunks"
    
    try:
        # 1. Check current collection
        print("1️⃣ Checking current collection...")
        response = requests.get(f"{base_url}/collections/{collection_name}")
        
        if response.status_code == 200:
            collection_info = response.json()
            current_dim = collection_info["result"]["config"]["params"]["vectors"]["size"]
            points_count = collection_info["result"]["points_count"]
            
            print(f"   📐 Current dimension: {current_dim}")
            print(f"   🔢 Points count: {points_count}")
            print(f"   🎯 Expected dimension: 768")
            
            if current_dim != 768:
                print(f"   ❌ DIMENSION MISMATCH!")
                
                # 2. Delete collection
                print("2️⃣ Deleting collection...")
                delete_response = requests.delete(f"{base_url}/collections/{collection_name}")
                
                if delete_response.status_code == 200:
                    print("   ✅ Collection deleted")
                else:
                    print(f"   ❌ Delete failed: {delete_response.text}")
                    return False
                
                # 3. Create new collection
                print("3️⃣ Creating new collection with 768 dimensions...")
                create_payload = {
                    "vectors": {
                        "size": 768,
                        "distance": "Cosine"
                    }
                }
                
                create_response = requests.put(
                    f"{base_url}/collections/{collection_name}",
                    json=create_payload
                )
                
                if create_response.status_code == 200:
                    print("   ✅ Collection created successfully")
                    
                    # Verify
                    verify_response = requests.get(f"{base_url}/collections/{collection_name}")
                    if verify_response.status_code == 200:
                        new_info = verify_response.json()
                        new_dim = new_info["result"]["config"]["params"]["vectors"]["size"]
                        print(f"   ✅ Verified dimension: {new_dim}")
                        return True
                    else:
                        print("   ⚠️ Could not verify new collection")
                        return False
                else:
                    print(f"   ❌ Create failed: {create_response.text}")
                    return False
            else:
                print("   ✅ Dimensions already correct!")
                
                if points_count == 0:
                    print("   ⚠️ Collection is empty - reprocess your document")
                else:
                    print("   🔍 Collection has data but search fails - checking points...")
                    
                    # Check what's actually in the collection
                    scroll_response = requests.post(
                        f"{base_url}/collections/{collection_name}/points/scroll",
                        json={"limit": 5, "with_payload": True}
                    )
                    
                    if scroll_response.status_code == 200:
                        scroll_data = scroll_response.json()
                        points = scroll_data["result"]["points"]
                        
                        print(f"   📋 Sample points:")
                        for i, point in enumerate(points[:3]):
                            doc_id = point["payload"].get("document_id", "N/A")
                            filename = point["payload"].get("file_name", "N/A")
                            print(f"      {i+1}. Doc: {doc_id[:12]}... | File: {filename}")
                
                return True
                
        elif response.status_code == 404:
            print("   📭 Collection doesn't exist - creating new one...")
            
            # Create collection
            create_payload = {
                "vectors": {
                    "size": 768,
                    "distance": "Cosine"
                }
            }
            
            create_response = requests.put(
                f"{base_url}/collections/{collection_name}",
                json=create_payload
            )
            
            if create_response.status_code == 200:
                print("   ✅ New collection created with 768 dimensions")
                return True
            else:
                print(f"   ❌ Failed to create collection: {create_response.text}")
                return False
        else:
            print(f"   ❌ Error checking collection: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Qdrant at http://localhost:6333")
        print("   Make sure Qdrant is running locally")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_embedding_search():
    """Test if search works after fix"""
    print("\n4️⃣ Testing search functionality...")
    
    try:
        import sys
        sys.path.append('app')
        
        import asyncio
        from embeddings import embed_chunks_async
        
        async def test_search():
            # Generate a test embedding
            embeddings = await embed_chunks_async(["test search query"])
            
            if embeddings and embeddings[0]:
                test_vector = embeddings[0]
                print(f"   📐 Test vector dimension: {len(test_vector)}")
                
                # Try search via HTTP API
                search_payload = {
                    "vector": test_vector,
                    "limit": 3,
                    "with_payload": True
                }
                
                response = requests.post(
                    "http://localhost:6333/collections/document_chunks/points/search",
                    json=search_payload
                )
                
                if response.status_code == 200:
                    results = response.json()["result"]
                    print(f"   ✅ Search successful - found {len(results)} results")
                    
                    if len(results) == 0:
                        print("   ⚠️ No results found - collection might be empty")
                        print("   💡 Reprocess your document to populate collection")
                    else:
                        print("   🎉 Search is working!")
                        
                    return True
                else:
                    print(f"   ❌ Search failed: {response.status_code} - {response.text}")
                    return False
            else:
                print("   ❌ Could not generate test embedding")
                return False
        
        return asyncio.run(test_search())
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting manual Qdrant fix...")
    
    success = manual_qdrant_fix()
    
    if success:
        print("\n✅ Collection fix completed!")
        
        # Test search
        if test_embedding_search():
            print("\n🎉 EVERYTHING WORKING!")
            print("   Now try your API queries again")
        else:
            print("\n⚠️ Collection fixed but search test failed")
            print("   Try reprocessing your document")
    else:
        print("\n❌ Fix failed - manual intervention needed")
        print("\n🔧 Manual steps:")
        print("1. Go to http://localhost:6333/dashboard")
        print("2. Delete the 'document_chunks' collection")
        print("3. Restart your application")
        print("4. Reprocess your document")