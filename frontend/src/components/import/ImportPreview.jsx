export default function ImportPreview({ data }) {
  if (!data) return null;

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Preview</h2>
        <p className="text-sm text-gray-600">
          Review the parsed MIDI data below. You can edit the metadata before saving.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Title
          </label>
          <input
            type="text"
            value={data.title || ''}
            readOnly
            className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Composer
          </label>
          <input
            type="text"
            value={data.composer || 'Unknown'}
            readOnly
            className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Key
          </label>
          <input
            type="text"
            value={data.key || 'C'}
            readOnly
            className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Time Signature
          </label>
          <input
            type="text"
            value={data.time_signature || '4/4'}
            readOnly
            className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Genre
          </label>
          <input
            type="text"
            value={data.genre || 'Standard'}
            readOnly
            className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Tempo (BPM)
          </label>
          <input
            type="text"
            value={data.tempo || 120}
            readOnly
            className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
          />
        </div>
      </div>

      {data.sections && data.sections.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Sections Found: {data.sections.length}
          </h3>
          <div className="space-y-2">
            {data.sections.map((section, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-gray-50 rounded border border-gray-200"
              >
                <span className="font-medium">{section.name || `Section ${index + 1}`}</span>
                <span className="text-sm text-gray-600">
                  {section.measure_count} measures
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.chord_count && (
        <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg">
          <p className="text-sm text-blue-800">
            <strong>{data.chord_count}</strong> chords detected across{' '}
            <strong>{data.measure_count}</strong> measures
          </p>
        </div>
      )}
    </div>
  );
}
