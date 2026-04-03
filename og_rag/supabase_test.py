import os
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY")

print(f"URL: {url}")
print(f"KEY: {key[:20]}..." if key else "KEY: NOT FOUND")

if not url or not key:
    print("❌ Missing env vars — check your .env file")
    exit()

try:
    client = create_client(url, key)
    
    # Test 1: basic connection
    result = client.table("disease_knowledge").select("*").limit(5).execute()
    print(f"\n✅ Connected! Rows returned: {len(result.data)}")
    
    if result.data:
        print("\nSample row:")
        for k, v in result.data[0].items():
            print(f"  {k}: {str(v)[:80]}")
    else:
        print("⚠️  Table is EMPTY — no disease knowledge loaded")

    # Test 2: count total rows
    count = client.table("disease_knowledge").select("*", count="exact").execute()
    print(f"\nTotal rows in disease_knowledge: {count.count}")

except Exception as e:
    print(f"\n❌ Connection failed: {e}")