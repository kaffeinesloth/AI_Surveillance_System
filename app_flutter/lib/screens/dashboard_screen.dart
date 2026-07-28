import 'dart:async';

import 'package:flutter/material.dart';

import '../models/security_models.dart';
import '../services/member_service.dart';
import '../services/security_service.dart';
import '../widgets/app_page.dart';
import '../widgets/empty_panel.dart';
import '../widgets/header_block.dart';
import '../widgets/status_tile.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({
    super.key,
    this.securityService,
    this.memberService = const MemberService(),
  });

  final SecurityService? securityService;
  final MemberService memberService;

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  late final SecurityService _security =
      widget.securityService ?? SecurityService();
  Timer? _timer;
  bool _online = false;
  int? _memberCount;
  int? _unreadAlerts;
  SurveillanceStatusModel? _status;
  DetectionLogModel? _latest;

  @override
  void initState() {
    super.initState();
    _refresh();
    _timer = Timer.periodic(const Duration(seconds: 5), (_) => _refresh());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final values = await Future.wait([
        _security.health(),
        widget.memberService.listMembers(),
        _security.surveillanceStatus(),
        _security.listAlerts(limit: 100),
        _security.listLogs(limit: 1),
      ]);
      if (!mounted) return;
      final alerts = values[3] as List<AlertModel>;
      final logs = values[4] as List<DetectionLogModel>;
      setState(() {
        _online = true;
        _memberCount = (values[1] as List).length;
        _status = values[2] as SurveillanceStatusModel;
        _unreadAlerts = alerts.where((alert) => !alert.isRead).length;
        _latest = logs.isEmpty ? null : logs.first;
      });
    } catch (_) {
      if (mounted) setState(() => _online = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppPage(
      children: [
        const HeaderBlock(
          title: 'AI Face Recognition Security System',
          subtitle:
              'Register known people, run webcam surveillance, and review saved alerts.',
          icon: Icons.security,
        ),
        const SizedBox(height: 16),
        LayoutBuilder(
          builder: (context, constraints) {
            final isWide = constraints.maxWidth >= 720;
            final cards = [
              StatusTile(
                label: 'Backend',
                value: _online ? 'Online' : 'Offline',
                icon: _online
                    ? Icons.cloud_done_outlined
                    : Icons.cloud_off_outlined,
              ),
              StatusTile(
                label: 'Camera',
                value: _status?.running == true
                    ? '${_status!.fps.toStringAsFixed(1)} FPS'
                    : 'Stopped',
                icon: _status?.running == true
                    ? Icons.videocam
                    : Icons.videocam_off_outlined,
              ),
              StatusTile(
                label: 'Registered people',
                value: _memberCount?.toString() ?? '—',
                icon: Icons.groups_outlined,
              ),
              StatusTile(
                label: 'Unread alerts',
                value: _unreadAlerts?.toString() ?? '—',
                icon: Icons.warning_amber_outlined,
              ),
            ];
            return GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: isWide ? 4 : 2,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
                mainAxisExtent: isWide ? 132 : 152,
              ),
              itemCount: cards.length,
              itemBuilder: (context, index) => cards[index],
            );
          },
        ),
        const SizedBox(height: 16),
        if (_latest == null)
          const EmptyPanel(
            icon: Icons.fact_check_outlined,
            title: 'No persistent live detection yet',
            message:
                'Uploaded-video results are temporary and do not appear here.',
          )
        else
          Card(
            child: ListTile(
              leading: Icon(
                _latest!.status == 'known'
                    ? Icons.verified_user
                    : Icons.warning_amber,
              ),
              title: Text(_latest!.memberName ?? 'Unknown person'),
              subtitle: Text('${_latest!.cameraName} · ${_latest!.detectedAt}'),
              trailing: Text(_latest!.status),
            ),
          ),
      ],
    );
  }
}
