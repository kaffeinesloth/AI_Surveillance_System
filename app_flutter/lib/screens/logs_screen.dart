import 'package:flutter/material.dart';

import '../models/security_models.dart';
import '../services/security_service.dart';
import '../widgets/app_page.dart';
import '../widgets/empty_panel.dart';
import '../widgets/header_block.dart';

class LogsScreen extends StatefulWidget {
  const LogsScreen({super.key, this.service});

  final SecurityService? service;

  @override
  State<LogsScreen> createState() => _LogsScreenState();
}

class _LogsScreenState extends State<LogsScreen> {
  late final SecurityService _service = widget.service ?? SecurityService();
  List<DetectionLogModel> _logs = const [];
  List<AlertModel> _alerts = const [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final values = await Future.wait([
        _service.listLogs(),
        _service.listAlerts(),
      ]);
      if (!mounted) return;
      setState(() {
        _logs = values[0] as List<DetectionLogModel>;
        _alerts = values[1] as List<AlertModel>;
      });
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _toggleRead(AlertModel alert) async {
    try {
      final updated = await _service.setAlertRead(alert.id, !alert.isRead);
      if (!mounted) return;
      setState(() {
        final index = _alerts.indexWhere((item) => item.id == alert.id);
        if (index >= 0) {
          _alerts = [..._alerts]..[index] = updated;
        }
      });
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: AppPage(
        children: [
          HeaderBlock(
            title: 'Persistent Logs & Alerts',
            subtitle:
                'Only live-webcam events are saved. Uploaded-video events never appear here.',
            icon: Icons.receipt_long,
            trailing: IconButton(
              tooltip: 'Refresh',
              onPressed: _loading ? null : _refresh,
              icon: const Icon(Icons.refresh),
            ),
          ),
          const SizedBox(height: 12),
          const TabBar(
            tabs: [
              Tab(text: 'Detection logs'),
              Tab(text: 'Alerts'),
            ],
          ),
          if (_loading) const LinearProgressIndicator(),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          const SizedBox(height: 12),
          SizedBox(
            height: 540,
            child: TabBarView(
              children: [
                _logs.isEmpty
                    ? const EmptyPanel(
                        icon: Icons.inbox_outlined,
                        title: 'No live detection logs',
                        message: 'Start live surveillance to create history.',
                      )
                    : ListView.builder(
                        itemCount: _logs.length,
                        itemBuilder: (context, index) {
                          final log = _logs[index];
                          return Card(
                            child: ListTile(
                              leading: Icon(
                                log.status == 'known'
                                    ? Icons.verified_user
                                    : Icons.person_search,
                              ),
                              title: Text(log.memberName ?? 'Unknown person'),
                              subtitle: Text(
                                '${log.cameraName} · ${log.detectedAt}',
                              ),
                              trailing: Text(log.status),
                            ),
                          );
                        },
                      ),
                _alerts.isEmpty
                    ? const EmptyPanel(
                        icon: Icons.notifications_none,
                        title: 'No persistent alerts',
                        message:
                            'Confirmed unknown people from live mode appear here.',
                      )
                    : ListView.builder(
                        itemCount: _alerts.length,
                        itemBuilder: (context, index) {
                          final alert = _alerts[index];
                          return Card(
                            child: ListTile(
                              leading: Icon(
                                alert.isRead
                                    ? Icons.notifications_none
                                    : Icons.notification_important,
                                color: alert.isRead
                                    ? null
                                    : Theme.of(context).colorScheme.error,
                              ),
                              title: Text(alert.message),
                              subtitle: Text(
                                '${alert.cameraName} · ${alert.createdAt}',
                              ),
                              trailing: TextButton(
                                onPressed: () => _toggleRead(alert),
                                child: Text(
                                  alert.isRead ? 'Unread' : 'Mark read',
                                ),
                              ),
                            ),
                          );
                        },
                      ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
