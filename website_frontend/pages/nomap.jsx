import React, { useEffect, useMemo, useState } from "react";
import {
  MapContainer,
  Marker,
  Popup,
  Polyline,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import * as XLSX from "xlsx";
import "leaflet/dist/leaflet.css";
import { useLocation, useNavigate } from "react-router-dom";
import {
  ChevronLeft,
  ChevronRight,
  Download,
  Route,
  User,
  Truck,
  Loader2,
  AlertCircle,
  X,
  Plus,
  LayoutGrid,
} from "lucide-react";

/* ---------------- Leaflet Icon Fix ---------------- */
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
  iconUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
});

/* ---------------- Custom SVG Icons ---------------- */
const createSvgIcon = (svgHtml, size = 28) =>
  L.divIcon({
    className: "",
    html: svgHtml,
    iconSize: [size, size],
    iconAnchor: [Math.floor(size / 2), size],
  });

const depotIcon = createSvgIcon(
  `
  <svg width="22" height="22" viewBox="0 0 22 22" xmlns="http://www.w3.org/2000/svg">
    <rect x="1" y="1" width="20" height="20" rx="5" fill="#e11d48" />
    <rect x="6.5" y="6" width="3" height="3" rx="0.6" fill="white" />
    <rect x="11.5" y="6" width="3" height="3" rx="0.6" fill="white" />
    <rect x="6.5" y="11" width="10" height="6" rx="1" fill="white" />
    <rect x="10.25" y="12.5" width="1.5" height="3" rx="0.4" fill="#e11d48" />
  </svg>
`,
  22
);

const employeeIcon = createSvgIcon(
  `
  <svg width="26" height="30" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
    <circle cx="9" cy="9" r="8" fill="black" />
    <circle cx="9" cy="6.3" r="1.8" fill="white" />
    <ellipse cx="9" cy="12.2" rx="4.2" ry="2.2" fill="white" />
  </svg>
`,
  18
);

// const COLORS = [
//   "#e11d48", "#2563eb", "#16a34a", "#f97316", "#7c3aed",
//   "#0891b2", "#dc2626", "#65a30d", "#d97706", "#0d9488",
//   "#9333ea", "#f43f5e", "#0284c7", "#22c55e", "#ea580c",
//   "#a855f7", "#14b8a6", "#ef4444", "#84cc16", "#f59e0b",
//   "#06b6d4", "#8b5cf6", "#10b981", "#3b82f6", "#ec4899",
// ];
const COLORS = [
  "#e11d48", "#2563eb", "#16a34a", "#f97316", "#7c3aed",
  "#0891b2", "#dc2626", "#65a30d", "#d97706", "#0d9488",
  "#9333ea", "#f43f5e", "#0284c7", "#22c55e", "#ea580c",
  "#a855f7", "#14b8a6", "#ef4444", "#84cc16", "#f59e0b",
  "#06b6d4", "#8b5cf6", "#10b981", "#3b82f6", "#ec4899",
];

const PREDEFINED_TESTCASES = [
  "TestCase_TC01.xlsx",
  "TestCase_TC02.xlsx",
  "TestCase_TC03.xlsx",
  "TestCase_TC04.xlsx",
];

function FitBounds({ bounds }) {
  const map = useMap();
  useEffect(() => {
    if (bounds) map.fitBounds(bounds, { padding: [10, 10] });
  }, [bounds, map]);
  return null;
}

function MapControls({ bounds }) {
  const map = useMap();
  const handleAutoFit = () => {
    if (bounds) map.fitBounds(bounds, { padding: [40, 40] });
  };
  return (
    <div className="leaflet-top leaflet-right" style={{ marginTop: 80, marginRight: 12 }}>
      <div
        className="flex flex-col rounded-[var(--radius-card)] overflow-hidden"
        style={{
          background: "#fff",
          boxShadow: "var(--shadow-float)",
          border: "1px solid rgba(0,0,0,0.06)",
          pointerEvents: 'auto',
        }}
      >
        <button
          type="button"
          aria-label="Zoom in"
          onClick={() => map.zoomIn()}
          className="w-11 h-11 flex items-center justify-center text-[#424242] hover:bg-[#f6f6f6] transition-colors border-b border-[#eee]"
        >
          <span className="text-lg font-medium leading-none">+</span>
        </button>
        <button
          type="button"
          aria-label="Zoom out"
          onClick={() => map.zoomOut()}
          className="w-11 h-11 flex items-center justify-center text-[#424242] hover:bg-[#f6f6f6] transition-colors border-b border-[#eee]"
        >
          <span className="text-lg font-medium leading-none">−</span>
        </button>
        <button
          type="button"
          aria-label="Auto fit routes"
          onClick={handleAutoFit}
          disabled={!bounds}
          className="w-11 h-11 flex items-center justify-center text-xs font-semibold text-[#616161] hover:bg-[#f6f6f6] transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent"
        >
          Fit
        </button>
      </div>
    </div>
  );
}

function formatTime(min) {
  if (!Number.isFinite(Number(min))) return "--:--";
  const normalizedMin = Math.max(0, Math.round(Number(min)));
  const hours = Math.floor(normalizedMin / 60);
  const minutes = normalizedMin % 60;
  return `${hours.toString().padStart(2, "0")}:${minutes
    .toString()
    .padStart(2, "0")}`;
}

function parseHHMMToMin(value) {
  if (typeof value !== "string") return NaN;
  const raw = value.trim();
  if (!raw || !raw.includes(":")) return NaN;
  const [hoursStr, minsStr] = raw.split(":", 2);
  const hours = Number(hoursStr);
  const mins = Number(minsStr);
  if (!Number.isFinite(hours) || !Number.isFinite(mins)) return NaN;
  return hours * 60 + mins;
}

export default function Loader() {
  const location = useLocation();
  const navigate = useNavigate();
  const file = location.state?.file;
  const testcaseName = location.state?.testcaseName;
  const effectiveTestcaseName =
    testcaseName || (PREDEFINED_TESTCASES.includes(file?.name) ? file.name : "");

  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [routes, setRoutes] = useState([]);
  const [isExporting, setIsExporting] = useState(false);
  const [showRoutes, setShowRoutes] = useState(true);
  const [selectedTripIndex, setSelectedTripIndex] = useState(null);
  const [tripsExpanded, setTripsExpanded] = useState(false);
  const [showEmployeeModal, setShowEmployeeModal] = useState(false);
  const [showVehicleModal, setShowVehicleModal] = useState(false);
  const [isAdding, setIsAdding] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [addedEmployees, setAddedEmployees] = useState([]);
  const [addedVehicles, setAddedVehicles] = useState([]);

  /* ---------------- Upload Logic ---------------- */
  useEffect(() => {
    if (!file && !testcaseName) {
      navigate("/");
      return;
    }

    const uploadFile = async () => {
      const formData = new FormData();
      
      if (file) {
        formData.append("file", file);
      } else if (testcaseName) {
        formData.append("testcase_name", testcaseName);
      }

      try {
        const apiBase =
          import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

        const res = await fetch(`${apiBase}/api/upload/`, {
          method: "POST",
          body: formData,
        });

        const data = await res.json();

        if (res.ok && data.status === "success") {
          setResult(data.data);
        } else {
          throw new Error(data.message || "Optimization failed");
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    uploadFile();
  }, [file, testcaseName, navigate]);

  const employees = result?.employees || [];
  const trips = result?.trips || [];
  const schedule = result?.schedule || [];
  const totalCost = result?.total_cost || 0;
  const costComparison = result?.cost_comparison || {};
  const employeeCostComparison = costComparison?.employees || [];
  const baselineTotal = Number(costComparison?.baseline_total || 0);
  const optimizedTotal = Number(costComparison?.optimized_total || 0);
  const savingsTotal = Number(costComparison?.savings_total || 0);
  const savingsTotalPct = baselineTotal > 0 ? (savingsTotal / baselineTotal) * 100 : 0;

  const employeeMap = useMemo(() => {
    const map = new Map();
    employees.forEach((emp) => map.set(emp.employee_id, emp));
    return map;
  }, [employees]);

  const pickupMinByEmployee = useMemo(() => {
    const map = new Map();
    employeeCostComparison.forEach((row) => {
      const pickupMin = parseHHMMToMin(row?.optimized_pickup_time);
      if (Number.isFinite(pickupMin)) {
        map.set(row.employee_id, pickupMin);
      }
    });
    return map;
  }, [employeeCostComparison]);

  const tripStartMinByIndex = useMemo(
    () =>
      schedule.map((item) => {
        const pickupMins = (item.employees || [])
          .map((employeeId) => pickupMinByEmployee.get(employeeId))
          .filter((value) => Number.isFinite(value));

        if (pickupMins.length > 0) {
          return Math.min(...pickupMins);
        }

        return Number(item.depart_min);
      }),
    [schedule, pickupMinByEmployee]
  );

  const employeeTimingById = useMemo(() => {
    const map = new Map();
    employeeCostComparison.forEach((row) => {
      map.set(row.employee_id, {
        pickup_time: row.optimized_pickup_time,
        dropoff_time: row.optimized_dropoff_time,
      });
    });
    return map;
  }, [employeeCostComparison]);

  const depot = useMemo(() => {
    if (employees.length > 0)
      return [employees[0].drop_lat, employees[0].drop_lng];
    return [28.6139, 77.2090];
  }, [employees]);

    // ---------------- Synthetic layout (plain background) ----------------
  // Deterministic "random" from a string (so positions stay stable per employee_id)
  const hash01 = (s) => {
    const str = String(s ?? "");
    let h = 2166136261;
    for (let i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    // map to [0,1)
    return ((h >>> 0) % 100000) / 100000;
  };

  // Map employee -> trip index (or null if not assigned)
  const empTripIndex = useMemo(() => {
    const m = new Map();
    schedule.forEach((item, idx) => {
      item.employees.forEach((id) => m.set(id, idx));
    });
    return m;
  }, [schedule]);

  // Build "display positions" (synthetic lat/lng around depot)
  // Same trip => same y (lat) line, x (lng) varies per employee (random-ish)
  const displayPosByEmpId = useMemo(() => {
    const [dLat, dLng] = depot;

    // degrees spacing (small offsets)
    const rowSpacing = 0.01;   // vertical separation between trips
    const colSpread  = 0.05;   // horizontal spread for employees
    const baseLatOffset = 0.01; // push employees a bit away from depot

    // group by trip index
    const tripToEmps = new Map();
    employees.forEach((emp) => {
      const t = empTripIndex.get(emp.employee_id);
      if (!tripToEmps.has(t)) tripToEmps.set(t, []);
      tripToEmps.get(t).push(emp.employee_id);
    });

    // stable ordering of trips: numeric first, then null (unassigned)
    const tripKeys = Array.from(tripToEmps.keys()).sort((a, b) => {
      if (a === null || a === undefined) return 1;
      if (b === null || b === undefined) return -1;
      return a - b;
    });

    const pos = new Map();

tripKeys.forEach((tripKey, colIdx) => {
  const ids = tripToEmps.get(tripKey) || [];
  const sorted = [...ids].sort((a, b) => String(a).localeCompare(String(b)));

  // ---- AUTO SPACING LOGIC ----

  const totalTrips = tripKeys.length;
  const maxEmployeesInTrip = Math.max(
    ...tripKeys.map((k) => (tripToEmps.get(k) || []).length)
  );

  // Wider spacing if fewer trips, tighter if many
  const colGap = Math.max(0.12, 0.35 / totalTrips);

  // Taller stacks if many employees
  const rowGap = Math.max(0.08, 0.6 / (maxEmployeesInTrip + 1));

  // Push entire layout higher above depot
  const baseUp = 0.25;

  // Center columns around depot
  const center = (totalTrips - 1) / 2;
  const lineLng = dLng + (colIdx - center) * colGap;

  sorted.forEach((id, k) => {
    const lineLat = dLat + baseUp + k * rowGap;
    pos.set(id, [lineLat, lineLng]);
  });
});

    return pos;
  }, [employees, empTripIndex, depot]);

  // Straight "routes": one straight segment from each employee to depot
const straightRoutes = useMemo(() => {
  return schedule.map((item, idx) => {
    // positions in the SAME ORDER as employees appear in schedule (or sort if you want)
    const coords = item.employees
      .map((id) => displayPosByEmpId.get(id))
      .filter(Boolean);

    if (!coords.length) return null;

    // Sort by latitude so it becomes a clean vertical chain (top -> bottom)
    const sorted = [...coords].sort((a, b) => b[0] - a[0]); // higher lat first

    // Vertical chain between employees + connect bottom-most to depot
    const bottomMost = sorted[sorted.length - 1];
    const path = [...sorted, depot];

    return {
      tripIndex: idx,
      color: COLORS[idx % COLORS.length],
      path,
    };
  }).filter(Boolean);
}, [schedule, displayPosByEmpId, depot]);

  /* ---------------- Employee Trip Info ---------------- */
  const getEmployeeTripInfo = (employeeId) => {
    const trip = schedule.find((item) =>
      item.employees.includes(employeeId)
    );

    if (!trip) return null;

    const timing = employeeTimingById.get(employeeId);

    return {
      vehicle_id: trip.vehicle_id,
      trip_id: trip.trip_id,
      depart: timing?.pickup_time || formatTime(trip.depart_min),
      arrival: timing?.dropoff_time || formatTime(trip.arrival_min),
    };
  };



  useEffect(() => {
    setSelectedTripIndex(null);
  }, [schedule]);
  const fitBounds = useMemo(() => {
    const pts = [];

    // include depot
    pts.push(depot);

    // include all synthetic employee positions
    employees.forEach((emp) => {
      const p = displayPosByEmpId.get(emp.employee_id);
      if (p) pts.push(p);
    });

    if (pts.length === 0) return null;

    const b = L.latLngBounds([]);
    pts.forEach((pt) => b.extend(pt));
    return b;
  }, [employees, displayPosByEmpId, depot]);

  const buildComparisonExportRows = () => {
    return employeeCostComparison.map((row) => ({
      "Emp ID": row.employee_id,
      "Vehicle Assigned": row.vehicle_assigned || "--",
      "Baseline Cost": Number(row.baseline_cost || 0).toFixed(2),
      "Optimized Cost": Number(row.optimized_cost || 0).toFixed(2),
      "Absolute Cost Saving": Number(
        row.absolute_cost_saving ?? Math.abs(Number(row.savings || 0))
      ).toFixed(2),
      "Baseline Time": row.baseline_time || formatTime(row.baseline_time_min),
      "Optimized Time": row.optimized_time || formatTime(row.optimized_time_min),
      "Absolute Time Saving": Number(
        row.absolute_time_saving_min ?? Math.abs(Number(row.time_savings_min || 0))
      ).toFixed(2),
      "% Saving Cost": Number(row.cost_saving_pct || 0).toFixed(2),
      "% Saving Time": Number(row.time_saving_pct || 0).toFixed(2),
      "Optimized Pickup Time": row.optimized_pickup_time || "--:--",
      "Optimized Dropoff Time": row.optimized_dropoff_time || "--:--",
    }));
  };

  const handleDownloadOutputExcel = async () => {
    if (!result) return;

    setIsExporting(true);

    try {
      const comparisonRows = buildComparisonExportRows();

      const workbook = XLSX.utils.book_new();

      const totalBaselineTimeMin = employeeCostComparison.reduce(
        (sum, row) => sum + Number(row.baseline_time_min || 0),
        0
      );
      const totalOptimizedTimeMin = employeeCostComparison.reduce(
        (sum, row) => sum + Number(row.optimized_time_min || 0),
        0
      );

      const absoluteCostSaving = Math.abs(baselineTotal - optimizedTotal);
      const costSavingPct = baselineTotal > 0
        ? Math.abs(((baselineTotal - optimizedTotal) / baselineTotal) * 100)
        : 0;

      const absoluteTimeSavingMin = Math.abs(totalBaselineTimeMin - totalOptimizedTimeMin);
      const timeSavingPct = totalBaselineTimeMin > 0
        ? Math.abs(((totalBaselineTimeMin - totalOptimizedTimeMin) / totalBaselineTimeMin) * 100)
        : 0;

      const summaryRows = [
        { metric: "Total Baseline Cost", value: Number(baselineTotal || 0).toFixed(2) },
        { metric: "Total Optimized Cost", value: Number(optimizedTotal || 0).toFixed(2) },
        { metric: "Absolute Cost Saving", value: Number(absoluteCostSaving || 0).toFixed(2) },
        { metric: "% Cost Saving", value: Number(costSavingPct || 0).toFixed(2) },
        { metric: "Total Baseline Time", value: Number(totalBaselineTimeMin || 0).toFixed(2) },
        { metric: "Total Optimized Time", value: Number(totalOptimizedTimeMin || 0).toFixed(2) },
        { metric: "Absolute Time Saving", value: Number(absoluteTimeSavingMin || 0).toFixed(2) },
        { metric: "% Time Saving", value: Number(timeSavingPct || 0).toFixed(2) },
      ];

      XLSX.utils.book_append_sheet(
        workbook,
        XLSX.utils.json_to_sheet(summaryRows),
        "Summary"
      );
      XLSX.utils.book_append_sheet(
        workbook,
        XLSX.utils.json_to_sheet(comparisonRows),
        "Cost_Time_Comparison"
      );

      const timestamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
      XLSX.writeFile(workbook, `optimized-output-${timestamp}.xlsx`);
    } finally {
      setIsExporting(false);
    }
  };

  const handleAddEmployee = async (e) => {
    e.preventDefault();
    setIsAdding(true);

    const formData = new FormData(e.target);
    const employeeData = {
      employee_id: formData.get("employee_id"),
      priority: parseInt(formData.get("priority")),
      pickup_lat: parseFloat(formData.get("pickup_lat")),
      pickup_lng: parseFloat(formData.get("pickup_lng")),
      drop_lat: parseFloat(formData.get("drop_lat")),
      drop_lng: parseFloat(formData.get("drop_lng")),
      earliest_pickup: formData.get("earliest_pickup"),
      latest_drop: formData.get("latest_drop"),
      vehicle_preference: formData.get("vehicle_preference"),
      sharing_preference: formData.get("sharing_preference"),
      baseline_cost: parseFloat(formData.get("baseline_cost")),
      baseline_time: parseFloat(formData.get("baseline_time")),
    };

    try {
      if (!effectiveTestcaseName) {
        alert("Adding entities is only supported for predefined testcases");
        setIsAdding(false);
        return;
      }

      const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
      const nextAddedEmployees = [...addedEmployees, employeeData];
      const formDataUpload = new FormData();
      formDataUpload.append("entity_type", "employee");
      formDataUpload.append("testcase_name", effectiveTestcaseName);
      formDataUpload.append("entity_data", JSON.stringify(employeeData));
      formDataUpload.append("added_employees", JSON.stringify(nextAddedEmployees));
      formDataUpload.append("added_vehicles", JSON.stringify(addedVehicles));

      const res = await fetch(`${apiBase}/api/add-entity/`, {
        method: "POST",
        body: formDataUpload,
      });

      const data = await res.json();
      if (res.ok && data.status === "success") {
        setResult(data.data);
        setAddedEmployees(nextAddedEmployees);
        setShowEmployeeModal(false);
      } else {
        console.error("Backend error details:", data);
        throw new Error(data.message || "Failed to add employee");
      }
    } catch (err) {
      console.error("Full error:", err);
      alert(err.message);
    } finally {
      setIsAdding(false);
    }
  };

  const handleAddVehicle = async (e) => {
    e.preventDefault();
    setIsAdding(true);

    const formData = new FormData(e.target);
    const vehicleData = {
      vehicle_id: formData.get("vehicle_id"),
      capacity: parseInt(formData.get("capacity")),
      cost_per_km: parseFloat(formData.get("cost_per_km")),
      avg_speed_kmph: parseFloat(formData.get("avg_speed_kmph")),
      current_lat: parseFloat(formData.get("current_lat")),
      current_lng: parseFloat(formData.get("current_lng")),
      available_from: formData.get("available_from"),
      category: formData.get("category"),
    };

    try {
      if (!effectiveTestcaseName) {
        alert("Adding entities is only supported for predefined testcases");
        setIsAdding(false);
        return;
      }

      const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
      const nextAddedVehicles = [...addedVehicles, vehicleData];
      const formDataUpload = new FormData();
      formDataUpload.append("entity_type", "vehicle");
      formDataUpload.append("testcase_name", effectiveTestcaseName);
      formDataUpload.append("entity_data", JSON.stringify(vehicleData));
      formDataUpload.append("added_employees", JSON.stringify(addedEmployees));
      formDataUpload.append("added_vehicles", JSON.stringify(nextAddedVehicles));

      const res = await fetch(`${apiBase}/api/add-entity/`, {
        method: "POST",
        body: formDataUpload,
      });

      const data = await res.json();
      if (res.ok && data.status === "success") {
        setResult(data.data);
        setAddedVehicles(nextAddedVehicles);
        setShowVehicleModal(false);
      } else {
        console.error("Backend error details:", data);
        throw new Error(data.message || "Failed to add vehicle");
      }
    } catch (err) {
      console.error("Full error:", err);
      alert(err.message);
    } finally {
      setIsAdding(false);
    }
  };

  /* ---------------- Loading & Error ---------------- */

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f6f6f6]">
        <div
          className="flex flex-col items-center gap-6 rounded-[var(--radius-card)] px-10 py-12 text-center"
          style={{ background: "#fff", boxShadow: "var(--shadow-card)" }}
        >
          <Loader2 className="w-12 h-12 text-[var(--uber-green)] animate-spin" />
          <div>
            <h2 className="text-lg font-semibold text-[#000]">Optimizing routes</h2>
            <p className="text-sm text-[#757575] mt-1">This may take a moment</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f6f6f6] p-4">
        <div
          className="flex flex-col items-center gap-6 rounded-[var(--radius-card)] px-10 py-12 max-w-md text-center"
          style={{ background: "#fff", boxShadow: "var(--shadow-card)" }}
        >
          <div className="w-14 h-14 rounded-full bg-red-50 flex items-center justify-center">
            <AlertCircle className="w-7 h-7 text-red-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-[#000]">Something went wrong</h2>
            <p className="text-sm text-[#757575] mt-2">{error}</p>
          </div>
          <button
            onClick={() => navigate("/")}
            className="px-6 py-3 rounded-[var(--radius-btn)] font-medium text-white transition-colors"
            style={{ background: "var(--uber-black)" }}
          >
            Back to upload
          </button>
        </div>
      </div>
    );
  }


  /* ---------------- Main Layout ---------------- */

  return (
    <div className="h-screen flex bg-[#f6f6f6]">
      {/* -------- Collapsible left panel (Uber-style drawer) -------- */}
      <div
        className="flex flex-col h-full bg-white overflow-hidden transition-[width] duration-300 ease-out border-r border-[#eee]"
        style={{
          width: sidebarOpen ? 360 : 0,
          boxShadow: sidebarOpen ? "var(--shadow-card)" : "none",
        }}
      >
        <div className="flex-shrink-0 flex items-center justify-between px-5 py-4 border-b border-[#eee]">
          <h2 className="text-lg font-semibold text-[#000]">Optimization</h2>
          <button
            type="button"
            onClick={() => setSidebarOpen(false)}
            className="p-2 rounded-lg hover:bg-[#f6f6f6] text-[#616161]"
            aria-label="Close panel"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleDownloadOutputExcel}
              disabled={isExporting}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-[var(--radius-btn)] font-medium text-white transition-colors disabled:opacity-60"
              style={{ background: "var(--uber-black)" }}
            >
              {isExporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              {isExporting ? "Preparing…" : "Export Excel"}
            </button>
            <button
              type="button"
              onClick={() => setShowRoutes((prev) => !prev)}
              className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-[var(--radius-btn)] font-medium text-[#424242] bg-[#f6f6f6] hover:bg-[#eee] transition-colors border border-[#e0e0e0]"
            >
              <Route className="w-4 h-4" />
              {showRoutes ? "Hide routes" : "Show routes"}
            </button>
          </div>

          <div className="rounded-[var(--radius-card)] p-4 border border-[#eee] bg-[#fafafa]">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-[#757575] mb-3">Summary</h3>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <p className="text-xs text-[#757575]">Employees</p>
                <p className="text-lg font-semibold text-[#000]">{employees.length}</p>
              </div>
              <div>
                <p className="text-xs text-[#757575]">Vehicles</p>
                <p className="text-lg font-semibold text-[#000]">{new Set(schedule.map((s) => s.vehicle_id)).size}</p>
              </div>
              <div>
                <p className="text-xs text-[#757575]">Trips</p>
                <p className="text-lg font-semibold text-[#000]">{trips.length}</p>
              </div>
            </div>
          </div>

          <div className="rounded-[var(--radius-card)] p-4 border border-[#eee] bg-white" style={{ boxShadow: "var(--shadow-card)" }}>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-[#757575] mb-3">Cost comparison</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-[#616161]">Baseline</span>
                <span className="font-medium">₹{baselineTotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#616161]">Optimized</span>
                <span className="font-medium">₹{optimizedTotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between pt-2 border-t border-[#eee]">
                <span className="text-[#616161]">Savings</span>
                <span className="font-semibold" style={{ color: savingsTotal >= 0 ? "var(--uber-green)" : "#b91c1c" }}>
                  ₹{Math.abs(savingsTotal).toFixed(2)} ({Math.abs(savingsTotalPct).toFixed(1)}%) {savingsTotal >= 0 ? "saved" : "increase"}
                </span>
              </div>
            </div>
            {employeeCostComparison.length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-medium text-[#757575] mb-2">Per employee</p>
                <div className="max-h-40 overflow-y-auto rounded-lg border border-[#eee] bg-white">
                  <div className="flex items-center px-3 py-2 bg-[#fafafa] border-b border-[#eee] sticky top-0 z-10">
                    <div className="flex-1 text-xs font-medium text-[#616161]">ID</div>
                    <div className="w-24 text-right text-xs font-medium text-[#616161]">Base</div>
                    <div className="w-24 text-right text-xs font-medium text-[#616161]">Opt</div>
                    <div className="w-28 text-right text-xs font-medium text-[#616161]">Save %</div>
                  </div>
                  <div>
                    {employeeCostComparison.map((row, i) => {
                      const saveColor = Number(row.savings || 0) >= 0 ? "var(--uber-green)" : "#b91c1c";
                      const savePct = Math.abs(Number(row.baseline_cost || 0)) > 0
                        ? `${((Number(row.savings || 0) / Number(row.baseline_cost || 0)) * 100).toFixed(1)}%`
                        : "0%";
                      return (
                        <div
                          key={row.employee_id}
                          className={`flex items-center px-3 py-2 text-sm ${i % 2 === 0 ? 'bg-white' : 'bg-[#fbfbfb]'} hover:bg-[#f8f8f8]`}
                          style={{ borderTop: '1px solid rgba(0,0,0,0.04)' }}
                        >
                          <div className="flex-1 text-[#424242]">{row.employee_id}</div>
                          <div className="w-24 text-right text-[#424242]">₹{Number(row.baseline_cost || 0).toFixed(2)}</div>
                          <div className="w-24 text-right text-[#424242]">₹{Number(row.optimized_cost || 0).toFixed(2)}</div>
                          <div className="w-28 text-right font-medium" style={{ color: saveColor }}>{savePct}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-[#757575]">Trips</h3>
              <button
                type="button"
                onClick={() => { setSelectedTripIndex(null); setShowRoutes(true); }}
                className="text-xs font-medium text-[var(--uber-green)] hover:underline"
              >
                Clear Filter
              </button>
            </div>
            <div className="space-y-2">
              {(tripsExpanded ? schedule : schedule.slice(0, 4)).map((item, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => { setSelectedTripIndex(idx); setShowRoutes(true); }}
                  className="w-full text-left rounded-[var(--radius-btn)] p-3 transition-colors border"
                  style={{
                    borderColor: selectedTripIndex === idx ? COLORS[idx % COLORS.length] : "#eee",
                    background: selectedTripIndex === idx ? `${COLORS[idx % COLORS.length]}10` : "#fff",
                  }}
                >
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full shrink-0" style={{ background: COLORS[idx % COLORS.length] }} />
                    <span className="font-medium text-[#000]">{item.vehicle_id}</span>
                    <span className="text-xs text-[#757575]">({item.trip_id})</span>
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-sm text-[#616161]">
                    <User className="w-3.5 h-3.5" />
                    {item.employees.join(", ")}
                  </div>
                  <div className="text-xs text-[#757575] mt-0.5">
                    {formatTime(tripStartMinByIndex[idx])} → {formatTime(item.arrival_min)}
                  </div>
                </button>
              ))}
            </div>
            {schedule.length > 4 && (
              <div className="mt-2">
                <button
                  type="button"
                  onClick={() => {
                    if (!tripsExpanded) {
                      setTripsExpanded(true);
                      setShowRoutes(true);
                      setSelectedTripIndex(null);
                    } else {
                      setTripsExpanded(false);
                    }
                  }}
                  className="w-full text-sm font-medium text-[var(--uber-green)] py-2 rounded-[var(--radius-btn)] hover:underline"
                >
                  {tripsExpanded ? "Show Less" : "Show All Trips"}
                </button>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={() => navigate("/")}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-[var(--radius-btn)] font-medium text-[#424242] bg-[#f6f6f6] hover:bg-[#eee] border border-[#e0e0e0] transition-colors"
          >
            <LayoutGrid className="w-4 h-4" />
            Upload new testcase
          </button>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setShowEmployeeModal(true)}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-[var(--radius-btn)] font-medium text-white transition-colors bg-[#000] hover:bg-[#111]"
              title="Add employee"
            >
              <User className="w-4 h-4" />
              Employee
            </button>
            <button
              type="button"
              onClick={() => setShowVehicleModal(true)}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-[var(--radius-btn)] font-medium text-white transition-colors bg-[#000] hover:bg-[#111]"
              title="Add vehicle"
            >
              <Truck className="w-4 h-4" />
              Vehicle
            </button>
          </div>
        </div>
      </div>

      {/* Toggle sidebar when closed */}
      {!sidebarOpen && (
        <button
          type="button"
          onClick={() => setSidebarOpen(true)}
          className="absolute left-4 top-4 z-[1000] w-10 h-10 flex items-center justify-center rounded-[var(--radius-card)] bg-white text-[#424242] hover:bg-[#f6f6f6] transition-colors"
          style={{ boxShadow: "var(--shadow-float)" }}
          aria-label="Open panel"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      )}

      {/* -------- MAP -------- */}
      <div className="flex-1 relative min-w-0">
        <MapContainer
          center={depot}
          zoom={20}
          zoomControl={false}
          style={{ height: "100%", width: "100%" ,background: "#f3f4f6" }}
        >
          

          {fitBounds && <FitBounds bounds={fitBounds} />}
          <MapControls bounds={fitBounds} />

          {/* Depot Marker */}
          <Marker position={depot} icon={depotIcon}>
            <Popup>
              <strong>Office / Depot</strong>
            </Popup>
          </Marker>

          {/* Employee Markers */}
          {employees.map((emp) => {
            const tripInfo = getEmployeeTripInfo(emp.employee_id);
            const employeeTripIndex = empTripIndex.get(emp.employee_id);
            const isDimmed =
              selectedTripIndex !== null && employeeTripIndex !== selectedTripIndex;

            return (
              <Marker
                key={emp.employee_id}
                 position={displayPosByEmpId.get(emp.employee_id) || depot}
                icon={employeeIcon}
                opacity={isDimmed ? 0.5 : 1}
                eventHandlers={{
                  mouseover: (e) => e.target.openPopup(),
                  mouseout: (e) => e.target.closePopup(),
                }}
              >
                <Popup>
                  <div style={{ minWidth: "180px" }}>
                    <strong>Employee:</strong> {emp.employee_id}
                    <br />
                    {tripInfo ? (
                      <>
                        <hr />
                        <strong>Trip ID:</strong> {tripInfo.trip_id}
                        <br />
                        <strong>Vehicle:</strong> {tripInfo.vehicle_id}
                        <br />
                        <strong>Pickup:</strong> {tripInfo.depart}
                        <br />
                        <strong>Dropoff:</strong> {tripInfo.arrival}
                      </>
                    ) : (
                      <div style={{ color: "gray" }}>
                        No trip assigned
                      </div>
                    )}
                  </div>
                </Popup>
              </Marker>
            );
          })}
          {/* Straight Routes: employee -> depot (colored by trip) */}
          {/* Trip Routes: vertical chain + bottom to depot */}
{showRoutes &&
  straightRoutes.map((r, idx) =>
    selectedTripIndex !== null && selectedTripIndex !== r.tripIndex ? null : (
      <Polyline
        key={idx}
        positions={r.path}
        pathOptions={{ color: r.color, weight: 4 }}
      />
    )
  )}
        </MapContainer>
      </div>

      {/* Employee Modal — Uber-style card */}
      {showEmployeeModal && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm" onClick={() => !isAdding && setShowEmployeeModal(false)}>
          <div className="bg-white rounded-2xl w-full max-w-md max-h-[90vh] overflow-hidden flex flex-col shadow-[var(--shadow-modal)]" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#eee]">
              <h3 className="text-lg font-semibold text-[#000]">Add employee</h3>
              <button type="button" onClick={() => !isAdding && setShowEmployeeModal(false)} className="p-2 rounded-lg hover:bg-[#f6f6f6] text-[#616161]" aria-label="Close">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleAddEmployee} className="flex-1 overflow-y-auto">
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-[#424242] mb-1">Employee ID *</label>
                  <input name="employee_id" required className="w-full px-3 py-2.5 rounded-[var(--radius-btn)] border border-[#e0e0e0] bg-white focus:outline-none focus:ring-2 focus:ring-[#000] focus:border-transparent" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#424242] mb-1">Priority (1–5) *</label>
                  <input name="priority" type="number" min="1" max="5" required className="w-full px-3 py-2.5 rounded-[var(--radius-btn)] border border-[#e0e0e0] bg-white focus:outline-none focus:ring-2 focus:ring-[#000] focus:border-transparent" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-[#424242] mb-1">Pickup Lat *</label>
                    <input name="pickup_lat" type="number" step="any" required className="w-full px-3 py-2.5 rounded-[var(--radius-btn)] border border-[#e0e0e0] bg-white focus:outline-none focus:ring-2 focus:ring-[#000] focus:border-transparent" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#424242] mb-1">Pickup Lng *</label>
                    <input name="pickup_lng" type="number" step="any" required className="w-full px-3 py-2.5 rounded-[var(--radius-btn)] border border-[#e0e0e0] bg-white focus:outline-none focus:ring-2 focus:ring-[#000] focus:border-transparent" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-[#424242] mb-1">Drop Lat *</label>
                    <input name="drop_lat" type="number" step="any" required className="w-full px-3 py-2.5 rounded-[var(--radius-btn)] border border-[#e0e0e0] bg-white focus:outline-none focus:ring-2 focus:ring-[#000] focus:border-transparent" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#424242] mb-1">Drop Lng *</label>
                    <input name="drop_lng" type="number" step="any" required className="w-full px-3 py-2.5 rounded-[var(--radius-btn)] border border-[#e0e0e0] bg-white focus:outline-none focus:ring-2 focus:ring-[#000] focus:border-transparent" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-[#424242] mb-1">Earliest pickup *</label>
                    <input name="earliest_pickup" type="time" required className="w-full px-3 py-2.5 rounded-[var(--radius-btn)] border border-[#e0e0e0] bg-white focus:outline-none focus:ring-2 focus:ring-[#000] focus:border-transparent" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#424242] mb-1">Latest drop *</label>
                    <input name="latest_drop" type="time" required className="w-full px-3 py-2.5 rounded-[var(--radius-btn)] border border-[#e0e0e0] bg-white focus:outline-none focus:ring-2 focus:ring-[#000] focus:border-transparent" />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#424242] mb-1">Vehicle preference *</label>
                  <select name="vehicle_preference" required className="w-full px-3 py-2.5 rounded-[var(--radius-btn)] border border-[#e0e0e0] bg-white focus:outline-none focus:ring-2 focus:ring-[#000] focus:border-transparent">
                    <option value="">Select…</option>
                    <option value="any">Any</option>
                    <option value="premium">Premium</option>
                    <option value="normal">Normal</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#424242] mb-1">Sharing preference *</label>
                  <select name="sharing_preference" required className="w-full px-3 py-2.5 rounded-[var(--radius-btn)] border border-[#e0e0e0] bg-white focus:outline-none focus:ring-2 focus:ring-[#000] focus:border-transparent">
                    <option value="">Select…</option>
                    <option value="any">Any</option>
                    <option value="single">Single</option>
                    <option value="double">Double</option>
                    <option value="triple">Triple</option>
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-[#424242] mb-1">Baseline cost *</label>
                    <input name="baseline_cost" type="number" step="any" required className="w-full px-3 py-2.5 rounded-[var(--radius-btn)] border border-[#e0e0e0] bg-white focus:outline-none focus:ring-2 focus:ring-[#000] focus:border-transparent" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#424242] mb-1">Baseline time (min) *</label>
                    <input name="baseline_time" type="number" step="any" required className="w-full px-3 py-2.5 rounded-[var(--radius-btn)] border border-[#e0e0e0] bg-white focus:outline-none focus:ring-2 focus:ring-[#000] focus:border-transparent" />
                  </div>
                </div>
              </div>
              <div className="flex gap-3 px-6 py-4 border-t border-[#eee] bg-[#fafafa]">
                <button type="button" onClick={() => !isAdding && setShowEmployeeModal(false)} disabled={isAdding} className="flex-1 py-2.5 rounded-[var(--radius-btn)] font-medium text-[#424242] bg-white border border-[#e0e0e0] hover:bg-[#f6f6f6] disabled:opacity-50">
                  Cancel
                </button>
                <button type="submit" disabled={isAdding} className="flex-1 py-2.5 rounded-[var(--radius-btn)] font-medium text-white bg-[#000] hover:bg-[#111] disabled:opacity-50 flex items-center justify-center gap-2">
                  {isAdding ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  {isAdding ? "Adding…" : "Add employee"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Vehicle Modal — Uber-style card */}
      {showVehicleModal && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm" onClick={() => !isAdding && setShowVehicleModal(false)}>
          <div className="bg-white rounded-2xl w-full max-w-md max-h-[90vh] overflow-hidden flex flex-col shadow-[var(--shadow-modal)]" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#eee]">
              <h3 className="text-lg font-semibold text-[#000]">Add vehicle</h3>
              <button type="button" onClick={() => !isAdding && setShowVehicleModal(false)} className="p-2 rounded-lg hover:bg-[#f6f6f6] text-[#616161]" aria-label="Close">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleAddVehicle} className="flex-1 overflow-y-auto">
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-[#424242] mb-1">Vehicle ID *</label>
                  <input name="vehicle_id" required className="w-full px-3 py-2.5 rounded-[var(--radius-btn)] border border-[#e0e0e0] bg-white focus:outline-none focus:ring-2 focus:ring-[#000] focus:border-transparent" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-[#424242] mb-1">Capacity *</label>
                    <input name="capacity" type="number" min="1" required className="w-full px-3 py-2.5 rounded-[var(--radius-btn)] border border-[#e0e0e0] bg-white focus:outline-none focus:ring-2 focus:ring-[#000] focus:border-transparent" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#424242] mb-1">Cost per km *</label>
                    <input name="cost_per_km" type="number" step="any" required className="w-full px-3 py-2.5 rounded-[var(--radius-btn)] border border-[#e0e0e0] bg-white focus:outline-none focus:ring-2 focus:ring-[#000] focus:border-transparent" />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#424242] mb-1">Avg speed (km/h) *</label>
                  <input name="avg_speed_kmph" type="number" step="any" required className="w-full px-3 py-2.5 rounded-[var(--radius-btn)] border border-[#e0e0e0] bg-white focus:outline-none focus:ring-2 focus:ring-[#000] focus:border-transparent" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-[#424242] mb-1">Current Lat *</label>
                    <input name="current_lat" type="number" step="any" required className="w-full px-3 py-2.5 rounded-[var(--radius-btn)] border border-[#e0e0e0] bg-white focus:outline-none focus:ring-2 focus:ring-[#000] focus:border-transparent" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#424242] mb-1">Current Lng *</label>
                    <input name="current_lng" type="number" step="any" required className="w-full px-3 py-2.5 rounded-[var(--radius-btn)] border border-[#e0e0e0] bg-white focus:outline-none focus:ring-2 focus:ring-[#000] focus:border-transparent" />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#424242] mb-1">Available from *</label>
                  <input name="available_from" type="time" required className="w-full px-3 py-2.5 rounded-[var(--radius-btn)] border border-[#e0e0e0] bg-white focus:outline-none focus:ring-2 focus:ring-[#000] focus:border-transparent" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#424242] mb-1">Category *</label>
                  <select name="category" required className="w-full px-3 py-2.5 rounded-[var(--radius-btn)] border border-[#e0e0e0] bg-white focus:outline-none focus:ring-2 focus:ring-[#000] focus:border-transparent">
                    <option value="">Select…</option>
                    <option value="premium">Premium</option>
                    <option value="normal">Normal</option>
                  </select>
                </div>
              </div>
              <div className="flex gap-3 px-6 py-4 border-t border-[#eee] bg-[#fafafa]">
                <button type="button" onClick={() => !isAdding && setShowVehicleModal(false)} disabled={isAdding} className="flex-1 py-2.5 rounded-[var(--radius-btn)] font-medium text-[#424242] bg-white border border-[#e0e0e0] hover:bg-[#f6f6f6] disabled:opacity-50">
                  Cancel
                </button>
                <button type="submit" disabled={isAdding} className="flex-1 py-2.5 rounded-[var(--radius-btn)] font-medium text-white bg-[#000] hover:bg-[#111] disabled:opacity-50 flex items-center justify-center gap-2">
                  {isAdding ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  {isAdding ? "Adding…" : "Add vehicle"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
