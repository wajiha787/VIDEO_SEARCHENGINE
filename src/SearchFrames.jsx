import React, { useState, useRef } from "react";
import axios from "axios";

const API = "http://127.0.0.1:8000";

function fmtTime(sec) {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

function ClipCard({ result }) {
  const videoRef = useRef(null);
  const [playing, setPlaying] = useState(false);

  const toggle = () => {
    if (!videoRef.current) return;
    if (playing) {
      videoRef.current.pause();
      setPlaying(false);
    } else {
      videoRef.current.play();
      setPlaying(true);
    }
  };

  const scoreColor =
    result.score >= 70 ? "#4ade80" : result.score >= 45 ? "#facc15" : "#94a3b8";

  return (
    <div
      style={{
        width: 300,
        background: "#0f172a",
        border: "1px solid #1e293b",
        borderRadius: 8,
        overflow: "hidden",
        boxShadow: playing ? "0 0 0 2px #4ade80" : "none",
        transition: "box-shadow 0.2s",
      }}
    >
      {/* Video */}
      <div
        style={{ position: "relative", background: "#000", aspectRatio: "16/9", cursor: "pointer" }}
        onClick={toggle}
      >
        <video
          ref={videoRef}
          src={`${API}${result.clip_url}`}
          poster={`${API}${result.thumb_url}`}
          loop
          muted
          playsInline
          style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
          onEnded={() => setPlaying(false)}
        />
        {/* Play / Pause overlay */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: playing ? "transparent" : "rgba(0,0,0,0.45)",
            transition: "background 0.2s",
          }}
        >
          {!playing && (
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
              <circle cx="24" cy="24" r="24" fill="rgba(255,255,255,0.15)" />
              <polygon points="19,14 38,24 19,34" fill="white" />
            </svg>
          )}
        </div>
      </div>

      {/* Info */}
      <div style={{ padding: "10px 14px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ color: "#94a3b8", fontSize: 12 }}>
            {fmtTime(result.start_time)} → {fmtTime(result.end_time)}
          </div>
          <div style={{ color: "#475569", fontSize: 11, marginTop: 2 }}>
            {result.frame_count} frames · Segment {result.group}
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ color: scoreColor, fontWeight: 700, fontSize: 16 }}>
            {result.score}%
          </div>
          <div style={{ color: "#334155", fontSize: 10 }}>match</div>
        </div>
      </div>
    </div>
  );
}

export default function SearchFrames() {
  const [query, setQuery]       = useState("");
  const [results, setResults]   = useState([]);
  const [loading, setLoading]   = useState(false);
  const [message, setMessage]   = useState("");
  const [lastQuery, setLastQuery] = useState("");

  const handleSearch = async () => {
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setResults([]);
    setMessage("");

    try {
      const res = await axios.get(`${API}/search`, {
        params: { query: q, top_k: 20, threshold: 35 },
      });
      setResults(res.data.results || []);
      setLastQuery(res.data.query);
      if (res.data.message) setMessage(res.data.message);
    } catch (err) {
      setMessage("Search failed — is the backend running on port 8000?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "#020817", color: "#e2e8f0", fontFamily: "system-ui, sans-serif", padding: "2rem 2.5rem" }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4, color: "#f8fafc" }}>
        🎬 Video Timelapse Search
      </h1>
      <p style={{ color: "#475569", fontSize: 13, marginBottom: 28 }}>
        Search by description — matching frames are stitched into MP4 clips
      </p>

      {/* Search bar */}
      <div style={{ display: "flex", gap: 10, marginBottom: 32 }}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder='e.g. "person in red shirt running"'
          style={{
            flex: 1, maxWidth: 480, padding: "10px 14px",
            background: "#0f172a", border: "1px solid #1e293b",
            borderRadius: 6, color: "#f1f5f9", fontSize: 14, outline: "none",
          }}
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          style={{
            padding: "10px 22px", background: loading ? "#1e293b" : "#3b82f6",
            color: "#fff", border: "none", borderRadius: 6,
            fontWeight: 600, fontSize: 14, cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "Building clips…" : "Search"}
        </button>
      </div>

      {/* Status */}
      {message && <p style={{ color: "#f59e0b", fontSize: 13, marginBottom: 20 }}>⚠ {message}</p>}

      {/* Results */}
      {results.length > 0 && (
        <>
          <p style={{ color: "#64748b", fontSize: 13, marginBottom: 16 }}>
            {results.length} timelapse clip{results.length !== 1 ? "s" : ""} for{" "}
            <strong style={{ color: "#94a3b8" }}>"{lastQuery}"</strong> — click to play
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 16 }}>
            {results.map((r, i) => <ClipCard key={i} result={r} />)}
          </div>
        </>
      )}
    </div>
  );
}