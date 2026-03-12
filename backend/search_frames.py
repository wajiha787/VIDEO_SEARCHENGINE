import numpy as np
import torch
import clip
import faiss
from PIL import Image
import os

# Load CLIP model
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

# Load embeddings
embeddings = np.load("frame_embeddings.npy")
frame_names = np.load("frame_names.npy")

# Build FAISS index
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)  # L2 distance
index.add(embeddings)

print("FAISS index built with", index.ntotal, "frames")

# --- Function to search ---
def search(query, top_k=5):
    # Convert text to embedding
    text_tokens = clip.tokenize([query]).to(device)
    with torch.no_grad():
        text_features = model.encode_text(text_tokens)
    text_features = text_features.cpu().numpy()
    
    # Search in FAISS
    distances, indices = index.search(text_features, top_k)
    
    results = []
    for i, idx in enumerate(indices[0]):
        results.append({
            "frame": frame_names[idx],
            "distance": float(distances[0][i])
        })
    
    return results

# --- Test search ---
query = "people running"
results = search(query, top_k=5)

print("Top results for query:", query)
for r in results:
    print(r)