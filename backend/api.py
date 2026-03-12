import numpy as np
import torch
import clip
import faiss
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI
app = FastAPI()

# Enable CORS
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frames folder
app.mount("/frames", StaticFiles(directory="frames"), name="frames")

# Load CLIP model
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

# Load embeddings
embeddings = np.load("frame_embeddings.npy")
frame_names = np.load("frame_names.npy")

# Build FAISS index
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

# Search endpoint
@app.get("/search")
def search_frames(query: str = Query(..., description="Text query to search frames"), top_k: int = 5):
    # Convert text to embedding
    text_tokens = clip.tokenize([query]).to(device)
    with torch.no_grad():
        text_features = model.encode_text(text_tokens)
    text_features = text_features.cpu().numpy()
    
    # Search FAISS
    distances, indices = index.search(text_features, top_k)
    
    results = []
    for i, idx in enumerate(indices[0]):
        results.append({
            "frame": frame_names[idx],
            "distance": float(distances[0][i])
        })
    
    return {"query": query, "results": results}