# Velora Mobitech - Mobile App

Flutter mobile application for the Route Optimization platform.

## Prerequisites
- Flutter SDK (3.x or above)
- Android Studio / Xcode
- Android or iOS device/emulator

## Setup & Run

1. Install dependencies:
   flutter pub get

2. Update the backend URL in lib/upload_screen.dart:
   final uri = Uri.parse("http://YOUR_BACKEND_IP:8000/api/upload/");

3. Run the app:
   flutter run

## Project Structure

lib/
main.dart             - App entry point
upload_screen.dart    - Home screen with file upload
loading_screen.dart   - Loading state while backend processes
map_screen.dart       - Route map with optimization results

## Features
- Upload employee Excel data (xls, xlsx)
- View optimized routes on interactive map
- Cost comparison (baseline vs optimized)
- Per-trip breakdown with vehicle and time info
- Add employees and vehicles dynamically

## Dependencies
See pubspec.yaml for full list. Key packages:
- flutter_map - Map rendering
- latlong2 - Coordinate handling
- file_picker - Excel file upload
- http - Backend API calls