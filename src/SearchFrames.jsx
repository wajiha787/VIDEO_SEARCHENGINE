import React, { useState } from "react";
import axios from "axios";

function SearchFrames() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);

  const handleSearch = async () => {
    if (!query) return;

    try {
      const res = await axios.get("http://127.0.0.1:8000/search", {
        params: { query, top_k: 5 },
      });
      setResults(res.data.results);
    } catch (err) {
      console.error("Search error:", err);
    }
  };

  return (
    <div style={{ padding: "2rem" }}>
      <h1>Video Frame Search</h1>
      <input
        type="text"
        placeholder="Type your search..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        style={{ width: "300px", padding: "0.5rem", marginRight: "1rem" }}
      />
      <button onClick={handleSearch} style={{ padding: "0.5rem 1rem" }}>
        Search
      </button>

      <div style={{ marginTop: "2rem", display: "flex", flexWrap: "wrap", gap: "1rem" }}>
        {results.map((r, idx) => (
          <div key={idx} style={{ textAlign: "center" }}>
            <img
              src={`http://127.0.0.1:8000/frames/${r.frame}`}
              alt={r.frame}
              style={{ width: "200px", border: "1px solid #ccc" }}
            />
            <p>{r.frame}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default SearchFrames;