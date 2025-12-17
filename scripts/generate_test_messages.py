import json
from pathlib import Path

TEST_MESSAGES = [
    {
        "content": "Fixed the authentication bug in the login service. Users were getting 401 errors due to expired JWT tokens not being refreshed properly.",
        "author": "Sarah Chen",
        "channel": "engineering"
    },
    {
        "content": "Security audit revealed we're not sanitizing user input in the search endpoint. Could lead to SQL injection. Opening ticket.",
        "author": "Mike Rodriguez",
        "channel": "security"
    },
    {
        "content": "Implemented OAuth2 flow for third-party integrations. Documentation is in Confluence under API Auth.",
        "author": "Sarah Chen",
        "channel": "backend"
    },
    {
        "content": "Password reset emails are being marked as spam. Switching to SendGrid with proper DKIM/SPF configuration.",
        "author": "Alex Kim",
        "channel": "ops"
    },
    {
        "content": "Added rate limiting to login endpoint (5 attempts per minute) to prevent brute force attacks.",
        "author": "Sarah Chen",
        "channel": "security"
    },
    {
        "content": "Database migration to add user_preferences table completed. Rolling out to production tonight at 2am.",
        "author": "Mike Rodriguez",
        "channel": "backend"
    },
    {
        "content": "PostgreSQL connection pool exhausted during peak traffic. Increased max_connections from 100 to 200.",
        "author": "Alex Kim",
        "channel": "ops"
    },
    {
        "content": "Optimized the search query - added index on created_at column. Query time dropped from 2s to 50ms.",
        "author": "Mike Rodriguez",
        "channel": "backend"
    },
    {
        "content": "Should we use PostgreSQL or MongoDB for the new analytics feature? Postgres has better JOIN support but Mongo is more flexible.",
        "author": "Jordan Lee",
        "channel": "architecture"
    },
    {
        "content": "API response times spiking. Turns out we're making N+1 queries. Added eager loading, problem solved.",
        "author": "Mike Rodriguez",
        "channel": "backend"
    },
    {
        "content": "Button on the checkout page not working on mobile Safari. CSS issue with touch events. Fix deployed.",
        "author": "Emma Wilson",
        "channel": "frontend"
    },
    {
        "content": "Redesigned the dashboard - moved from grid layout to flexbox. Much cleaner on different screen sizes.",
        "author": "Jordan Lee",
        "channel": "design"
    },
    {
        "content": "Dark mode implementation complete! Toggle is in user settings. Default respects system preference.",
        "author": "Emma Wilson",
        "channel": "frontend"
    },
    {
        "content": "React component re-rendering too often. Added useMemo and useCallback, performance improved significantly.",
        "author": "Emma Wilson",
        "channel": "frontend"
    },
    {
        "content": "Users reporting the modal dialog doesn't close on mobile. Z-index issue with overlay. Investigating.",
        "author": "Jordan Lee",
        "channel": "frontend"
    },
    {
        "content": "Deployed new API version to production. Load balancer health checks passing. Monitoring for errors.",
        "author": "Alex Kim",
        "channel": "ops"
    },
    {
        "content": "CI pipeline failing intermittently due to Docker registry timeouts. Switched to artifact caching.",
        "author": "Alex Kim",
        "channel": "devops"
    },
    {
        "content": "Kubernetes cluster upgraded to v1.28. Rolling update completed with zero downtime.",
        "author": "Chris Taylor",
        "channel": "ops"
    },
    {
        "content": "Added automated backups for production database. Daily snapshots retained for 30 days.",
        "author": "Chris Taylor",
        "channel": "ops"
    },
    {
        "content": "Server costs increased 40% this month. Rightsizing EC2 instances and enabling auto-scaling.",
        "author": "Alex Kim",
        "channel": "ops"
    }
]

def generate_test_messages():
    tests_dir = Path(__file__).parent.parent / "tests"
    tests_dir.mkdir(exist_ok=True)
    
    output_file = tests_dir / "test_messages.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(TEST_MESSAGES, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Generated {len(TEST_MESSAGES)} test messages")
    print(f"✓ Saved to: {output_file}")
    print()
    print("Topic distribution:")
    print("  - Authentication/Security: 5 messages")
    print("  - Database/Backend: 5 messages")
    print("  - Frontend/UI: 5 messages")
    print("  - DevOps/Infrastructure: 5 messages")

if __name__ == "__main__":
    generate_test_messages()