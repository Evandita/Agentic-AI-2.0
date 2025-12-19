"""
Example CTF challenges for testing the Red Teaming AI system
"""

EXAMPLE_CHALLENGES = {
    "base64_flag": {
        "name": "Simple Base64 Flag",
        "description": "Decode this base64 string to find the flag",
        "challenge": "RkxBR3tiYXNlNjRfaXNfZWFzeX0=",
        "hint": "Use base64_decode tool",
        "solution": "FLAG{base64_is_easy}"
    },
    
    "nested_encoding": {
        "name": "Nested Encoding",
        "description": "The flag is encoded multiple times",
        "challenge": "VTBaQlIxdGlZWE5sTmpSZmJtVnpkR1ZrWDJWdVkyOWthVzVuZlE9PQ==",
        "hint": "Decode multiple times",
        "solution": "FLAG{base64_nested_encoding}"
    },
    
    "web_challenge": {
        "name": "Web Source Flag",
        "description": "Find the flag hidden in a webpage",
        "url": "Create a simple HTML file with flag in comment",
        "hint": "Check HTML comments",
        "solution": "FLAG{hidden_in_html}"
    },
    
    "header_flag": {
        "name": "HTTP Header Flag",
        "description": "The flag is in an HTTP header",
        "url": "Server responds with X-Flag header",
        "hint": "Check response headers",
        "solution": "FLAG{check_the_headers}"
    }
}


def print_challenges():
    """Print all example challenges"""
    print("\n🎯 Example CTF Challenges for Testing\n")
    print("=" * 60)
    
    for key, challenge in EXAMPLE_CHALLENGES.items():
        print(f"\n📌 {challenge['name']}")
        print(f"   Description: {challenge['description']}")
        if 'challenge' in challenge:
            print(f"   Challenge: {challenge['challenge']}")
        if 'url' in challenge:
            print(f"   URL: {challenge['url']}")
        print(f"   Hint: {challenge['hint']}")
        print(f"   Solution: {challenge['solution']}")
    
    print("\n" + "=" * 60)
    print("\n💡 How to use:")
    print("1. Start the Red Teaming AI: python main.py")
    print("2. Select agent: /agent gemini (or /agent ollama)")
    print("3. Select mode: /mode web-ctf")
    print("4. Give the challenge to the AI:")
    print("   Example: 'Decode this base64: RkxBR3tiYXNlNjRfaXNfZWFzeX0='")
    print("\n")


if __name__ == "__main__":
    print_challenges()
