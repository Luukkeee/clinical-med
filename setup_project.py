# Copy .env.example to .env if it doesn't exist
import os
import shutil

project_root = os.path.dirname(os.path.abspath(__file__))
env_example = os.path.join(project_root, ".env.example")
env_file = os.path.join(project_root, ".env")

if not os.path.exists(env_file):
    shutil.copy(env_example, env_file)
    print(f"Created .env from .env.example")
    print(f"Edit .env to set your OPENAI_API_KEY for full mode.")
else:
    print(f".env already exists.")

# Create data directory
data_dir = os.path.join(project_root, "data")
os.makedirs(data_dir, exist_ok=True)
print(f"Data directory ready: {data_dir}")

print("\nSetup complete! Next steps:")
print("1. Install Python deps:  pip install -r requirements.txt")
print("2. Build FAISS index:    python run.py --build-index")
print("3. Start backend:        python run.py")
print("4. Install frontend:     cd frontend && npm install")
print("5. Start frontend:       cd frontend && npm run dev")
print("\nOptional: Set OPENAI_API_KEY in .env for full LLM mode.")
print("Without it, the system runs in demo mode with template responses.")
