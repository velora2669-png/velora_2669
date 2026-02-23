import os
import tempfile
import json
import pandas as pd

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from route_optimizer.main import run_optimizer_from_excel


@csrf_exempt
@require_POST
def upload_and_optimize(request):
    """
    1. Receive Excel file from frontend OR testcase selection
    2. Save temporarily or use predefined testcase
    3. Run optimizer
    4. Return JSON result
    """

    temp_path = None
    should_cleanup = False

    # ------------- 1️⃣ Check for predefined testcase selection -------------
    testcase_name = request.POST.get("testcase_name")
    
    if testcase_name:
        # Use predefined testcase
        from pathlib import Path
        testcase_dir = Path(__file__).parent.parent / "route_optimizer" / "testcases"
        testcase_path = testcase_dir / testcase_name
        
        if not testcase_path.exists():
            return JsonResponse(
                {"status": "error", "message": f"Testcase {testcase_name} not found"},
                status=400
            )
        
        temp_path = str(testcase_path)
        should_cleanup = False
    elif "file" in request.FILES:
        # Handle file upload
        uploaded_file = request.FILES["file"]

        # Optional: validate extension
        if not uploaded_file.name.endswith(".xlsx"):
            return JsonResponse(
                {"status": "error", "message": "Only .xlsx files allowed"},
                status=400
            )

        # ------------- 2️⃣ Save Temporarily -------------
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_file:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)

            temp_path = temp_file.name
        
        should_cleanup = True
    else:
        return JsonResponse(
            {"status": "error", "message": "No file uploaded or testcase selected"},
            status=400
        )

    # ------------- 3️⃣ Run Optimizer -------------
    try:
        result = run_optimizer_from_excel(temp_path)

        # ------------- 4️⃣ Return JSON -------------
        

        return JsonResponse(
            json.loads(json.dumps({
                "status": "success",
                "data": result
            }, default=str))
        )


    except Exception as e:
            import traceback
            traceback.print_exc()  
            return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)

    finally:
        # ------------- Cleanup -------------
        if should_cleanup and temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except PermissionError:
                # If the optimizer JUST finished, Windows might need 
                # a split second to release the lock.
                pass


@csrf_exempt
@require_POST
def add_entity_and_reoptimize(request):
    """
    Add a new employee or vehicle to an existing testcase and re-run optimization
    
    Request format:
    - entity_type: "employee" or "vehicle"
    - testcase_name: name of the predefined testcase file
    - entity_data: JSON string of the new entity fields
    """
    
    temp_path = None

    def _parse_optional_json(raw_value, field_name):
        if raw_value is None or raw_value == "":
            return None
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in {field_name}")

    try:
        # Parse request data
        entity_type = request.POST.get("entity_type")
        testcase_name = request.POST.get("testcase_name")
        entity_data_str = request.POST.get("entity_data")
        added_employees_str = request.POST.get("added_employees")
        added_vehicles_str = request.POST.get("added_vehicles")
        
        if not testcase_name:
            return JsonResponse(
                {"status": "error", "message": "Missing required fields"},
                status=400
            )

        entity_data = _parse_optional_json(entity_data_str, "entity_data")
        added_employees = _parse_optional_json(added_employees_str, "added_employees")
        added_vehicles = _parse_optional_json(added_vehicles_str, "added_vehicles")

        if entity_data is not None and not isinstance(entity_data, dict):
            return JsonResponse(
                {"status": "error", "message": "entity_data must be a JSON object"},
                status=400,
            )

        if added_employees is not None and not isinstance(added_employees, list):
            return JsonResponse(
                {"status": "error", "message": "added_employees must be a JSON array"},
                status=400,
            )

        if added_vehicles is not None and not isinstance(added_vehicles, list):
            return JsonResponse(
                {"status": "error", "message": "added_vehicles must be a JSON array"},
                status=400,
            )

        if entity_data is None and not isinstance(added_employees, list) and not isinstance(added_vehicles, list):
            return JsonResponse(
                {"status": "error", "message": "No entity payload provided"},
                status=400,
            )
        
        # Validate entity type when single-entity payload is used
        if entity_data is not None and entity_type not in ["employee", "vehicle"]:
            return JsonResponse(
                {"status": "error", "message": "Invalid entity_type"},
                status=400
            )
        
        # Load the original testcase file
        from pathlib import Path
        testcase_dir = Path(__file__).parent.parent / "route_optimizer" / "testcases"
        testcase_path = testcase_dir / testcase_name
        
        if not testcase_path.exists():
            return JsonResponse(
                {"status": "error", "message": f"Testcase {testcase_name} not found"},
                status=400
            )
        
        # Read all sheets from the original testcase
        with pd.ExcelFile(testcase_path) as xl:
            employees_df = pd.read_excel(xl, "employees")
            vehicles_df = pd.read_excel(xl, "vehicles")
            metadata_df = pd.read_excel(xl, "metadata")
            baseline_df = pd.read_excel(xl, "baseline") if "baseline" in xl.sheet_names else None
        
        def _add_employee_to_frames(employee_payload):
            nonlocal employees_df, baseline_df

            employee_id = employee_payload.get("employee_id")
            baseline_cost = employee_payload.get("baseline_cost", None)
            baseline_time = employee_payload.get("baseline_time", None)

            employee_clean = {
                k: v for k, v in employee_payload.items()
                if k not in ["baseline_cost", "baseline_time"]
            }

            employees_df = pd.concat([employees_df, pd.DataFrame([employee_clean])], ignore_index=True)

            if baseline_cost is None or baseline_time is None or not employee_id:
                return

            import math
            try:
                baseline_cost_float = float(baseline_cost)
                baseline_time_float = float(baseline_time)

                if math.isnan(baseline_cost_float) or math.isnan(baseline_time_float):
                    return

                if baseline_df is None or baseline_df.empty:
                    baseline_df = pd.DataFrame([{
                        "employee_id": employee_id,
                        "baseline_cost": baseline_cost_float,
                        "baseline_time": baseline_time_float,
                    }])
                else:
                    cols = {str(col).strip().lower(): col for col in baseline_df.columns}
                    emp_id_col = cols.get("employee_id", "employee_id")
                    cost_col = cols.get("baseline_cost") or cols.get("cost") or "baseline_cost"
                    time_col = (
                        cols.get("baseline_time")
                        or cols.get("baseline_time_min")
                        or cols.get("time")
                        or cols.get("time_min")
                        or "baseline_time"
                    )

                    baseline_df = pd.concat([
                        baseline_df,
                        pd.DataFrame([{
                            emp_id_col: employee_id,
                            cost_col: baseline_cost_float,
                            time_col: baseline_time_float,
                        }]),
                    ], ignore_index=True)
            except (ValueError, TypeError):
                return

        # Prefer cumulative payloads when provided; fallback to single entity payload
        if isinstance(added_employees, list) or isinstance(added_vehicles, list):
            if isinstance(added_employees, list):
                for employee_payload in added_employees:
                    if isinstance(employee_payload, dict):
                        _add_employee_to_frames(employee_payload)

            if isinstance(added_vehicles, list):
                valid_vehicles = [v for v in added_vehicles if isinstance(v, dict)]
                if valid_vehicles:
                    vehicles_df = pd.concat([vehicles_df, pd.DataFrame(valid_vehicles)], ignore_index=True)
        elif entity_data is not None:
            if entity_type == "employee":
                _add_employee_to_frames(entity_data)
            elif entity_type == "vehicle":
                vehicles_df = pd.concat([vehicles_df, pd.DataFrame([entity_data])], ignore_index=True)

        # De-duplicate by IDs to keep latest payload when same entity is re-sent cumulatively
        if "employee_id" in employees_df.columns:
            employees_df = employees_df.drop_duplicates(subset=["employee_id"], keep="last")
        if "vehicle_id" in vehicles_df.columns:
            vehicles_df = vehicles_df.drop_duplicates(subset=["vehicle_id"], keep="last")
        if baseline_df is not None and not baseline_df.empty and "employee_id" in baseline_df.columns:
            baseline_df = baseline_df.drop_duplicates(subset=["employee_id"], keep="last")
        
        # Create a temporary file with the updated data
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx", mode="wb") as temp_file:
            temp_path = temp_file.name
        
        # Write all sheets to the new file
        with pd.ExcelWriter(temp_path, engine='openpyxl') as writer:
            employees_df.to_excel(writer, sheet_name="employees", index=False)
            vehicles_df.to_excel(writer, sheet_name="vehicles", index=False)
            metadata_df.to_excel(writer, sheet_name="metadata", index=False)
            if baseline_df is not None and not baseline_df.empty:
                baseline_df.to_excel(writer, sheet_name="baseline", index=False)
        
        # Run the optimizer with the updated data
        result = run_optimizer_from_excel(temp_path)
        
        return JsonResponse(
            json.loads(json.dumps({
                "status": "success",
                "data": result
            }, default=str))
        )
    
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error in add_entity_and_reoptimize: {error_traceback}")
        return JsonResponse({
            "status": "error",
            "message": str(e),
            "details": error_traceback
        }, status=500)
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
