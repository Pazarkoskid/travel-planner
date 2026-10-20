import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import { useEffect } from "react";
import "leaflet/dist/leaflet.css";

export interface MapPoint {
  lat: number;
  lng: number;
  label: string;
  sub?: string;
  color?: string;
  order?: number;
}

function FitBounds({ points }: { points: MapPoint[] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 1) map.setView([points[0].lat, points[0].lng], 14);
    else if (points.length > 1) map.fitBounds(points.map((p) => [p.lat, p.lng] as [number, number]), { padding: [30, 30] });
  }, [map, points]);
  return null;
}

export default function MapView({ points, route = false, height = 380 }: { points: MapPoint[]; route?: boolean; height?: number }) {
  const center: [number, number] = points.length ? [points[0].lat, points[0].lng] : [41.6, 21.7];
  return (
    <div className="map" style={{ height }}>
      <MapContainer center={center} zoom={12} style={{ height: "100%", width: "100%" }} scrollWheelZoom={false}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds points={points} />
        {route && points.length > 1 && (
          <Polyline positions={points.map((p) => [p.lat, p.lng] as [number, number])} pathOptions={{ color: "#c99a2e", weight: 4, dashArray: "2 9", lineCap: "round" }} />
        )}
        {points.map((p, i) => (
          <CircleMarker
            key={`${p.lat}-${p.lng}-${i}`}
            center={[p.lat, p.lng]}
            radius={9}
            pathOptions={{ color: "#fff", weight: 2, fillColor: p.color || "#08415c", fillOpacity: 1 }}
          >
            <Popup>
              <strong>
                {p.order !== undefined ? `${p.order}. ` : ""}
                {p.label}
              </strong>
              {p.sub && <div>{p.sub}</div>}
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
