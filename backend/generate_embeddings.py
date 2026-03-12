import os
import torch
import clip
import numpy as np
from PIL import Image

frames_folder = "frames"

# load model
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

embeddings = []
frame_names = []

for file in os.listdir(frames_folder):
    
    if file.endswith(".jpg"):
        
        path = os.path.join(frames_folder, file)
        
        image = preprocess(Image.open(path)).unsqueeze(0).to(device)

        with torch.no_grad():
            image_features = model.encode_image(image)

        embeddings.append(image_features.cpu().numpy())
        frame_names.append(file)

# convert to numpy array
embeddings = np.vstack(embeddings)

# save embeddings
np.save("frame_embeddings.npy", embeddings)
np.save("frame_names.npy", frame_names)

print("Embeddings generated for", len(frame_names), "frames")