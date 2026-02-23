import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapPin, Navigation, MapPinned, Route, X } from 'lucide-react';

// Fix for default marker icons in React-Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const MapWithOSRM = () => {
  const [route, setRoute] = useState(null);
  const [startPoint, setStartPoint] = useState([28.6139, 77.2090]);
  const [endPoint, setEndPoint] = useState([28.7041, 77.1025]);
  const [selection, setSelection] = useState('start');
  const [waypoints, setWaypoints] = useState([]);
  const [manualLat, setManualLat] = useState('');
  const [manualLng, setManualLng] = useState('');
  const [showCoords, setShowCoords] = useState(false);

  const fetchRoute = async (start, end, mids) => {
    if (!start || !end) return;
    try {
      const segments = [start, ...mids, end]
        .map(pt => `${pt[1]},${pt[0]}`)
        .join(';');
      const response = await fetch(
        `https://router.project-osrm.org/route/v1/driving/${segments}?overview=full&geometries=geojson`
      );
      const data = await response.json();

      if (data.routes && data.routes.length > 0) {
        const coordinates = data.routes[0].geometry.coordinates.map(coord => [coord[1], coord[0]]);
        setRoute({
          coordinates,
          distance: (data.routes[0].distance / 1000).toFixed(2),
          duration: (data.routes[0].duration / 60).toFixed(0),
        });
      }
    } catch (error) {
      console.error('Error fetching route:', error);
    }
  };

  useEffect(() => {
    fetchRoute(startPoint, endPoint, waypoints);
  }, [startPoint, endPoint, waypoints]);

  return (
    <div className="h-screen w-full relative bg-[#f6f6f6]">
      <MapContainer
        center={startPoint}
        zoom={12}
        className="h-full w-full"
        style={{ height: '100%', width: '100%' }}
      >
        <MapClickHandler
          selection={selection}
          setStartPoint={setStartPoint}
          setEndPoint={setEndPoint}
          waypoints={waypoints}
          setWaypoints={setWaypoints}
        />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <Marker position={startPoint}>
          <Popup>
            <span className="font-medium">Start</span>
            <br />
            <span className="text-xs text-[#757575]">{startPoint[0].toFixed(5)}, {startPoint[1].toFixed(5)}</span>
          </Popup>
        </Marker>
        <Marker position={endPoint}>
          <Popup>
            <span className="font-medium">End</span>
            <br />
            <span className="text-xs text-[#757575]">{endPoint[0].toFixed(5)}, {endPoint[1].toFixed(5)}</span>
          </Popup>
        </Marker>

        {route && (
          <>
            <Polyline
              positions={route.coordinates}
              pathOptions={{ color: 'var(--uber-green)', weight: 5, opacity: 0.9 }}
            />
            <RouteInfo route={route} />
          </>
        )}
      </MapContainer>

      <ControlPanel
        selection={selection}
        setSelection={setSelection}
        setStartPoint={setStartPoint}
        setEndPoint={setEndPoint}
        waypoints={waypoints}
        setWaypoints={setWaypoints}
        manualLat={manualLat}
        manualLng={manualLng}
        setManualLat={setManualLat}
        setManualLng={setManualLng}
        showCoords={showCoords}
        setShowCoords={setShowCoords}
      />
    </div>
  );
};

const MapClickHandler = ({ selection, setStartPoint, setEndPoint, waypoints, setWaypoints }) => {
  useMapEvents({
    click(e) {
      const { lat, lng } = e.latlng;
      if (selection === 'start') setStartPoint([lat, lng]);
      else if (selection === 'end') setEndPoint([lat, lng]);
      else setWaypoints([...waypoints, [lat, lng]]);
    },
  });
  return null;
};

const RouteInfo = ({ route }) => (
  <div
    className="absolute top-4 right-4 z-[1000] rounded-[var(--radius-card)] bg-white p-4 min-w-[180px]"
    style={{ boxShadow: 'var(--shadow-float)' }}
  >
    <div className="flex items-center gap-2 mb-3">
      <Route className="w-4 h-4 text-[var(--uber-green)]" />
      <h3 className="text-sm font-semibold text-[#000]">Route</h3>
    </div>
    <div className="space-y-2 text-sm">
      <div className="flex justify-between gap-4">
        <span className="text-[#757575]">Distance</span>
        <span className="font-medium text-[#000]">{route.distance} km</span>
      </div>
      <div className="flex justify-between gap-4">
        <span className="text-[#757575]">Duration</span>
        <span className="font-medium text-[#000]">{route.duration} min</span>
      </div>
    </div>
  </div>
);

const ControlPanel = ({
  selection,
  setSelection,
  setStartPoint,
  setEndPoint,
  waypoints,
  setWaypoints,
  manualLat,
  manualLng,
  setManualLat,
  setManualLng,
  showCoords,
  setShowCoords,
}) => {
  const setFromGeolocation = () => {
    if (!navigator.geolocation) {
      alert('Geolocation not supported');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        if (selection === 'start') setStartPoint([latitude, longitude]);
        else if (selection === 'end') setEndPoint([latitude, longitude]);
        else setWaypoints([...waypoints, [latitude, longitude]]);
      },
      () => alert('Unable to get location')
    );
  };

  const setFromManual = () => {
    const lat = parseFloat(manualLat);
    const lng = parseFloat(manualLng);
    const valid = Number.isFinite(lat) && Number.isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180;
    if (!valid) {
      alert('Enter valid lat (-90–90) and lng (-180–180)');
      return;
    }
    if (selection === 'start') setStartPoint([lat, lng]);
    else if (selection === 'end') setEndPoint([lat, lng]);
    else setWaypoints([...waypoints, [lat, lng]]);
  };

  const pillBase = 'px-4 py-2 rounded-[var(--radius-pill)] text-sm font-medium transition-colors';
  const pillActive = 'bg-[#000] text-white';
  const pillInactive = 'bg-white text-[#616161] border border-[#e0e0e0] hover:bg-[#f6f6f6]';

  return (
    <div
      className="absolute bottom-4 left-4 right-4 z-[1000] rounded-[var(--radius-card)] bg-white p-4 flex flex-col gap-4"
      style={{ boxShadow: 'var(--shadow-float)' }}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-[#757575] mr-1">Set point:</span>
        <button
          type="button"
          onClick={() => setSelection('start')}
          className={`${pillBase} flex items-center gap-2 ${selection === 'start' ? pillActive : pillInactive}`}
        >
          <MapPin className="w-3.5 h-3.5" />
          Start
        </button>
        <button
          type="button"
          onClick={() => setSelection('end')}
          className={`${pillBase} flex items-center gap-2 ${selection === 'end' ? pillActive : pillInactive}`}
        >
          <MapPin className="w-3.5 h-3.5" />
          End
        </button>
        <button
          type="button"
          onClick={() => setSelection('waypoint')}
          className={`${pillBase} flex items-center gap-2 ${selection === 'waypoint' ? pillActive : pillInactive}`}
        >
          <MapPinned className="w-3.5 h-3.5" />
          Waypoint
        </button>
        <button
          type="button"
          onClick={setFromGeolocation}
          className={`${pillBase} flex items-center gap-2 ml-auto bg-[var(--uber-green)] text-white hover:opacity-90`}
        >
          <Navigation className="w-3.5 h-3.5" />
          My location
        </button>
      </div>

      <button
        type="button"
        onClick={() => setShowCoords(!showCoords)}
        className="text-xs font-medium text-[#757575] hover:text-[#000]"
      >
        {showCoords ? 'Hide' : 'Set by'} coordinates
      </button>
      {showCoords && (
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="text"
            placeholder="Lat"
            value={manualLat}
            onChange={(e) => setManualLat(e.target.value)}
            className="w-24 px-3 py-2 rounded-[var(--radius-btn)] border border-[#e0e0e0] text-sm focus:outline-none focus:ring-2 focus:ring-[#000]"
          />
          <input
            type="text"
            placeholder="Lng"
            value={manualLng}
            onChange={(e) => setManualLng(e.target.value)}
            className="w-24 px-3 py-2 rounded-[var(--radius-btn)] border border-[#e0e0e0] text-sm focus:outline-none focus:ring-2 focus:ring-[#000]"
          />
          <button
            type="button"
            onClick={setFromManual}
            className="px-4 py-2 rounded-[var(--radius-btn)] text-sm font-medium bg-[#000] text-white hover:opacity-90"
          >
            Set
          </button>
        </div>
      )}

      {waypoints.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-[#757575]">Stops:</span>
          {waypoints.map((wp, idx) => (
            <div
              key={`${wp[0]}-${wp[1]}-${idx}`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-pill)] bg-[#f6f6f6] border border-[#eee] text-xs"
            >
              <span className="text-[#424242]">{idx + 1}. {wp[0].toFixed(4)}, {wp[1].toFixed(4)}</span>
              <button
                type="button"
                onClick={() => setWaypoints(waypoints.filter((_, i) => i !== idx))}
                className="p-0.5 rounded-full hover:bg-[#e0e0e0] text-[#757575]"
                aria-label="Remove"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default MapWithOSRM;
