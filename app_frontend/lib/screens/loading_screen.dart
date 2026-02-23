import 'dart:convert';
import 'package:flutter/material.dart';
import 'map_screen.dart';

class LoadingScreen extends StatefulWidget {
  final Future<String> backendCall;

  const LoadingScreen({super.key, required this.backendCall});

  @override
  State<LoadingScreen> createState() => _LoadingScreenState();
}

class _LoadingScreenState extends State<LoadingScreen> {
  @override
  void initState() {
    super.initState();
    _waitForBackend();
  }

  Future<void> _waitForBackend() async {
    try {
      final responseBody = await widget.backendCall;

      print("==========================================");
      print("RAW BACKEND RESPONSE:");
      print(responseBody);
      print("==========================================");

      // Parse JSON
      Map<String, dynamic> parsedResponse;
      try {
        final decoded = jsonDecode(responseBody);

        if (decoded is! Map<String, dynamic>) {
          throw Exception("Response is not a JSON object");
        }

        parsedResponse = decoded;
      } catch (e) {
        throw Exception("Invalid JSON response: $e");
      }

      print("Response keys: ${parsedResponse.keys.toList()}");

      // Handle different response formats
      Map<String, dynamic> backendResponse;

      // Check if response has 'data' field (nested format)
      if (parsedResponse.containsKey('data')) {
        print("✓ Detected nested response format (data field found)");

        final dataField = parsedResponse['data'];
        if (dataField == null) {
          throw Exception("'data' field is null");
        }

        if (dataField is! Map<String, dynamic>) {
          throw Exception("'data' field is not an object");
        }

        backendResponse = dataField;
      }
      // Check if response has 'employees' directly (flat format)
      else if (parsedResponse.containsKey('employees')) {
        print("✓ Detected flat response format");
        backendResponse = parsedResponse;
      }
      // Unknown format
      else {
        throw Exception(
            "Unknown response format. Keys found: ${parsedResponse.keys.toList()}\n"
                "Expected either 'employees' or 'data' field"
        );
      }

      // Validate required fields exist
      if (!backendResponse.containsKey('employees')) {
        throw Exception(
            "Response missing 'employees' field after parsing. "
                "Keys found: ${backendResponse.keys.toList()}"
        );
      }

      if (backendResponse['employees'] == null) {
        throw Exception("'employees' field is null");
      }

      if (backendResponse['employees'] is! List) {
        throw Exception(
            "'employees' field is not a list. "
                "Type: ${backendResponse['employees'].runtimeType}"
        );
      }

      if (!backendResponse.containsKey('schedule')) {
        throw Exception(
            "Response missing 'schedule' field. "
                "Keys found: ${backendResponse.keys.toList()}"
        );
      }

      if (backendResponse['schedule'] == null) {
        throw Exception("'schedule' field is null");
      }

      if (backendResponse['schedule'] is! List) {
        throw Exception(
            "'schedule' field is not a list. "
                "Type: ${backendResponse['schedule'].runtimeType}"
        );
      }

      final employeesList = backendResponse['employees'] as List;
      final scheduleList = backendResponse['schedule'] as List;

      print("✓ Validation passed!");
      print("✓ Employees count: ${employeesList.length}");
      print("✓ Schedule count: ${scheduleList.length}");

      if (employeesList.isEmpty) {
        throw Exception("No employees in response");
      }

      if (scheduleList.isEmpty) {
        throw Exception("No schedule/trips in response");
      }

      if (!mounted) return;

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => MapScreen(result: backendResponse),
        ),
      );
    } catch (e) {
      print("==========================================");
      print("ERROR in _waitForBackend:");
      print(e);
      print("==========================================");

      if (!mounted) return;

      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (context) => AlertDialog(
          title: const Text("Upload Failed"),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  "Failed to process route data:",
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                Text(
                  "$e",
                  style: const TextStyle(fontSize: 12),
                ),
                const SizedBox(height: 16),
                const Text(
                  "Check the console logs for the full backend response.",
                  style: TextStyle(fontSize: 11, color: Colors.grey),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(context); // Close dialog
                Navigator.pop(context); // Go back to upload screen
              },
              child: const Text("OK"),
            ),
          ],
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: const [
            CircularProgressIndicator(color: Colors.white),
            SizedBox(height: 20),
            Text(
              "Optimizing routes...\nPlease wait",
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white, fontSize: 16),
            ),
          ],
        ),
      ),
    );
  }
}
