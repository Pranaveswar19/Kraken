import os
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv()

CHANNEL_ID = "C0A474TT6CU"


def test_slack():
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        print("❌ SLACK_BOT_TOKEN not in .env")
        return False
    
    client = WebClient(token=token)
    
    try:
        print("Test 1: Authentication...")
        auth = client.auth_test()
        print(f"✓ Connected to: {auth['team']}")
        print(f"  Bot user: {auth['user']}")
        print()
        
        print(f"Test 2: Fetching messages from channel {CHANNEL_ID}...")
        response = client.conversations_history(
            channel=CHANNEL_ID,
            limit=5
        )
        
        messages = response['messages']
        print(f"✓ Fetched {len(messages)} messages")
        print()
        
        print("Sample messages:")
        for i, msg in enumerate(messages[:3], 1):
            user_id = msg.get('user', 'system')
            text = msg.get('text', '')[:80]
            print(f"{i}. [{user_id}] {text}")
        
        print()
        print("✓ Phase 1 complete! Bot can read Slack messages.")
        return True
        
    except SlackApiError as e:
        error = e.response['error']
        print(f"❌ Slack API error: {error}")
        
        if error == 'invalid_auth':
            print("  → Token is invalid. Check SLACK_BOT_TOKEN in .env")
        elif error == 'not_in_channel':
            print(f"  → Bot not in channel. Run: /invite @YourBotName in channel")
        elif error == 'channel_not_found':
            print(f"  → Channel {CHANNEL_ID} doesn't exist")
        elif error == 'missing_scope':
            print(f"  → Missing permission: {e.response.get('needed', 'unknown')}")
            print("  → Add scope in app settings, then reinstall app")
        
        return False


if __name__ == "__main__":
    success = test_slack()
    exit(0 if success else 1)