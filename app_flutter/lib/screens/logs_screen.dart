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
  Set<int> _selectedLogIds = const {};
  Set<int> _selectedAlertIds = const {};
  bool _loading = true;
  bool _deletingLogs = false;
  bool _deletingAlerts = false;
  String? _error;

  bool get _busy => _loading || _deletingLogs || _deletingAlerts;

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
        _selectedLogIds = _selectedLogIds
            .where((id) => _logs.any((log) => log.id == id))
            .toSet();
        _selectedAlertIds = _selectedAlertIds
            .where((id) => _alerts.any((alert) => alert.id == id))
            .toSet();
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

  void _toggleLogSelection(DetectionLogModel log, bool selected) {
    setState(() {
      final selectedIds = {..._selectedLogIds};
      if (selected) {
        selectedIds.add(log.id);
      } else {
        selectedIds.remove(log.id);
      }
      _selectedLogIds = selectedIds;
    });
  }

  void _toggleAlertSelection(AlertModel alert, bool selected) {
    setState(() {
      final selectedIds = {..._selectedAlertIds};
      if (selected) {
        selectedIds.add(alert.id);
      } else {
        selectedIds.remove(alert.id);
      }
      _selectedAlertIds = selectedIds;
    });
  }

  Future<bool> _confirmDelete({
    required String title,
    required String message,
  }) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton.icon(
            onPressed: () => Navigator.of(context).pop(true),
            icon: const Icon(Icons.delete_outline),
            label: const Text('Delete'),
          ),
        ],
      ),
    );
    return confirmed == true;
  }

  Future<void> _deleteSelectedLogs() async {
    final count = _selectedLogIds.length;
    if (count == 0 || _deletingLogs) return;

    final confirmed = await _confirmDelete(
      title: count == 1 ? 'Delete log' : 'Delete logs',
      message: count == 1
          ? 'Delete this detection log from persistent storage?'
          : 'Delete these $count detection logs from persistent storage?',
    );
    if (confirmed != true) return;

    final ids = _selectedLogIds.toList();
    setState(() {
      _deletingLogs = true;
      _error = null;
    });
    try {
      await Future.wait(ids.map(_service.deleteLog));
      if (!mounted) return;
      setState(() => _selectedLogIds = const {});
      await _refresh();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _deletingLogs = false);
    }
  }

  Future<void> _deleteSelectedAlerts() async {
    final count = _selectedAlertIds.length;
    if (count == 0 || _deletingAlerts) return;

    final confirmed = await _confirmDelete(
      title: count == 1 ? 'Delete alert' : 'Delete alerts',
      message: count == 1
          ? 'Delete this alert from persistent storage?'
          : 'Delete these $count alerts from persistent storage?',
    );
    if (confirmed != true) return;

    final ids = _selectedAlertIds.toList();
    setState(() {
      _deletingAlerts = true;
      _error = null;
    });
    try {
      await Future.wait(ids.map(_service.deleteAlert));
      if (!mounted) return;
      setState(() => _selectedAlertIds = const {});
      await _refresh();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _deletingAlerts = false);
    }
  }

  Future<void> _deleteAllLogs() async {
    if (_logs.isEmpty || _deletingLogs) return;
    final confirmed = await _confirmDelete(
      title: 'Delete all logs',
      message: 'Delete all detection logs from persistent storage?',
    );
    if (!confirmed) return;

    setState(() {
      _deletingLogs = true;
      _error = null;
    });
    try {
      await _service.deleteAllLogs();
      if (!mounted) return;
      setState(() => _selectedLogIds = const {});
      await _refresh();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _deletingLogs = false);
    }
  }

  Future<void> _deleteAllAlerts() async {
    if (_alerts.isEmpty || _deletingAlerts) return;
    final confirmed = await _confirmDelete(
      title: 'Delete all alerts',
      message: 'Delete all alerts from persistent storage?',
    );
    if (!confirmed) return;

    setState(() {
      _deletingAlerts = true;
      _error = null;
    });
    try {
      await _service.deleteAllAlerts();
      if (!mounted) return;
      setState(() => _selectedAlertIds = const {});
      await _refresh();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _deletingAlerts = false);
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
              onPressed: _busy ? null : _refresh,
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
          if (_selectedLogIds.isNotEmpty) ...[
            const SizedBox(height: 12),
            _SelectionToolbar(
              label: '${_selectedLogIds.length} log selected',
              deleting: _deletingLogs,
              onClear: () => setState(() => _selectedLogIds = const {}),
              onDelete: _deleteSelectedLogs,
            ),
          ],
          if (_selectedAlertIds.isNotEmpty) ...[
            const SizedBox(height: 12),
            _SelectionToolbar(
              label: '${_selectedAlertIds.length} alert selected',
              deleting: _deletingAlerts,
              onClear: () => setState(() => _selectedAlertIds = const {}),
              onDelete: _deleteSelectedAlerts,
            ),
          ],
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
                Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Align(
                      alignment: Alignment.centerRight,
                      child: OutlinedButton.icon(
                        onPressed: _logs.isEmpty || _deletingLogs
                            ? null
                            : _deleteAllLogs,
                        icon: const Icon(Icons.delete_sweep_outlined),
                        label: const Text('Delete all logs'),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Expanded(
                      child: _logs.isEmpty
                          ? const EmptyPanel(
                              icon: Icons.inbox_outlined,
                              title: 'No live detection logs',
                              message:
                                  'Start live surveillance to create history.',
                            )
                          : ListView.builder(
                              itemCount: _logs.length,
                              itemBuilder: (context, index) {
                                final log = _logs[index];
                                final selected = _selectedLogIds.contains(
                                  log.id,
                                );
                                return Card(
                                  child: ListTile(
                                    leading: Checkbox(
                                      value: selected,
                                      onChanged: _deletingLogs
                                          ? null
                                          : (value) => _toggleLogSelection(
                                              log,
                                              value ?? false,
                                            ),
                                    ),
                                    title: Row(
                                      children: [
                                        Icon(
                                          log.status == 'known'
                                              ? Icons.verified_user
                                              : Icons.person_search,
                                          size: 20,
                                        ),
                                        const SizedBox(width: 8),
                                        Expanded(
                                          child: Text(
                                            log.memberName ?? 'Unknown person',
                                          ),
                                        ),
                                      ],
                                    ),
                                    subtitle: Text(
                                      '${log.cameraName} · ${log.detectedAt}',
                                    ),
                                    trailing: Text(log.status),
                                    onTap: _deletingLogs
                                        ? null
                                        : () => _toggleLogSelection(
                                            log,
                                            !selected,
                                          ),
                                  ),
                                );
                              },
                            ),
                    ),
                  ],
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Align(
                      alignment: Alignment.centerRight,
                      child: OutlinedButton.icon(
                        onPressed: _alerts.isEmpty || _deletingAlerts
                            ? null
                            : _deleteAllAlerts,
                        icon: const Icon(Icons.delete_sweep_outlined),
                        label: const Text('Delete all alerts'),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Expanded(
                      child: _alerts.isEmpty
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
                                final selected = _selectedAlertIds.contains(
                                  alert.id,
                                );
                                return Card(
                                  child: ListTile(
                                    leading: Checkbox(
                                      value: selected,
                                      onChanged: _deletingAlerts
                                          ? null
                                          : (value) => _toggleAlertSelection(
                                              alert,
                                              value ?? false,
                                            ),
                                    ),
                                    title: Row(
                                      children: [
                                        Icon(
                                          alert.isRead
                                              ? Icons.notifications_none
                                              : Icons.notification_important,
                                          color: alert.isRead
                                              ? null
                                              : Theme.of(
                                                  context,
                                                ).colorScheme.error,
                                          size: 20,
                                        ),
                                        const SizedBox(width: 8),
                                        Expanded(child: Text(alert.message)),
                                      ],
                                    ),
                                    subtitle: Text(
                                      '${alert.cameraName} · ${alert.createdAt}',
                                    ),
                                    trailing: TextButton(
                                      onPressed: () => _toggleRead(alert),
                                      child: Text(
                                        alert.isRead ? 'Unread' : 'Mark read',
                                      ),
                                    ),
                                    onTap: _deletingAlerts
                                        ? null
                                        : () => _toggleAlertSelection(
                                            alert,
                                            !selected,
                                          ),
                                  ),
                                );
                              },
                            ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SelectionToolbar extends StatelessWidget {
  const _SelectionToolbar({
    required this.label,
    required this.deleting,
    required this.onClear,
    required this.onDelete,
  });

  final String label;
  final bool deleting;
  final VoidCallback onClear;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            Expanded(
              child: Text(label, style: Theme.of(context).textTheme.titleSmall),
            ),
            TextButton(
              onPressed: deleting ? null : onClear,
              child: const Text('Clear'),
            ),
            const SizedBox(width: 8),
            FilledButton.icon(
              onPressed: deleting ? null : onDelete,
              icon: deleting
                  ? const SizedBox.square(
                      dimension: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.delete_outline),
              label: Text(deleting ? 'Deleting' : 'Delete'),
            ),
          ],
        ),
      ),
    );
  }
}
