import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import { useEffect } from 'react';
import { districts, riskColor } from '../../data/districtData';
import DistrictPopup from './DistrictPopup';

function FitSriLanka() {
  const map = useMap();
  useEffect(() => {
    map.setView([7.8731, 80.7718], 7);
  }, [map]);
  return null;
}

export default function SriLankaMap({
  filterRisk = 'All',
  selectedId,
  onSelect,
  height = '100%',
  districtData = districts,
}) {
  const visible = districtData.filter(
    (d) => filterRisk === 'All' || d.risk === filterRisk.replace(' Risk', '')
  );

  return (
    <div className="overflow-hidden rounded-xl" style={{ height, minHeight: 320 }}>
      <MapContainer
        center={[7.8731, 80.7718]}
        zoom={7}
        scrollWheelZoom
        className="h-full w-full"
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitSriLanka />
        {visible.map((d) => (
          <CircleMarker
            key={d.id}
            center={[d.lat, d.lng]}
            radius={Math.max(8, Math.min(22, d.cases / 28))}
            pathOptions={{
              color: selectedId === d.id ? '#0B1F4D' : riskColor(d.risk),
              fillColor: riskColor(d.risk),
              fillOpacity: selectedId === d.id ? 0.9 : 0.65,
              weight: selectedId === d.id ? 3 : 1.5,
            }}
            eventHandlers={{
              click: () => onSelect?.(d),
            }}
          >
            <Popup>
              <DistrictPopup district={d} />
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
