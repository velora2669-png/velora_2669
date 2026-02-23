import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

export default function Loader() {
  const location = useLocation();
  const navigate = useNavigate();
  const file = location.state?.file;

  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  // Convert minutes → HH:MM format
  const formatTime = (minutes) => {
    const hrs = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hrs.toString().padStart(2, "0")}:${mins
      .toString()
      .padStart(2, "0")}`;
  };

  useEffect(() => {
    if (!file) {
      navigate("/");
      return;
    }

    const uploadFile = async () => {
      const formData = new FormData();
      formData.append("file", file);

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
  }, [file, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="w-full max-w-4xl p-6">

        {/* Loading State */}
        {loading && (
          <div className="text-center">
            <h2 className="text-2xl font-semibold">Optimizing Routes...</h2>
            <p className="text-gray-500 mt-2">Please wait...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="text-center text-red-600">
            <h2 className="text-xl font-semibold">Upload Failed</h2>
            <p className="mt-2">{error}</p>
            <button
              onClick={() => navigate("/")}
              className="mt-4 px-4 py-2 bg-red-500 text-white rounded-lg"
            >
              Go Back
            </button>
          </div>
        )}

        {/* Result State */}
        {result && (
          <div className="space-y-8">

            {/* Total Cost Card */}
            <div className="bg-white p-6 rounded-2xl shadow-lg text-center">
              <h2 className="text-xl font-semibold">
                Total Optimization Cost
              </h2>
              <p className="text-3xl font-bold text-blue-600 mt-2">
                {result.total_cost.toFixed(2)}
              </p>
            </div>

            {/* Trips Section */}
            <div>
              <h3 className="text-xl font-semibold mb-4">Trips</h3>
              <div className="grid md:grid-cols-2 gap-4">
                {result.trips.map((trip) => (
                  <div
                    key={trip.trip_id}
                    className="bg-white p-4 rounded-xl shadow"
                  >
                    <p><strong>Trip ID:</strong> {trip.trip_id}</p>
                    <p>
                      <strong>Employees:</strong>{" "}
                      {trip.employees.join(", ")}
                    </p>
                    <p>
                      <strong>Cost:</strong> {trip.cost.toFixed(2)}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Schedule Section */}
            <div>
              <h3 className="text-xl font-semibold mb-4">
                Vehicle Schedule
              </h3>
              <div className="space-y-4">
                {result.schedule.map((item, index) => (
                  <div
                    key={index}
                    className="bg-white p-4 rounded-xl shadow"
                  >
                    <div className="grid md:grid-cols-2 gap-2">
                      <p><strong>Vehicle:</strong> {item.vehicle_id}</p>
                      <p><strong>Trip:</strong> {item.trip_id}</p>
                      <p>
                        <strong>Employees:</strong>{" "}
                        {item.employees.join(", ")}
                      </p>
                      <p>
                        <strong>Departure:</strong>{" "}
                        {formatTime(item.depart_min)}
                      </p>
                      <p>
                        <strong>Arrival:</strong>{" "}
                        {formatTime(item.arrival_min)}
                      </p>
                      <p>
                        <strong>Cost:</strong> {item.cost.toFixed(2)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>
        )}
      </div>
    </div>
  );
}
