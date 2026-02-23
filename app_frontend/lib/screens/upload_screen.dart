import 'dart:io';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'loading_screen.dart';

/* ================= COLORS ================= */
const Color kOlive = Color(0xFF4A5240);
const Color kOliveLight = Color(0xFF6B7560);
const Color kBg = Color(0xFFF5F0E8);
const Color kCard = Color(0xFFFFFFFF);
const Color kText = Color(0xFF1A1A1A);
const Color kSubText = Color(0xFF6B7280);
const Color kBorder = Color(0xFFE5E7EB);

/* ================= SCREEN ================= */
class UploadScreen extends StatefulWidget {
  const UploadScreen({super.key});

  @override
  State<UploadScreen> createState() => _UploadScreenState();
}

class _UploadScreenState extends State<UploadScreen> {
  final ScrollController _scrollController = ScrollController();
  String? _selectedFileName;
  File? _selectedFile;

  Future<void> pickExcelFile(BuildContext context) async {
    FilePickerResult? result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['xls', 'xlsx', 'csv'],
    );

    if (result == null) return;

    setState(() {
      _selectedFileName = result.files.single.name;
      _selectedFile = File(result.files.single.path!);
    });
  }

  void _uploadData(BuildContext context) {
    if (_selectedFile == null) {
      pickExcelFile(context);
      return;
    }

    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => LoadingScreen(
          backendCall: _uploadFileToBackend(_selectedFile!),
        ),
      ),
    );
  }

  Future<String> _uploadFileToBackend(File file) async {
    try {
      // IMPORTANT: Replace this IP with your backend IP
      final uri = Uri.parse("http://192.168.123.94:8000/api/upload/");
      final request = http.MultipartRequest('POST', uri);
      request.files.add(
        await http.MultipartFile.fromPath('file', file.path),
      );

      final response = await request.send();
      final responseBody = await response.stream.bytesToString();

      if (response.statusCode != 200) {
        throw Exception(
            "Upload failed with status ${response.statusCode}\nResponse: $responseBody");
      }

      try {
        jsonDecode(responseBody);
      } catch (e) {
        throw Exception("Invalid JSON response from server: $responseBody");
      }

      return responseBody;
    } catch (e) {
      rethrow;
    }
  }

  void scrollToTop() {
    _scrollController.animateTo(0,
        duration: const Duration(milliseconds: 600), curve: Curves.easeOut);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SingleChildScrollView(
        controller: _scrollController,
        child: Column(
          children: [
            _buildHeroSection(context),
            _buildFeaturesSection(),
            _buildHowItWorksSection(),
            _buildCtaSection(context),
          ],
        ),
      ),
    );
  }

  /* ── HERO ── */
  Widget _buildHeroSection(BuildContext context) {
    return SizedBox(
      height: MediaQuery.of(context).size.height * 0.85,
      child: Stack(
        children: [
          // CARTO map background
          FlutterMap(
            options: const MapOptions(
              initialCenter: LatLng(12.9716, 77.5946),
              initialZoom: 12,
              interactionOptions:
              InteractionOptions(flags: InteractiveFlag.none),
            ),
            children: [
              TileLayer(
                urlTemplate:
                'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
                subdomains: const ['a', 'b', 'c', 'd'],
                userAgentPackageName: 'com.example.kriti_project',
              ),
            ],
          ),

          // Semi-transparent overlay
          Container(color: Colors.white.withOpacity(0.35)),

          // Content centered
          Center(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Container(
                constraints: const BoxConstraints(maxWidth: 520),
                padding:
                const EdgeInsets.symmetric(horizontal: 36, vertical: 44),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.92),
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.08),
                      blurRadius: 32,
                      offset: const Offset(0, 8),
                    )
                  ],
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Badge
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 12, vertical: 5),
                      decoration: BoxDecoration(
                        color: kOlive.withOpacity(0.08),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                            color: kOlive.withOpacity(0.2), width: 1),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 7,
                            height: 7,
                            decoration: BoxDecoration(
                              color: kOlive,
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            'Optimization Engine Active',
                            style: TextStyle(
                              color: kOlive,
                              fontSize: 11,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),

                    // Title
                    Text.rich(
                      TextSpan(
                        children: [
                          const TextSpan(text: 'Optimizing the '),
                          TextSpan(
                            text: 'Future',
                            style: TextStyle(color: kOlive),
                          ),
                          const TextSpan(text: ' of\nthe Commute'),
                        ],
                        style: const TextStyle(
                          fontSize: 28,
                          fontWeight: FontWeight.bold,
                          color: kText,
                          height: 1.25,
                        ),
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 12),

                    Text(
                      'Intelligent fleet routing that cuts costs, saves time, and simplifies employee transportation — all from a single upload.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: kSubText,
                        fontSize: 13.5,
                        height: 1.55,
                      ),
                    ),
                    const SizedBox(height: 28),

                    // File picker row
                    GestureDetector(
                      onTap: () => pickExcelFile(context),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 11),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          border: Border.all(color: kBorder),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 10, vertical: 5),
                              decoration: BoxDecoration(
                                color: const Color(0xFFF3F4F6),
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(color: kBorder),
                              ),
                              child: const Text(
                                'Browse...',
                                style: TextStyle(
                                    fontSize: 12, color: kText),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                _selectedFileName ?? 'No file selected',
                                style: TextStyle(
                                  fontSize: 13,
                                  color: _selectedFileName != null
                                      ? kText
                                      : kSubText,
                                ),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),

                    // Upload button
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: () => _uploadData(context),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: kOlive,
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10)),
                          elevation: 0,
                        ),
                        child: const Text(
                          'Upload Data',
                          style: TextStyle(
                              color: Colors.white,
                              fontSize: 15,
                              fontWeight: FontWeight.w600),
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),

                    Text(
                      'Supported formats: xls, xlsx',
                      style: TextStyle(
                          fontSize: 11,
                          color: kSubText.withOpacity(0.7)),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  /* ── FEATURES ── */
  Widget _buildFeaturesSection() {
    final features = [
      (Icons.people_alt_outlined, 'Smart Seat Matching',
      'Automatically pairs employees with the best vehicle based on seating capacity and their personal preferences.'),
      (Icons.alt_route, 'Fastest Route Planning',
      'Creates the most efficient pick-up and drop-off paths to save time and reduce driving distance.'),
      (Icons.bar_chart, 'Schedule Sync',
      'Organizes trips around specific employee work hours and vehicle availability times.'),
      (Icons.savings_outlined, 'Cost Savings',
      'Compares your optimized plan against standard taxi prices to show exactly how much money you saved.'),
      (Icons.upload_file_outlined, 'Easy File Upload',
      'Lets you quickly upload an Excel sheet of trip requests and get an optimized plan in seconds.'),
      (Icons.map_outlined, 'Trip Map Preview',
      'Displays all employee locations and your planned routes clearly on a real-world map.'),
    ];

    return Container(
      color: kBg,
      padding: const EdgeInsets.symmetric(vertical: 48, horizontal: 20),
      child: Column(
        children: [
          Text.rich(
            TextSpan(
              children: [
                const TextSpan(text: 'Everything You Need to '),
                TextSpan(
                    text: 'Optimize',
                    style: TextStyle(color: kOlive)),
              ],
              style: const TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                  color: kText),
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          Text(
            'A complete suite of tools to transform employee transportation from chaos into clarity.',
            textAlign: TextAlign.center,
            style: TextStyle(color: kSubText, fontSize: 13, height: 1.5),
          ),
          const SizedBox(height: 28),
          Wrap(
            spacing: 14,
            runSpacing: 14,
            alignment: WrapAlignment.center,
            children: features.map((f) {
              final cardWidth =
                  (MediaQuery.of(context).size.width - 54) / 2;
              return SizedBox(
                width: cardWidth,
                height: 188,
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: kCard,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: kBorder.withOpacity(0.6)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(f.$1, size: 22, color: kOlive),
                      const SizedBox(height: 10),
                      Text(f.$2,
                          style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 13,
                              color: kText)),
                      const SizedBox(height: 6),
                      Expanded(
                        child: Text(
                          f.$3,
                          style: TextStyle(
                              fontSize: 11.5,
                              color: kSubText,
                              height: 1.4),
                          overflow: TextOverflow.fade,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  /* ── HOW IT WORKS ── */
  Widget _buildHowItWorksSection() {
    final steps = [
      ('1', Icons.upload_outlined, 'Upload Data',
      'Push optimized routes to drivers and track everything from one dashboard.'),
      ('2', Icons.settings_outlined, 'Engine Optimizes',
      'Push optimized routes to drivers and track everything from one dashboard.'),
      ('3', Icons.rocket_launch_outlined, 'Deploy Routes',
      'Push optimized routes to drivers and track everything from one dashboard.'),
    ];

    return Stack(
      children: [
        // Map fills exactly the space the content needs
        Positioned.fill(
          child: FlutterMap(
            options: const MapOptions(
              initialCenter: LatLng(12.9516, 77.6046),
              initialZoom: 13,
              interactionOptions:
              InteractionOptions(flags: InteractiveFlag.none),
            ),
            children: [
              TileLayer(
                urlTemplate:
                'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
                subdomains: const ['a', 'b', 'c', 'd'],
                userAgentPackageName: 'com.example.kriti_project',
              ),
            ],
          ),
        ),
        Positioned.fill(
          child: Container(color: Colors.white.withOpacity(0.65)),
        ),
        // Content drives the height
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 36),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'How It Works',
                style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                    color: kText),
              ),
              const SizedBox(height: 6),
              Text(
                'Three simple steps from raw data to optimized routes.',
                style: TextStyle(color: kSubText, fontSize: 12),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 28),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: steps.map((s) {
                  return Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 6),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            s.$1,
                            style: TextStyle(
                              fontSize: 48,
                              fontWeight: FontWeight.bold,
                              color: kBorder.withOpacity(0.9),
                              height: 1,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            s.$3,
                            style: const TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 13,
                                color: kText),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 6),
                          Text(
                            s.$4,
                            style: TextStyle(
                                fontSize: 11,
                                color: kSubText,
                                height: 1.45),
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ],
    );
  }

  /* ── CTA ── */
  Widget _buildCtaSection(BuildContext context) {
    return Stack(
      children: [
        // Map fills exactly the space content needs
        Positioned.fill(
          child: FlutterMap(
            options: const MapOptions(
              initialCenter: LatLng(12.9616, 77.5846),
              initialZoom: 13,
              interactionOptions:
              InteractionOptions(flags: InteractiveFlag.none),
            ),
            children: [
              TileLayer(
                urlTemplate:
                'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
                subdomains: const ['a', 'b', 'c', 'd'],
                userAgentPackageName: 'com.example.kriti_project',
              ),
            ],
          ),
        ),
        Positioned.fill(
          child: Container(color: Colors.white.withOpacity(0.5)),
        ),
        // Content drives the height
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Container(
            width: double.infinity,
            padding:
            const EdgeInsets.symmetric(horizontal: 28, vertical: 32),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.95),
              borderRadius: BorderRadius.circular(20),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.07),
                  blurRadius: 24,
                  offset: const Offset(0, 6),
                )
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.bar_chart, size: 28, color: kOlive),
                const SizedBox(height: 12),
                const Text(
                  'Ready to optimize your fleet?',
                  style: TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.bold,
                      color: kText),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 8),
                Text(
                  'Upload your data and see optimized routes, cost savings, and fleet utilization instantly.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                      color: kSubText, fontSize: 12.5, height: 1.5),
                ),
                const SizedBox(height: 20),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: scrollToTop,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: kOlive,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10)),
                      elevation: 0,
                    ),
                    child: const Text(
                      'Get Started Now',
                      style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                          fontSize: 14),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
