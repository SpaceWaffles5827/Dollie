import ollama
import sys

def extract_message(response):
    # Ollama v0.x returns {"choices":[{"message":{...}}]}
    if "choices" in response:
        return response["choices"][0]["message"]["content"]
    # Ollama v1.x might return {"message": {"content": ...}}
    if "message" in response:
        return response["message"].get("content", "")
    # fallback: maybe it's top‑level "content"
    return response.get("content", "")

def main():
    history = [
        {
            "role": "system",
            "content": "You are a helpful assistant that can describe images and answer follow‑up questions."
        },
        {
            "role": "user",
            "content": "Describe this image?",
            "images": ["./screenshots/tweet.png"]
        }
    ]

    # First request: describe the image
    response = ollama.chat(model="gemma3:4b", messages=history)

    # print raw response once so you know its structure
    print("RAW RESPONSE:", response, file=sys.stderr)

    assistant_text = extract_message(response)
    print("\nAssistant:", assistant_text)

    history.append({"role": "assistant", "content": assistant_text})

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        history.append({"role": "user", "content": user_input})
        response = ollama.chat(model="gemma3:4b", messages=history)
        assistant_text = extract_message(response)
        print("\nAssistant:", assistant_text)
        history.append({"role": "assistant", "content": assistant_text})

if __name__ == "__main__":
    main()
