import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.files.storage import default_storage

ALLOWED_EXTS = {".xlsx", ".xls"}  # CSV not allowed

@csrf_exempt
def upload_excel(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    file = request.FILES.get("file")
    if not file:
        return JsonResponse({"error": "No file provided (field name must be 'file')"}, status=400)

    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_EXTS:
        return JsonResponse({"error": "Only .xlsx or .xls files allowed"}, status=400)

    # Save to media/uploads/
    save_path = f"uploads/{file.name}"
    stored_path = default_storage.save(save_path, file)

    return JsonResponse({
        "message": "Excel uploaded successfully",
        "path": stored_path,
        "url": request.build_absolute_uri(settings.MEDIA_URL + stored_path)
    }, status=201)

