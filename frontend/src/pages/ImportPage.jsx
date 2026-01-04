import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import FileDropZone from '../components/import/FileDropZone';
import ImportPreview from '../components/import/ImportPreview';

export default function ImportPage() {
  const [file, setFile] = useState(null);
  const [parsedData, setParsedData] = useState(null);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleFileSelect = (selectedFile) => {
    setFile(selectedFile);
    setParsedData(null);
    setError(null);
  };

  const handleParse = async () => {
    if (!file) return;

    setImporting(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/imports/midi/preview`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to parse MIDI file');
      }

      const data = await response.json();
      setParsedData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setImporting(false);
    }
  };

  const handleSave = async () => {
    if (!parsedData || !file) return;

    setImporting(true);
    setError(null);

    try {
      // Use the full import endpoint that saves chords too
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', parsedData.title);
      formData.append('composer', parsedData.composer || 'Unknown');
      formData.append('genre', parsedData.genre || 'Standard');

      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/imports/midi/import`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to import MIDI file');
      }

      const result = await response.json();
      navigate(`/songs/${result.song_id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setImporting(false);
    }
  };

  const handleCancel = () => {
    setFile(null);
    setParsedData(null);
    setError(null);
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Import MIDI File</h1>
        <Link 
          to="/import/audit"
          className="text-blue-600 hover:text-blue-800 underline text-sm"
        >
          Debug Parser →
        </Link>
      </div>

      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {!parsedData ? (
        <>
          <FileDropZone onFileSelect={handleFileSelect} selectedFile={file} />
          
          {file && (
            <div className="mt-6 flex gap-4">
              <button
                onClick={handleParse}
                disabled={importing}
                className="flex-1 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {importing ? 'Parsing...' : 'Parse MIDI File'}
              </button>
              <button
                onClick={handleCancel}
                className="px-6 py-3 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          )}
        </>
      ) : (
        <>
          <ImportPreview data={parsedData} />
          
          <div className="mt-6 flex gap-4">
            <button
              onClick={handleSave}
              disabled={importing}
              className="flex-1 bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {importing ? 'Saving...' : 'Save to Library'}
            </button>
            <button
              onClick={handleCancel}
              className="px-6 py-3 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </>
      )}
    </div>
  );
}

