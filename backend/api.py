import os
import re
import numpy as np
import torch
import clip
import faiss
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import subprocess

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config ───────────────────────────────────────────────────────────────────
FRAMES_FOLDER   = "frames"
CLIPS_FOLDER    = "clips"
FRAME_INTERVAL  = 30        # every Nth video frame was saved (matches extract_frames.py)
FPS             = 30        # source video FPS
OUTPUT_FPS      = 8         # FPS for the output timelapse MP4
GAP_THRESHOLD   = 5         # max frame-index gap to still consider "same group"

os.makedirs(CLIPS_FOLDER, exist_ok=True)

# ── Load CLIP model ───────────────────────────────────────────────────────────
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

# ── Load embeddings & build FAISS index ──────────────────────────────────────
embeddings  = np.load("frame_embeddings.npy")
frame_names = np.load("frame_names.npy", allow_pickle=True)

dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings.astype("float32"))

print(f"FAISS index ready — {index.ntotal} frames indexed")


# ── Helpers ───────────────────────────────────────────────────────────────────

def frame_name_to_index(name: str) -> int:
    m = re.search(r"frame_(\d+)", str(name))
    if not m:
        raise ValueError(f"Cannot parse frame index from '{name}'")
    return int(m.group(1))


def group_consecutive(frame_indices: list, gap: int = GAP_THRESHOLD) -> list:
    """Group frame indices that are within `gap` of each other into sublists."""
    if not frame_indices:
        return []
    sorted_idx = sorted(frame_indices)
    groups, current = [], [sorted_idx[0]]
    for idx in sorted_idx[1:]:
        if idx - current[-1] <= gap:
            current.append(idx)
        else:
            groups.append(current)
            current = [idx]
    groups.append(current)
    return groups


def stitch_frames_to_mp4(frame_indices: list, output_path: str) -> str:
    """
    Given a list of saved-frame indices, collect the JPG files in order
    and stitch them into an MP4 timelapse using ffmpeg concat demuxer.
    """
    list_path = output_path.replace(".mp4", "_list.txt")
    duration_per_frame = 1.0 / OUTPUT_FPS  # seconds each frame is shown

    with open(list_path, "w") as f:
        for idx in sorted(frame_indices):
            jpg = os.path.join(FRAMES_FOLDER, f"frame_{idx}.jpg")
            if os.path.exists(jpg):
                f.write(f"file '{os.path.abspath(jpg)}'\n")
                f.write(f"duration {duration_per_frame}\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_path,
        "-vf", "scale=640:-2",        # normalise width, keep aspect ratio
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",        # browser-compatible pixel format
        "-movflags", "+faststart",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    os.remove(list_path)

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")

    return output_path


# ── Routes ────────────────────────────────────────────────────────────────────

app.mount("/frames", StaticFiles(directory=FRAMES_FOLDER), name="frames")
app.mount("/clips",  StaticFiles(directory=CLIPS_FOLDER),  name="clips")


@app.get("/search")
def search(query: str = Query(...), top_k: int = 20, threshold: float = 35.0):
    """
    1. Embed the query with CLIP.
    2. Find top_k nearest frames.
    3. Filter by L2 distance threshold.
    4. Group consecutive matching frames.
    5. Stitch each group into a timelapse MP4 (frames → mp4, no source video needed).
    6. Return clip URLs + metadata.
    """
    # --- 1. Embed query ---
    text_tokens = clip.tokenize([query]).to(device)
    with torch.no_grad():
        text_features = model.encode_text(text_tokens)
    text_features = text_features.cpu().numpy().astype("float32")

    # --- 2. Search FAISS ---
    distances, indices = index.search(text_features, top_k)

    # --- 3. Filter by threshold ---
    matched = []
    for dist, idx in zip(distances[0], indices[0]):
        if dist <= threshold:
            matched.append((int(idx), float(dist)))

    if not matched:
        return {"results": [], "query": query, "message": "No matches above threshold. Try raising threshold or a different query."}

    # --- 4. Group consecutive frame indices ---
    frame_idx_list = [frame_name_to_index(frame_names[i]) for i, _ in matched]
    dist_map       = {frame_name_to_index(frame_names[i]): d for i, d in matched}
    groups         = group_consecutive(frame_idx_list)

    # --- 5. Stitch each group → MP4 ---
    results = []
    for g_num, group in enumerate(groups):
        cache_name  = f"clip_{abs(hash(query))}_{group[0]}_{group[-1]}.mp4"
        output_path = os.path.join(CLIPS_FOLDER, cache_name)

        if not os.path.exists(output_path):
            try:
                stitch_frames_to_mp4(group, output_path)
            except RuntimeError as e:
                print(f"Skipping group {g_num}: {e}")
                continue

        start_sec = round(group[0]  * FRAME_INTERVAL / FPS, 2)
        end_sec   = round(group[-1] * FRAME_INTERVAL / FPS, 2)
        avg_dist  = sum(dist_map.get(fi, 99) for fi in group) / len(group)
        score     = max(0, round(100 - avg_dist * 3))

        results.append({
            "clip_url":    f"/clips/{cache_name}",
            "thumb_url":   f"/frames/frame_{group[len(group)//2]}.jpg",
            "start_time":  start_sec,
            "end_time":    end_sec,
            "frame_count": len(group),
            "score":       score,
            "group":       g_num + 1,
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    return {"results": results, "query": query}