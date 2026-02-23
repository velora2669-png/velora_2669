# Route Optimization - Velora Mobitech

## Overview
This project solves the Velora Optimization Problem by providing an intelligent corporate mobility system capable of generating efficient employee transportation plans under real-world operational constraints. The system autonomously assigns employees to available vehicles and determines optimized pickup and drop-off routes. The primary objective is to minimize total travel distance, travel time, and operational cost while ensuring service feasibility and adaptability to enterprise-scale commute scenarios. The problem is modeled as a constrained vehicle routing and assignment optimization task, combining elements of the Vehicle Routing Problem with Time Windows (Vehicle Routing Problem with Time Windows) and fleet allocation.

## Features
* **Two-Stage Optimization Framework:** Separates global route construction from vehicle-level feasibility optimization to ensure scalable enterprise deployment.

* **Strict Hard Constraint Enforcement:** Ensures compliance with vehicle seating capacity, geographic reachability, earliest pickup times, and latest drop-off deadlines before schedule confirmation.

* **Penalty-Aware Soft Constraints:** Optimizes operational efficiency and employee comfort by applying weighted penalties for sharing preference violations, vehicle category mismatches, fleet scarcity, and excessive deadhead distances.

* **Multi-Tiered Relaxation Strategy:** Prevents systemic failure during infeasible scenarios by progressively relaxing secondary constraints to guarantee a fallback schedule.

* **Interactive Map UI with OSRM Integration:** Visualizes optimized routes, vehicle tracking, and pickup/drop-off locations using a React frontend integrated with OSRM.

## Architecture Overview

The core routing engine utilizes a scalable, two-stage optimization framework:

### Stage 1: Giant Tour Construction

The optimization begins by constructing a **Giant Tour**, a globally efficient ordering of employees independent of vehicle assignments.

* **Regret-k Heuristic:** Unassigned employees are incrementally inserted into the tour based on future insertion loss (*regret*) rather than immediate cost minimization, prioritizing difficult-to-place employees early.

* **2-Opt Local Search Optimization:** A time-constrained 2-opt improvement phase refines the tour by performing pairwise segment swaps that reduce total travel distance while preserving time-window feasibility.

---

### Stage 2: Optimal Route Partitioning

The Giant Tour is optimally divided into feasible vehicle trips using a **Dynamic Programming (DP) Split Algorithm**.

* The algorithm evaluates contiguous segments of the tour against hard constraints such as vehicle capacity, geographic reachability, and time windows.

* It computes the minimum-cost partition of the tour, ensuring the final set of vehicle routes minimizes operational cost while strictly maintaining constraint feasibility.

## Tech Stack

### Frontend

* **React.js:** Used for building interactive UI components and the operational dashboard.

---

### Backend

* **Python:** Core language for implementing optimization algorithms and data processing logic.
* **Django (6.0.2) + Django REST Framework:** Manages API endpoints, authentication, request handling, and backend orchestration.

---

### Maps & Routing

* **OSRM (Open Source Routing Machine):** Serves as the routing engine to compute real-world travel distances and time matrices.
* **Haversine Logic:** Applied for initial geographic clustering and approximate distance estimation before routing refinement.

## Installation and Setup

### Prerequisites

- **Python 3.11+**
- **Node.js**

---

### Backend Setup

1. Navigate to the backend directory:

```bash
cd backend
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
venv\Scripts\activate

```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run migrations and start the server:

```bash
python manage.py migrate
python manage.py runserver
```

---

### Frontend Setup

1. Navigate to the frontend directory:

```bash
cd website_frontend
```

2. Install dependencies:

```bash
npm install
```

3. Start the development server:

```bash
npm run dev
```

## Usage

1. **Data Preparation:**  
   Prepare an Excel/CSV file containing employee pickup locations, time windows, and vehicle fleet details.

2. **Upload:**  
   Use the **ExcelUpload** page to submit the data to the backend.

3. **Optimization:**  
   The backend processes the data through the Two-Stage Optimization Framework (Regret-k Heuristic → DP Split Algorithm).

4. **Review Results:**  
   View the generated routes, employee-to-vehicle assignments, and chronologically ordered trip objects (e.g., T001, T002, etc.) on the interactive map dashboard.

## Future Enhancements

* **Real-Time Traffic Integration:** Incorporate live traffic data into the `Eval_Segment_Cost` function to improve arrival time predictions and enhance real-world route accuracy.

## Conclusion

The Velora Optimization Engine successfully balances strict operational service-level agreements (SLAs) with employee comfort and fleet efficiency.  

By separating global routing from localized Dynamic Programming–based constraint validation, the platform delivers a robust and scalable solution capable of navigating the complex temporal and geographic realities of modern enterprise commuting.
