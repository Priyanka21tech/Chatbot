# #1- Load API keys from .env file
# #2- Retrieve API keys using os.getenv()
# #3- fast api initialization
# #4- Initialize Pinecone and making index name
# #5 Connect to the index
# #6- making functions- to store/upload text
# extract text
# #7- make embeddings of text
# make hash of the file


from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel #for validating incoming data structure
import fitz  # PyMuPDF for PDF text extraction
from langchain_openai import OpenAIEmbeddings
import os
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec  # type:ignore
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import hashlib #for hashing to detect duplicate files

# 1. Load API keys from .env file
load_dotenv()

# 2. Retrieve API keys
pinecone_api_key = os.getenv("PINECONE_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

if not pinecone_api_key:
    raise ValueError("Missing Pinecone API key!")
if not openai_api_key:
    raise ValueError("Missing OpenAI API key!")

print("API Keys loaded successfully!")

# 3. FastAPI initialization
app = FastAPI()

# 4. Initialize Pinecone
pc = Pinecone(api_key=pinecone_api_key)
index_name = "Chatbot"

# 5. Connect to the index
index = pc.Index(index_name)

# 6. Making a directory for the uploaded PDFs
UPLOAD_FOLDER = "uploads" #local folder
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Hashes of prev uploaded files stored in the set- to gain uniqueness
file_hashes = set()

# 7. Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    text = ""  # stores extracted data
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text("text") + "\n"
    except Exception as e:
        print(e)
    return text

# 8. Function to generate embeddings of the text
def get_embedding(text):
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    return embeddings.embed_query(text)

# Function to calculate file hash (used for checking duplicates)
def calculate_file_hash(file_bytes):
    return hashlib.md5(file_bytes).hexdigest()

# Endpoint to upload PDF and store in Pinecone
@app.post("/upload/")
async def upload_pdf(file: UploadFile = File(...)):
    # UploadFile is oject of FastAPI- file class
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    file_bytes = await file.read()
    file_hash = calculate_file_hash(file_bytes)

# checks if hash already in the set
    if file_hash in file_hashes:
        print("Duplicate files")
        return {"message": "File already uploaded. Skipping duplicate."}
        
    # Save file locally under uploads
    pdf_path = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(pdf_path, "wb") as f:
        f.write(file_bytes)

    # Extract and chunk text
    text = extract_text_from_pdf(pdf_path)
    chunks = [text[i:i+500] for i in range(0, len(text), 500)]

    # Embed and upload each chunk with metadata
    for i, chunk in enumerate(chunks):
        vector = get_embedding(chunk)
        metadata = {"text": chunk, "filename": file.filename}  # metadata contains filename
        index.upsert([(f"{file.filename}_{i}", vector, metadata)])

    # Add file hash to track uploaded files
    # this is a set- add hashes to it
    file_hashes.add(file_hash)

    return {"message": "You can now start chatting with the BOT"}

# Pydantic model for chat request
class QueryRequest(BaseModel):
    query: str
    query_filename: str  # Receive the filename for filtering

# Initialize OpenAI Chat Model
llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=openai_api_key)

# Endpoint to handle chat query
@app.post("/chat/")
async def chat(request: QueryRequest):
    query_vector = get_embedding(request.query)

    # Query Pinecone with metadata filter to ensure only relevant results are returned
    results = index.query(
        vector=query_vector,
        top_k=5,
        include_metadata=True,
        filter={"filename": request.query_filename}  # Filter by the uploaded filename
    )

    # Check if any results were returned
    if not results or not results.matches:
        raise HTTPException(status_code=404, detail="No relevant information found.")

    # Combine the text of the matched Pinecone documents
    context = "\n".join([match.metadata["text"] for match in results.matches])

    # Use OpenAI GPT to generate a response based on the context
    messages = [
        SystemMessage(
    content="You are an AI assistant. Only answer using the information from the provided PDF content. "
            "If the answer is not in the context, reply with: 'Sorry, I couldn't find that in the uploaded document.'"
),

        HumanMessage(content=f"Context:\n{context}\n\nUser Query: {request.query}")
    ]

    llm_response = llm(messages)

    return {"response": llm_response.content}
