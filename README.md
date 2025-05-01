# Chatbot
VectorChat AI is an intelligent chatbot platform that enables users to upload PDF documents—secured or unprotected—and interact with them conversationally. It uses FastAPI for backend processing, Pinecone for storing and retrieving vectorized text data, and LangChain with OpenAI for generating context-aware responses. Uploaded PDFs are parsed using PyMuPDF, hashed to detect duplicates, chunked, embedded, and stored with metadata. The chatbot only answers based on content from the uploaded file, ensuring accuracy and relevance in every response.

Create a .env file to store open api key credentials.

The virtual environment is (pinenv)
# setup virtual environment 
  python -m venv pinenv
# activate virtual environment
  pinenv\Scripts\activate

# Project Structure
> Chatbot
  > static
    > bg.jpg
    > styles.css
  > templates
    > index.html
  > app.py
  > chatbotAPI.py

# Project Running
first run,
  uvicorn chatbotAPI:app --reload --port 8001    
then run,
  python app.py
