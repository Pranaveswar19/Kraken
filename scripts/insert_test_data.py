import json
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client, Client

load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)


def load_test_messages():
    tests_dir = Path(__file__).parent.parent / "tests"
    messages_file = tests_dir / "test_messages.json"
    
    if not messages_file.exists():
        raise FileNotFoundError(f"Test messages file not found: {messages_file}")
    
    with open(messages_file, 'r', encoding='utf-8') as f:
        messages = json.load(f)
    
    print(f"✓ Loaded {len(messages)} test messages from {messages_file}")
    return messages


def generate_embeddings(messages):
    print(f"Generating embeddings for {len(messages)} messages...")
    
    texts = [msg["content"] for msg in messages]
    
    try:
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
    except Exception as e:
        print(f"✗ OpenAI API error: {e}")
        raise
    
    embeddings = [item.embedding for item in response.data]
    
    print(f"✓ Generated {len(embeddings)} embeddings")
    print(f"  Model: text-embedding-3-small")
    print(f"  Dimensions: {len(embeddings[0])}")
    print(f"  Cost: ~${response.usage.total_tokens * 0.00000002:.6f}")
    
    return embeddings


def insert_into_supabase(messages, embeddings):
    print(f"Inserting {len(messages)} messages into Supabase...")
    
    rows = []
    for msg, embedding in zip(messages, embeddings):
        rows.append({
            "content": msg["content"],
            "author": msg["author"],
            "channel": msg["channel"],
            "embedding": embedding,
            "metadata": {}
        })
    
    try:
        result = supabase.table("test_messages").insert(rows).execute()
        
        print(f"✓ Inserted {len(result.data)} messages")
        print(f"  Table: test_messages")
        print(f"  Columns: content, author, channel, embedding")
        
        return result.data
        
    except Exception as e:
        print(f"✗ Supabase insert error: {e}")
        raise


def verify_insertion():
    print("Verifying insertion...")
    
    result = supabase.table("test_messages").select("id", count="exact").execute()
    count = result.count
    
    print(f"✓ Verification passed")
    print(f"  Total rows in test_messages: {count}")
    
    sample = supabase.table("test_messages").select("content, author, embedding").limit(1).execute()
    if sample.data:
        row = sample.data[0]
        has_embedding = row.get("embedding") is not None
        embedding_size = len(row.get("embedding", [])) if has_embedding else 0
        
        print(f"  Sample row:")
        print(f"    Content: {row['content'][:50]}...")
        print(f"    Author: {row['author']}")
        print(f"    Embedding: {'✓' if has_embedding else '✗'} ({embedding_size} dimensions)")


def main():
    print("=" * 60)
    print("Insert Test Data into Supabase")
    print("=" * 60)
    print()
    
    messages = load_test_messages()
    print()
    
    embeddings = generate_embeddings(messages)
    print()
    
    insert_into_supabase(messages, embeddings)
    print()
    
    verify_insertion()
    print()
    
    print("=" * 60)
    print("✓ Setup complete!")
    print("=" * 60)
    print()
    print("Next: Run vector search tests")
    print("  python scripts/test_vector_search.py")


if __name__ == "__main__":
    main()