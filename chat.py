import os
from llama_cpp import Llama, llama_cpp

# Optional: show error only
os.environ["LLAMA_CPP_LOG_LEVEL"] = "ERROR"

# Check GPU support
if not llama_cpp.llama_supports_gpu_offload():
    print("🚫 GPU acceleration is NOT enabled. Reinstall with:\n")
    print("  CMAKE_ARGS=\"-DLLAMA_CUBLAS=on\" pip install llama-cpp-python --force-reinstall --no-binary llama-cpp-python")
    exit(1)

# Initialize LLaMA with GPU offload
llm = Llama(
    model_path="./models/deepseek-llm-7b-chat.Q6_K.gguf",
    n_gpu_layers=35,   # Use GPU for first 35 layers
    n_ctx=8192,        # Context size
    verbose=False,     # Suppress verbose output
)

chat_history = ""

print("🦙 DeepSeek Chatbot (type 'exit' to quit)\n")

while True:
    user_input = input("You: ")
    if user_input.lower() in {"exit", "quit"}:
        print("Bot: Goodbye!")
        break

    # Append to history with prompt template
    chat_history += f"### Human: {user_input}\n### Assistant:"

    # Generate response
    output = llm(chat_history, max_tokens=150, stop=["### Human:"])
    response = output["choices"][0]["text"].strip()

    print("Bot:", response)

    # Append response to history
    chat_history += f" {response}\n"
