import React, { useState } from "react";
import { FiUpload } from "react-icons/fi";

export default function UploadBox() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState("idle"); // idle | selected | uploading | uploaded | error
  const [message, setMessage] = useState("");
  const [serverData, setServerData] = useState(null);
  const handleFileChange = (e) => {
    const selected = e.target.files?.[0];
    if (!selected) return;

    const ext = selected.name.split(".").pop().toLowerCase();
    if (!["xlsx", "xls"].includes(ext)) {
      setStatus("error");
      setMessage("Only Excel files (.xlsx, .xls) are allowed.");
      e.target.value = "";
      setFile(null);
      return;
    }

    setFile(selected);
    setStatus("selected");
    setMessage(`Selected: ${selected.name}`);
    setServerData(null);
  };

  const handleUpload = async () => {
    if (!file) {
      setStatus("error");
      setMessage("Select an Excel file first!");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      setUploading(true);
      setStatus("uploading");
      setMessage("Uploading...");

      console.log("Uploading file:", file.name); // helps confirm click happened

      const apiBase = import.meta.env.VITE_API_BASE_URL || "https://velora-2669-2.onrender.com";

      const res = await fetch(`${apiBase}/api/upload-excel/`, {
        method: "POST",
        body: formData,
      });

      const text = await res.text();
let data = {};

try {
  data = JSON.parse(text);
} catch {
  throw new Error("Server returned non-JSON response");
}

      if (!res.ok) {
        throw new Error(data.error || `Upload failed (HTTP ${res.status})`);
      }

      // Normalize upload-only vs optimization responses
      setServerData(data);
      setStatus("uploaded");
      setMessage(`Uploaded ✅ ${file.name}`);

    } catch (err) {
      setStatus("error");
      setMessage(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="w-full max-w-md relative">
      <label className="border-2 border-dashed border-orange-400 rounded-xl p-12 flex flex-col items-center justify-center mb-4 hover:border-orange-600 transition-colors cursor-pointer relative">
        <FiUpload size={48} className="text-orange-500 mb-4" />
        <p className="text-orange-700 font-medium mb-1">Drop your Excel file here</p>
        <p className="text-sm text-orange-600">or click to browse (.xlsx, .xls)</p>

        <input
          type="file"
          accept=".xlsx,.xls"
          onChange={handleFileChange}
          className="hidden"
        />
      </label>

      {/* Status line */}
      {message && (
        <div
          className={`text-sm mb-4 ${
            status === "error" ? "text-red-600" : status === "uploaded" ? "text-green-700" : "text-orange-700"
          }`}
        >
          {message}
        </div>
      )}

      <button
        onClick={handleUpload}
        disabled={uploading || !file}
        className={`w-full ${
          uploading || !file ? "bg-orange-300" : "bg-orange-500 hover:bg-orange-600"
        } text-white font-semibold py-3 rounded-lg transition`}
      >
        {uploading ? "Uploading..." : "Upload & Optimize Routes"}
      </button>

      {/* Optional: show server response for debugging */}
      {serverData && (
        <pre className="mt-4 p-3 bg-white/50 rounded text-xs overflow-auto">
          {JSON.stringify(serverData, null, 2)}
        </pre>
      )}
    </div>
  );
}
