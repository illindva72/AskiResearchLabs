import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    print("🚀 Starting AskiResearchLabs Locally...")
    print("👉 Access the app at: http://127.0.0.1:8000")
    
    # Run the application using the app instance from main.py
    # We force the local 8000 port and 127.0.0.1 host
    uvicorn.run(
        "main:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=True
    )
