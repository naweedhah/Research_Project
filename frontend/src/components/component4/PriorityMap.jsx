import { useEffect, useMemo } from 'react';
import { GeoJSON, MapContainer, TileLayer, useMap } from 'react-leaflet';
import L from 'leaflet';
import { formatCases, formatNumber, priorityColor } from './utils';
import { normalizeDistrictName } from './format';

const LEGEND = ['Critical', 'High', 'Medium', 'Low'];
const SRI_LANKA_CENTER = [7.8731, 80.7718];

function featureKey(feature) {
  const props = feature?.properties || {};
  return normalizeDistrictName(props._district_key || props.District || props.name);
}

function escapeHtml(value) {
  return String(value ?? '-')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function popupHtml(record, horizonKey) {
  const rows = [
    ['Priority', record.priority_level],
    ['DMBI', formatNumber(record.dmbi_score, 1)],
    ['Predicted cases', formatCases(record.predicted_cases)],
    ['Uncertainty', record.uncertainty_level],
    ['Confidence', record.confidence_label],
  ].filter(([, v]) => v !== undefined && v !== null && v !== '');

  return `
    <div style="font-size:14px;line-height:1.5;min-width:190px">
      <div style="font-size:16px;font-weight:700;color:#0B1F4D;margin-bottom:4px">
        ${escapeHtml(record.district)}
        <span style="font-weight:500;color:#64748b;font-size:13px"> (${escapeHtml(
          String(horizonKey).toUpperCase()
        )})</span>
      </div>
      ${rows
        .map(
          ([label, value]) =>
            `<div style="display:flex;justify-content:space-between;gap:12px"><span style="color:#64748b">${escapeHtml(
              label
            )}</span><strong style="color:#0B1F4D">${escapeHtml(value)}</strong></div>`
        )
        .join('')}
    </div>`;
}

function FitBounds({ boundaries }) {
  const map = useMap();
  useEffect(() => {
    if (!boundaries?.features?.length) return;
    const bounds = L.geoJSON(boundaries).getBounds();
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [12, 12] });
  }, [map, boundaries]);
  return null;
}

export default function PriorityMap({
  boundaries,
  districts = [],
  selectedDistrict,
  onSelectDistrict,
  horizonKey = 'h1',
  height = 420,
}) {
  const recordsByKey = useMemo(() => {
    const map = new Map();
    districts.forEach((record) => {
      map.set(normalizeDistrictName(record.district), record);
    });
    return map;
  }, [districts]);

  const selectedKey = normalizeDistrictName(selectedDistrict);
  const geoKey = `${horizonKey}|${selectedKey}|${districts.length}|${
    districts[0]?.target_date || ''
  }`;

  const style = (feature) => {
    const key = featureKey(feature);
    const record = recordsByKey.get(key);
    const isSelected = key === selectedKey;
    return {
      fillColor: record ? priorityColor(record.priority_level) : '#CBD5E1',
      fillOpacity: isSelected ? 0.92 : 0.72,
      color: isSelected ? '#0B1F4D' : '#FFFFFF',
      weight: isSelected ? 3 : 1.2,
    };
  };

  const onEachFeature = (feature, layer) => {
    const key = featureKey(feature);
    const record = recordsByKey.get(key);
    const label = record?.district || feature?.properties?.District || key;

    layer.bindTooltip(escapeHtml(label), { sticky: true });
    if (record) layer.bindPopup(popupHtml(record, horizonKey));

    layer.on({
      click: () => {
        if (record) onSelectDistrict?.(record.district);
      },
    });

    if (key === selectedKey) {
      layer.on('add', () => layer.bringToFront());
    }
  };

  return (
    <div
      className="relative overflow-hidden rounded-xl border border-slate-100"
      style={{ height }}
    >
      <MapContainer
        center={SRI_LANKA_CENTER}
        zoom={7}
        scrollWheelZoom
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {boundaries?.features?.length > 0 && (
          <>
            <FitBounds boundaries={boundaries} />
            <GeoJSON
              key={geoKey}
              data={boundaries}
              style={style}
              onEachFeature={onEachFeature}
            />
          </>
        )}
      </MapContainer>

      <div className="absolute bottom-3 left-3 z-[400] rounded-xl border border-slate-200 bg-white/95 px-3 py-2 shadow">
        <p className="mb-1 text-sm font-semibold text-primary">Priority</p>
        <div className="space-y-1">
          {LEGEND.map((level) => (
            <p key={level} className="flex items-center gap-2 text-sm text-slate-600">
              <span
                className="h-3 w-3 rounded-full"
                style={{ background: priorityColor(level) }}
              />
              {level}
            </p>
          ))}
        </div>
      </div>
    </div>
  );
}
