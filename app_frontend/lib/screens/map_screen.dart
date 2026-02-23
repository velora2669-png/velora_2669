import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:http/http.dart' as http;

/* ================= COLORS ================= */
const Color kOlive = Color(0xFF4A5240);
const Color kText = Color(0xFF1A1A1A);
const Color kSubText = Color(0xFF6B7280);
const Color kBorder = Color(0xFFE5E7EB);
const Color kGrey = Color(0xFFF6F6F6);
const Color kGreen = Color(0xFF16A34A);
const Color kRed = Color(0xFFDC2626);

const List<Color> kRouteColors = [
  Color(0xFFE11D48),
  Color(0xFF2563EB),
  Color(0xFF16A34A),
  Color(0xFFF97316),
  Color(0xFF7C3AED),
  Color(0xFF0891B2),
  Color(0xFF65A30D),
  Color(0xFFD97706),
  Color(0xFF0D9488),
  Color(0xFF9333EA),
];

/* ================= SCREEN ================= */
class MapScreen extends StatefulWidget {
  final Map<String, dynamic> result;

  const MapScreen({super.key, required this.result});

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  final MapController _mapController = MapController();
  final List<Marker> _markers = [];
  final List<Polyline> _polylines = [];

  bool _isLoading = true;
  String? _errorMessage;
  bool _sidebarOpen = true;
  bool _showRoutes = true;
  bool _tripsExpanded = false;
  int? _selectedTripIndex;

  LatLng _initialPosition = const LatLng(12.9716, 77.5946);

  // Parsed data
  List _employees = [];
  List _schedule = [];
  List _trips = [];
  double _totalCost = 0;
  Map<String, dynamic> _costComparison = {};
  List _employeeCostComparison = [];
  double _baselineTotal = 0;
  double _optimizedTotal = 0;
  double _savingsTotal = 0;

  @override
  void initState() {
    super.initState();
    _parseResult();
    _initializeMap();
  }

  void _parseResult() {
    final r = widget.result;
    _employees = r['employees'] ?? [];
    _schedule = r['schedule'] ?? [];
    _trips = r['trips'] ?? _schedule;
    _totalCost = (r['total_cost'] as num?)?.toDouble() ?? 0;
    _costComparison = (r['cost_comparison'] as Map<String, dynamic>?) ?? {};
    _employeeCostComparison =
        (_costComparison['employees'] as List?) ?? [];
    _baselineTotal =
        ((_costComparison['baseline_total']) as num?)?.toDouble() ?? 0;
    _optimizedTotal =
        ((_costComparison['optimized_total']) as num?)?.toDouble() ?? 0;
    _savingsTotal =
        ((_costComparison['savings_total']) as num?)?.toDouble() ?? 0;
  }

  Future<void> _initializeMap() async {
    try {
      if (_employees.isEmpty || _schedule.isEmpty) {
        throw Exception("No data available");
      }

      final firstEmp = _employees[0];
      if (firstEmp['drop_lat'] != null && firstEmp['drop_lng'] != null) {
        _initialPosition = LatLng(
          (firstEmp['drop_lat'] as num).toDouble(),
          (firstEmp['drop_lng'] as num).toDouble(),
        );
      }

      // Depot marker
      _markers.add(Marker(
        point: _initialPosition,
        width: 36,
        height: 36,
        child: _DepotMarker(),
      ));

      // Employee markers
      for (final emp in _employees) {
        if (emp == null) continue;
        final lat = emp['pickup_lat'];
        final lng = emp['pickup_lng'];
        if (lat == null || lng == null) continue;

        _markers.add(Marker(
          point: LatLng((lat as num).toDouble(), (lng as num).toDouble()),
          width: 28,
          height: 28,
          child: _EmployeeMarker(),
        ));
      }

      await _buildRoutes();

      if (mounted) setState(() => _isLoading = false);
    } catch (e) {
      if (mounted) setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _buildRoutes() async {
    for (int i = 0; i < _schedule.length; i++) {
      try {
        final trip = _schedule[i];
        if (trip == null || trip['employees'] == null) continue;

        final tripEmployees = trip['employees'] as List? ?? [];
        if (tripEmployees.isEmpty) continue;

        final coords = <LatLng>[];

        for (final empId in tripEmployees) {
          try {
            final emp = _employees.firstWhere(
                  (e) =>
              e != null &&
                  e['employee_id']?.toString() == empId?.toString(),
            );
            if (emp != null &&
                emp['pickup_lat'] != null &&
                emp['pickup_lng'] != null) {
              coords.add(LatLng(
                (emp['pickup_lat'] as num).toDouble(),
                (emp['pickup_lng'] as num).toDouble(),
              ));
            }
          } catch (_) {}
        }

        coords.add(_initialPosition);
        if (coords.length < 2) continue;

        final osrmCoords =
        coords.map((c) => "${c.longitude},${c.latitude}").join(";");
        final url =
            "https://router.project-osrm.org/route/v1/driving/$osrmCoords?overview=full&geometries=geojson";

        final res = await http.get(Uri.parse(url));
        if (res.statusCode != 200) continue;

        final data = jsonDecode(res.body);
        final geometry = data['routes']?[0]?['geometry'];
        if (geometry == null) continue;

        final points = (geometry['coordinates'] as List)
            .map((p) =>
            LatLng((p[1] as num).toDouble(), (p[0] as num).toDouble()))
            .toList();

        _polylines.add(Polyline(
          points: points,
          color: kRouteColors[i % kRouteColors.length],
          strokeWidth: 4.0,
        ));
      } catch (_) {}
    }
  }

  /* ── Helpers ── */
  String _formatTime(dynamic min) {
    if (min == null) return '--:--';
    final n = (min as num).toDouble();
    if (!n.isFinite) return '--:--';
    final total = n.round().clamp(0, 1440 * 2);
    final h = total ~/ 60;
    final m = total % 60;
    return '${h.toString().padLeft(2, '0')}:${m.toString().padLeft(2, '0')}';
  }

  Map<String, dynamic>? _getEmployeeTripInfo(String empId) {
    for (final trip in _schedule) {
      final emps = trip['employees'] as List? ?? [];
      if (emps.any((e) => e?.toString() == empId)) {
        return {
          'vehicle_id': trip['vehicle_id'],
          'trip_id': trip['trip_id'],
          'depart': _formatTime(trip['depart_min']),
          'arrival': _formatTime(trip['arrival_min']),
        };
      }
    }
    return null;
  }

  double get _savingsPct =>
      _baselineTotal > 0 ? (_savingsTotal / _baselineTotal) * 100 : 0;

  /* ─────────── BUILD ─────────── */
  @override
  Widget build(BuildContext context) {
    if (_errorMessage != null) return _buildError();
    if (_isLoading) return _buildLoading();

    return Scaffold(
      backgroundColor: kGrey,
      body: Row(
        children: [
          // ── Sidebar ──
          AnimatedContainer(
            duration: const Duration(milliseconds: 280),
            curve: Curves.easeOut,
            width: _sidebarOpen ? 340 : 0,
            child: _sidebarOpen ? _buildSidebar() : const SizedBox.shrink(),
          ),

          // ── Map ──
          Expanded(child: _buildMap()),
        ],
      ),
    );
  }

  /* ── SIDEBAR ── */
  Widget _buildSidebar() {
    return Container(
      color: Colors.white,
      child: Column(
        children: [
          // Header
          SafeArea(
            bottom: false,
            child: Container(
              padding: const EdgeInsets.fromLTRB(18, 14, 10, 14),
              decoration: const BoxDecoration(
                  border: Border(bottom: BorderSide(color: kBorder))),
              child: Row(
                children: [
                  const Text('Optimization',
                      style: TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.bold,
                          color: kText)),
                  const Spacer(),
                  IconButton(
                    icon: const Icon(Icons.chevron_left, color: kSubText),
                    onPressed: () =>
                        setState(() => _sidebarOpen = false),
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                  ),
                ],
              ),
            ),
          ),

          // Scrollable content
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildActionButtons(),
                  const SizedBox(height: 14),
                  _buildSummaryCard(),
                  const SizedBox(height: 14),
                  _buildCostComparisonCard(),
                  const SizedBox(height: 14),
                  _buildTripsSection(),
                  const SizedBox(height: 14),
                  _buildAddEntityButtons(),
                  const SizedBox(height: 14),
                  _buildUploadNewButton(),
                  const SizedBox(height: 20),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionButtons() {
    return Row(
      children: [
        Expanded(
          child: ElevatedButton.icon(
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                    content: Text('Export feature coming soon'),
                    duration: Duration(seconds: 2)),
              );
            },
            icon: const Icon(Icons.download, size: 16, color: Colors.white),
            label: const Text('Export Excel',
                style: TextStyle(color: Colors.white, fontSize: 13)),
            style: ElevatedButton.styleFrom(
              backgroundColor: kText,
              padding: const EdgeInsets.symmetric(vertical: 11),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10)),
              elevation: 0,
            ),
          ),
        ),
        const SizedBox(width: 8),
        OutlinedButton.icon(
          onPressed: () => setState(() => _showRoutes = !_showRoutes),
          icon: Icon(Icons.route,
              size: 16, color: _showRoutes ? kText : kSubText),
          label: Text(_showRoutes ? 'Hide routes' : 'Show routes',
              style: TextStyle(
                  color: _showRoutes ? kText : kSubText, fontSize: 12)),
          style: OutlinedButton.styleFrom(
            padding:
            const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10)),
            side: const BorderSide(color: kBorder),
          ),
        ),
      ],
    );
  }

  Widget _buildSummaryCard() {
    return _sectionCard(
      label: 'SUMMARY',
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Total cost',
                    style: TextStyle(fontSize: 11, color: kSubText)),
                const SizedBox(height: 2),
                Text('\$${_totalCost.toStringAsFixed(2)}',
                    style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                        color: kText)),
              ],
            ),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Trips',
                    style: TextStyle(fontSize: 11, color: kSubText)),
                const SizedBox(height: 2),
                Text('${_trips.length}',
                    style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                        color: kText)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCostComparisonCard() {
    return _sectionCard(
      label: 'COST COMPARISON',
      child: Column(
        children: [
          _costRow('Baseline',
              '\$${_baselineTotal.toStringAsFixed(2)}', kText),
          const SizedBox(height: 6),
          _costRow('Optimized',
              '\$${_optimizedTotal.toStringAsFixed(2)}', kText),
          const Divider(height: 16, color: kBorder),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Savings',
                  style: TextStyle(
                      fontSize: 13, color: kSubText)),
              Text(
                '\$${_savingsTotal.abs().toStringAsFixed(2)} '
                    '(${_savingsPct.abs().toStringAsFixed(1)}%) '
                    '${_savingsTotal >= 0 ? 'saved' : 'increase'}',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: _savingsTotal >= 0 ? kGreen : kRed,
                ),
              ),
            ],
          ),

          if (_employeeCostComparison.isNotEmpty) ...[
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerLeft,
              child: Text('Per employee',
                  style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: kSubText)),
            ),
            const SizedBox(height: 6),
            Container(
              constraints: const BoxConstraints(maxHeight: 160),
              decoration: BoxDecoration(
                border: Border.all(color: kBorder),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Header
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 10, vertical: 7),
                    decoration: const BoxDecoration(
                        color: Color(0xFFFAFAFA),
                        borderRadius: BorderRadius.vertical(
                            top: Radius.circular(8))),
                    child: Row(
                      children: [
                        _tableCell('ID', flex: 2, header: true),
                        _tableCell('Base', header: true),
                        _tableCell('Opt', header: true),
                        _tableCell('Save %', header: true),
                      ],
                    ),
                  ),
                  Flexible(
                    child: ListView.builder(
                      padding: EdgeInsets.zero,
                      shrinkWrap: true,
                      itemCount: _employeeCostComparison.length,
                      itemBuilder: (ctx, i) {
                        final row = _employeeCostComparison[i];
                        final base =
                            (row['baseline_cost'] as num?)?.toDouble() ??
                                0;
                        final opt =
                            (row['optimized_cost'] as num?)?.toDouble() ??
                                0;
                        final sav =
                            (row['savings'] as num?)?.toDouble() ?? 0;
                        final pct = base > 0
                            ? (sav / base * 100).toStringAsFixed(1)
                            : '0.0';
                        return Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 10, vertical: 6),
                          color: i % 2 == 0
                              ? Colors.white
                              : const Color(0xFFFBFBFB),
                          child: Row(
                            children: [
                              _tableCell(
                                  row['employee_id']?.toString() ?? '--',
                                  flex: 2),
                              _tableCell(
                                  '\$${base.toStringAsFixed(2)}'),
                              _tableCell(
                                  '\$${opt.toStringAsFixed(2)}'),
                              Expanded(
                                child: Text(
                                  '$pct%',
                                  textAlign: TextAlign.right,
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                    color:
                                    sav >= 0 ? kGreen : kRed,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _tableCell(String text,
      {int flex = 1, bool header = false}) {
    return Expanded(
      flex: flex,
      child: Text(
        text,
        textAlign: TextAlign.right,
        style: TextStyle(
          fontSize: 11,
          fontWeight: header ? FontWeight.w600 : FontWeight.normal,
          color: header ? kSubText : kText,
        ),
      ),
    );
  }

  Widget _costRow(String label, String value, Color valueColor) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: TextStyle(fontSize: 13, color: kSubText)),
        Text(value,
            style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: valueColor)),
      ],
    );
  }

  Widget _buildTripsSection() {
    final visibleTrips =
    _tripsExpanded ? _schedule : _schedule.take(4).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text('TRIPS',
                style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: kSubText,
                    letterSpacing: 0.5)),
            GestureDetector(
              onTap: () => setState(() => _selectedTripIndex = null),
              child: Text('Clear Filter',
                  style: TextStyle(
                      fontSize: 12,
                      color: kOlive,
                      fontWeight: FontWeight.w500)),
            ),
          ],
        ),
        const SizedBox(height: 8),
        ...visibleTrips.asMap().entries.map((entry) {
          final i = entry.key;
          final trip = entry.value;
          final color = kRouteColors[i % kRouteColors.length];
          final isSelected = _selectedTripIndex == i;
          final empList = (trip['employees'] as List? ?? []).join(', ');

          return GestureDetector(
            onTap: () => setState(() {
              _selectedTripIndex = i;
              _showRoutes = true;
            }),
            child: Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: isSelected
                    ? Color.fromARGB(
                    16,
                    (color.value >> 16 & 0xFF),
                    (color.value >> 8 & 0xFF),
                    (color.value & 0xFF))
                    : Colors.white,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                    color: isSelected ? color : kBorder,
                    width: isSelected ? 1.5 : 1),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                              color: color, shape: BoxShape.circle)),
                      const SizedBox(width: 8),
                      Text(trip['vehicle_id']?.toString() ?? '--',
                          style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 13,
                              color: kText)),
                      const SizedBox(width: 6),
                      Text('(${trip['trip_id'] ?? ''})',
                          style:
                          TextStyle(fontSize: 11, color: kSubText)),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Icon(Icons.person_outline,
                          size: 13, color: kSubText),
                      const SizedBox(width: 4),
                      Expanded(
                        child: Text(empList,
                            style: TextStyle(
                                fontSize: 12, color: kSubText),
                            overflow: TextOverflow.ellipsis),
                      ),
                    ],
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '${_formatTime(trip['depart_min'])} → ${_formatTime(trip['arrival_min'])}',
                    style: TextStyle(fontSize: 11, color: kSubText),
                  ),
                ],
              ),
            ),
          );
        }),

        if (_schedule.length > 4)
          GestureDetector(
            onTap: () => setState(() => _tripsExpanded = !_tripsExpanded),
            child: Padding(
              padding: const EdgeInsets.only(top: 2),
              child: Center(
                child: Text(
                  _tripsExpanded ? 'Show Less' : 'Show All Trips',
                  style: TextStyle(
                      color: kOlive,
                      fontSize: 13,
                      fontWeight: FontWeight.w500),
                ),
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildAddEntityButtons() {
    return Row(
      children: [
        Expanded(
          child: ElevatedButton.icon(
            onPressed: () => _showEmployeeModal(),
            icon: const Icon(Icons.person, size: 16, color: Colors.white),
            label: const Text('Employee',
                style: TextStyle(color: Colors.white, fontSize: 13)),
            style: ElevatedButton.styleFrom(
              backgroundColor: kText,
              padding: const EdgeInsets.symmetric(vertical: 11),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10)),
              elevation: 0,
            ),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: ElevatedButton.icon(
            onPressed: () => _showVehicleModal(),
            icon: const Icon(Icons.local_shipping,
                size: 16, color: Colors.white),
            label: const Text('Vehicle',
                style: TextStyle(color: Colors.white, fontSize: 13)),
            style: ElevatedButton.styleFrom(
              backgroundColor: kText,
              padding: const EdgeInsets.symmetric(vertical: 11),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10)),
              elevation: 0,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildUploadNewButton() {
    return SizedBox(
      width: double.infinity,
      child: OutlinedButton.icon(
        onPressed: () => Navigator.popUntil(context, (r) => r.isFirst),
        icon: const Icon(Icons.grid_view, size: 16, color: kText),
        label: const Text('Upload new testcase',
            style: TextStyle(color: kText, fontSize: 13)),
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 11),
          shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(10)),
          side: const BorderSide(color: kBorder),
        ),
      ),
    );
  }

  /* ── MAP ── */
  Widget _buildMap() {
    return Stack(
      children: [
        FlutterMap(
          mapController: _mapController,
          options: MapOptions(
            initialCenter: _initialPosition,
            initialZoom: 12,
            minZoom: 3,
            maxZoom: 18,
          ),
          children: [
            TileLayer(
              urlTemplate:
              'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'com.example.kriti_project',
            ),
            if (_showRoutes)
              PolylineLayer(
                polylines: _selectedTripIndex != null
                    ? [
                  if (_selectedTripIndex! < _polylines.length)
                    _polylines[_selectedTripIndex!]
                ]
                    : _polylines,
              ),
            MarkerLayer(markers: _markers),
          ],
        ),

        // Zoom controls
        Positioned(
          top: 80,
          right: 12,
          child: Column(
            children: [
              _mapBtn(Icons.add, () => _mapController.move(
                  _mapController.camera.center,
                  _mapController.camera.zoom + 1)),
              const SizedBox(height: 1),
              _mapBtn(Icons.remove, () => _mapController.move(
                  _mapController.camera.center,
                  _mapController.camera.zoom - 1)),
              const SizedBox(height: 1),
              _mapFitBtn(),
            ],
          ),
        ),

        // Open sidebar button
        if (!_sidebarOpen)
          Positioned(
            top: 16,
            left: 12,
            child: _mapBtn(Icons.chevron_right,
                    () => setState(() => _sidebarOpen = true)),
          ),
      ],
    );
  }

  Widget _mapBtn(IconData icon, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: kBorder),
          boxShadow: [
            BoxShadow(
                color: Colors.black.withOpacity(0.07),
                blurRadius: 6,
                offset: const Offset(0, 2))
          ],
        ),
        child: Icon(icon, size: 20, color: const Color(0xFF424242)),
      ),
    );
  }

  Widget _mapFitBtn() {
    return GestureDetector(
      onTap: () {
        if (_markers.isNotEmpty) {
          final lats = _markers.map((m) => m.point.latitude).toList();
          final lngs = _markers.map((m) => m.point.longitude).toList();
          final bounds = LatLngBounds(
            LatLng(
                lats.reduce((a, b) => a < b ? a : b),
                lngs.reduce((a, b) => a < b ? a : b)),
            LatLng(
                lats.reduce((a, b) => a > b ? a : b),
                lngs.reduce((a, b) => a > b ? a : b)),
          );
          _mapController.fitCamera(
            CameraFit.bounds(
                bounds: bounds, padding: const EdgeInsets.all(40)),
          );
        }
      },
      child: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: kBorder),
          boxShadow: [
            BoxShadow(
                color: Colors.black.withOpacity(0.07),
                blurRadius: 6,
                offset: const Offset(0, 2))
          ],
        ),
        child: const Center(
          child: Text('Fit',
              style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF616161))),
        ),
      ),
    );
  }

  /* ── MODALS ── */
  void _showEmployeeModal() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => _EmployeeModal(
        onSubmit: (data) {
          Navigator.pop(ctx);
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
                content: Text('Employee add functionality requires testcase mode'),
                duration: Duration(seconds: 3)),
          );
        },
      ),
    );
  }

  void _showVehicleModal() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => _VehicleModal(
        onSubmit: (data) {
          Navigator.pop(ctx);
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
                content: Text('Vehicle add functionality requires testcase mode'),
                duration: Duration(seconds: 3)),
          );
        },
      ),
    );
  }

  /* ── Helper widgets ── */
  Widget _sectionCard({required String label, required Widget child}) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: kBorder),
        boxShadow: [
          BoxShadow(
              color: Colors.black.withOpacity(0.03),
              blurRadius: 6,
              offset: const Offset(0, 2))
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style: const TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  color: kSubText,
                  letterSpacing: 0.6)),
          const SizedBox(height: 10),
          child,
        ],
      ),
    );
  }

  Widget _buildLoading() {
    return const Scaffold(
      backgroundColor: Colors.black,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(color: Colors.white),
            SizedBox(height: 16),
            Text('Building map...',
                style: TextStyle(color: Colors.white, fontSize: 15)),
          ],
        ),
      ),
    );
  }

  Widget _buildError() {
    return Scaffold(
      backgroundColor: kGrey,
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, color: kRed, size: 56),
              const SizedBox(height: 16),
              const Text('Failed to load map',
                  style: TextStyle(
                      fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              Text(_errorMessage!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 13, color: kSubText)),
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: () => Navigator.pop(context),
                style: ElevatedButton.styleFrom(
                    backgroundColor: kText, elevation: 0),
                child: const Text('Go Back',
                    style: TextStyle(color: Colors.white)),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _mapController.dispose();
    super.dispose();
  }
}

/* ─────────── CUSTOM MARKERS ─────────── */

class _DepotMarker extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 32,
      height: 32,
      decoration: BoxDecoration(
        color: const Color(0xFFE11D48),
        borderRadius: BorderRadius.circular(6),
        boxShadow: [
          BoxShadow(
              color: Colors.black.withOpacity(0.25),
              blurRadius: 4,
              offset: const Offset(0, 2))
        ],
      ),
      child: const Icon(Icons.business, color: Colors.white, size: 18),
    );
  }
}

class _EmployeeMarker extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 28,
      height: 28,
      decoration: BoxDecoration(
        color: Colors.black,
        shape: BoxShape.circle,
        boxShadow: [
          BoxShadow(
              color: Colors.black.withOpacity(0.25),
              blurRadius: 4,
              offset: const Offset(0, 2))
        ],
      ),
      child: const Icon(Icons.person, color: Colors.white, size: 16),
    );
  }
}

/* ─────────── EMPLOYEE MODAL ─────────── */

class _EmployeeModal extends StatelessWidget {
  final void Function(Map<String, dynamic>) onSubmit;

  const _EmployeeModal({required this.onSubmit});

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.9,
      maxChildSize: 0.95,
      minChildSize: 0.5,
      builder: (ctx, sc) => Container(
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: Column(
          children: [
            const SizedBox(height: 8),
            Container(
                width: 36,
                height: 4,
                decoration: BoxDecoration(
                    color: kBorder,
                    borderRadius: BorderRadius.circular(2))),
            const SizedBox(height: 4),
            Padding(
              padding:
              const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
              child: Row(
                children: [
                  const Text('Add employee',
                      style: TextStyle(
                          fontSize: 17, fontWeight: FontWeight.bold)),
                  const Spacer(),
                  IconButton(
                      onPressed: () => Navigator.pop(context),
                      icon: const Icon(Icons.close)),
                ],
              ),
            ),
            const Divider(height: 1, color: kBorder),
            Expanded(
              child: ListView(
                controller: sc,
                padding: const EdgeInsets.all(20),
                children: [
                  _field('Employee ID *', 'employee_id'),
                  _field('Priority (1–5) *', 'priority', keyboardType: TextInputType.number),
                  Row(children: [
                    Expanded(child: _field('Pickup Lat *', 'pickup_lat', keyboardType: TextInputType.number)),
                    const SizedBox(width: 10),
                    Expanded(child: _field('Pickup Lng *', 'pickup_lng', keyboardType: TextInputType.number)),
                  ]),
                  Row(children: [
                    Expanded(child: _field('Drop Lat *', 'drop_lat', keyboardType: TextInputType.number)),
                    const SizedBox(width: 10),
                    Expanded(child: _field('Drop Lng *', 'drop_lng', keyboardType: TextInputType.number)),
                  ]),
                  Row(children: [
                    Expanded(child: _field('Baseline Cost *', 'baseline_cost', keyboardType: TextInputType.number)),
                    const SizedBox(width: 10),
                    Expanded(child: _field('Baseline Time (min) *', 'baseline_time', keyboardType: TextInputType.number)),
                  ]),
                  const SizedBox(height: 20),
                  ElevatedButton(
                    onPressed: () => onSubmit({}),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: kText,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10)),
                      elevation: 0,
                    ),
                    child: const Text('Add employee',
                        style:
                        TextStyle(color: Colors.white, fontSize: 15)),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _field(String label, String key,
      {TextInputType keyboardType = TextInputType.text}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  color: kText)),
          const SizedBox(height: 5),
          TextField(
            keyboardType: keyboardType,
            decoration: InputDecoration(
              contentPadding: const EdgeInsets.symmetric(
                  horizontal: 12, vertical: 11),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: const BorderSide(color: kBorder),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: const BorderSide(color: kBorder),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: const BorderSide(color: kText, width: 1.5),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/* ─────────── VEHICLE MODAL ─────────── */

class _VehicleModal extends StatelessWidget {
  final void Function(Map<String, dynamic>) onSubmit;

  const _VehicleModal({required this.onSubmit});

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.85,
      maxChildSize: 0.95,
      minChildSize: 0.4,
      builder: (ctx, sc) => Container(
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: Column(
          children: [
            const SizedBox(height: 8),
            Container(
                width: 36,
                height: 4,
                decoration: BoxDecoration(
                    color: kBorder,
                    borderRadius: BorderRadius.circular(2))),
            const SizedBox(height: 4),
            Padding(
              padding:
              const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
              child: Row(
                children: [
                  const Text('Add vehicle',
                      style: TextStyle(
                          fontSize: 17, fontWeight: FontWeight.bold)),
                  const Spacer(),
                  IconButton(
                      onPressed: () => Navigator.pop(context),
                      icon: const Icon(Icons.close)),
                ],
              ),
            ),
            const Divider(height: 1, color: kBorder),
            Expanded(
              child: ListView(
                controller: sc,
                padding: const EdgeInsets.all(20),
                children: [
                  _field('Vehicle ID *', 'vehicle_id'),
                  Row(children: [
                    Expanded(child: _field('Capacity *', 'capacity', keyboardType: TextInputType.number)),
                    const SizedBox(width: 10),
                    Expanded(child: _field('Cost per km *', 'cost_per_km', keyboardType: TextInputType.number)),
                  ]),
                  _field('Avg Speed (km/h) *', 'avg_speed_kmph', keyboardType: TextInputType.number),
                  Row(children: [
                    Expanded(child: _field('Current Lat *', 'current_lat', keyboardType: TextInputType.number)),
                    const SizedBox(width: 10),
                    Expanded(child: _field('Current Lng *', 'current_lng', keyboardType: TextInputType.number)),
                  ]),
                  const SizedBox(height: 8),
                  const Text('Category *',
                      style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          color: kText)),
                  const SizedBox(height: 5),
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 12, vertical: 4),
                    decoration: BoxDecoration(
                      border: Border.all(color: kBorder),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<String>(
                        isExpanded: true,
                        hint: const Text('Select…',
                            style: TextStyle(color: kSubText)),
                        items: const [
                          DropdownMenuItem(
                              value: 'premium',
                              child: Text('Premium')),
                          DropdownMenuItem(
                              value: 'normal', child: Text('Normal')),
                        ],
                        onChanged: (_) {},
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),
                  ElevatedButton(
                    onPressed: () => onSubmit({}),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: kText,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10)),
                      elevation: 0,
                    ),
                    child: const Text('Add vehicle',
                        style:
                        TextStyle(color: Colors.white, fontSize: 15)),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _field(String label, String key,
      {TextInputType keyboardType = TextInputType.text}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  color: kText)),
          const SizedBox(height: 5),
          TextField(
            keyboardType: keyboardType,
            decoration: InputDecoration(
              contentPadding: const EdgeInsets.symmetric(
                  horizontal: 12, vertical: 11),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: const BorderSide(color: kBorder),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: const BorderSide(color: kBorder),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: const BorderSide(color: kText, width: 1.5),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
