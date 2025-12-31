import { useCallback } from 'react';

export default function FileDropZone({ onFileSelect, selectedFile }) {
  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      const file = files[0];
      if (file.name.endsWith('.mid') || file.name.endsWith('.midi')) {
        onFileSelect(file);
      } else {
        alert('Please upload a MIDI file (.mid or .midi)');
      }
    }
  }, [onFileSelect]);

  const handleFileInput = useCallback((e) => {
    const files = e.target.files;
    if (files.length > 0) {
      onFileSelect(files[0]);
    }
  }, [onFileSelect]);

  return (
    <div
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-blue-500 transition-colors"
    >
      {selectedFile ? (
        <div className="space-y-4">
          <div className="text-6xl">🎵</div>
          <div>
            <p className="text-lg font-medium text-gray-900">{selectedFile.name}</p>
            <p className="text-sm text-gray-500">
              {(selectedFile.size / 1024).toFixed(2)} KB
            </p>
          </div>
          <label className="inline-block cursor-pointer text-blue-600 hover:text-blue-700">
            Choose different file
            <input
              type="file"
              accept=".mid,.midi"
              onChange={handleFileInput}
              className="hidden"
            />
          </label>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="text-6xl">📁</div>
          <div>
            <p className="text-lg font-medium text-gray-900">
              Drop MIDI file here or click to browse
            </p>
            <p className="text-sm text-gray-500 mt-2">
              Accepts .mid and .midi files
            </p>
          </div>
          <label className="inline-block mt-4 px-6 py-3 bg-blue-600 text-white rounded-lg cursor-pointer hover:bg-blue-700">
            Select File
            <input
              type="file"
              accept=".mid,.midi"
              onChange={handleFileInput}
              className="hidden"
            />
          </label>
        </div>
      )}
    </div>
  );
}
