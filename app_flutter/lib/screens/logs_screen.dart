import 'package:flutter/material.dart';

import '../core/timestamp_formatter.dart';
import '../models/security_models.dart';
import '../services/security_service.dart';
import '../theme/app_tokens.dart';
import '../widgets/app_message.dart';
import '../widgets/app_page.dart';
import '../widgets/empty_panel.dart';
import '../widgets/header_block.dart';
import '../widgets/status_badge.dart';

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
  int get _unknownLogCount =>
      _logs.where((log) => log.status != 'known').length;
  int get _unreadAlertCount => _alerts.where((alert) => !alert.isRead).length;

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
      if (mounted) setState(() => _error = friendlyErrorMessage(error));
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
      showAppSnackBar(
        context,
        message: updated.isRead ? 'Alert marked read.' : 'Alert marked unread.',
        tone: AppMessageTone.success,
      );
    } catch (error) {
      if (mounted) setState(() => _error = friendlyErrorMessage(error));
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
        icon: const Icon(Icons.delete_outline, color: AppColors.danger),
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton.icon(
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.danger,
              foregroundColor: Colors.white,
            ),
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
      if (!mounted) return;
      showAppSnackBar(
        context,
        message: count == 1 ? 'Deleted selected log.' : 'Deleted $count logs.',
        tone: AppMessageTone.success,
      );
    } catch (error) {
      if (mounted) setState(() => _error = friendlyErrorMessage(error));
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
      if (!mounted) return;
      showAppSnackBar(
        context,
        message:
            count == 1 ? 'Deleted selected alert.' : 'Deleted $count alerts.',
        tone: AppMessageTone.success,
      );
    } catch (error) {
      if (mounted) setState(() => _error = friendlyErrorMessage(error));
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
      if (!mounted) return;
      showAppSnackBar(
        context,
        message: 'Deleted all logs.',
        tone: AppMessageTone.success,
      );
    } catch (error) {
      if (mounted) setState(() => _error = friendlyErrorMessage(error));
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
      if (!mounted) return;
      showAppSnackBar(
        context,
        message: 'Deleted all alerts.',
        tone: AppMessageTone.success,
      );
    } catch (error) {
      if (mounted) setState(() => _error = friendlyErrorMessage(error));
    } finally {
      if (mounted) setState(() => _deletingAlerts = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final listHeight = (MediaQuery.sizeOf(context).height - 330)
        .clamp(420.0, 760.0)
        .toDouble();

    return DefaultTabController(
      length: 2,
      child: AppPage(
        maxWidth: AppLayout.dataMaxWidth,
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
          const SizedBox(height: AppSpacing.lg),
          _LogsSummaryBar(
            logCount: _logs.length,
            unknownLogCount: _unknownLogCount,
            alertCount: _alerts.length,
            unreadAlertCount: _unreadAlertCount,
          ),
          const SizedBox(height: AppSpacing.md),
          if (_error != null)
            _ErrorPanel(message: _error!, onRetry: _busy ? null : _refresh),
          if (_error != null) const SizedBox(height: AppSpacing.md),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const TabBar(
                    tabs: [
                      Tab(
                        icon: Icon(Icons.fact_check_outlined),
                        text: 'Detection logs',
                      ),
                      Tab(
                        icon: Icon(Icons.notifications_outlined),
                        text: 'Alerts',
                      ),
                    ],
                  ),
                  if (_loading) const LinearProgressIndicator(),
                  if (_selectedLogIds.isNotEmpty) ...[
                    const SizedBox(height: AppSpacing.md),
                    _SelectionToolbar(
                      label: '${_selectedLogIds.length} log selected',
                      deleting: _deletingLogs,
                      onClear: () => setState(() => _selectedLogIds = const {}),
                      onDelete: _deleteSelectedLogs,
                    ),
                  ],
                  if (_selectedAlertIds.isNotEmpty) ...[
                    const SizedBox(height: AppSpacing.md),
                    _SelectionToolbar(
                      label: '${_selectedAlertIds.length} alert selected',
                      deleting: _deletingAlerts,
                      onClear: () =>
                          setState(() => _selectedAlertIds = const {}),
                      onDelete: _deleteSelectedAlerts,
                    ),
                  ],
                  const SizedBox(height: AppSpacing.md),
                  SizedBox(
                    height: listHeight,
                    child: TabBarView(
                      children: [
                        _DetectionLogsTab(
                          logs: _logs,
                          loading: _loading,
                          deleting: _deletingLogs,
                          selectedIds: _selectedLogIds,
                          onToggleSelection: _toggleLogSelection,
                          onDeleteAll: _deleteAllLogs,
                        ),
                        _AlertsTab(
                          alerts: _alerts,
                          loading: _loading,
                          deleting: _deletingAlerts,
                          selectedIds: _selectedAlertIds,
                          onToggleSelection: _toggleAlertSelection,
                          onToggleRead: _toggleRead,
                          onDeleteAll: _deleteAllAlerts,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _LogsSummaryBar extends StatelessWidget {
  const _LogsSummaryBar({
    required this.logCount,
    required this.unknownLogCount,
    required this.alertCount,
    required this.unreadAlertCount,
  });

  final int logCount;
  final int unknownLogCount;
  final int alertCount;
  final int unreadAlertCount;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: AppSpacing.sm,
      runSpacing: AppSpacing.sm,
      children: [
        StatusBadge(
          icon: Icons.fact_check_outlined,
          label: '$logCount logs',
        ),
        StatusBadge(
          icon: Icons.person_search,
          label: '$unknownLogCount unknown',
          tone: unknownLogCount == 0
              ? StatusBadgeTone.neutral
              : StatusBadgeTone.warning,
        ),
        StatusBadge(
          icon: Icons.notifications_outlined,
          label: '$alertCount alerts',
        ),
        StatusBadge(
          icon: Icons.notification_important,
          label: '$unreadAlertCount unread',
          tone: unreadAlertCount == 0
              ? StatusBadgeTone.neutral
              : StatusBadgeTone.danger,
        ),
      ],
    );
  }
}

class _DetectionLogsTab extends StatelessWidget {
  const _DetectionLogsTab({
    required this.logs,
    required this.loading,
    required this.deleting,
    required this.selectedIds,
    required this.onToggleSelection,
    required this.onDeleteAll,
  });

  final List<DetectionLogModel> logs;
  final bool loading;
  final bool deleting;
  final Set<int> selectedIds;
  final void Function(DetectionLogModel log, bool selected) onToggleSelection;
  final VoidCallback onDeleteAll;

  @override
  Widget build(BuildContext context) {
    if (loading && logs.isEmpty) {
      return const _LoadingRows(label: 'Loading detection logs');
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _TabActionRow(
          title: 'Live detection history',
          subtitle: 'Known and unknown people detected by live surveillance.',
          action: OutlinedButton.icon(
            onPressed: logs.isEmpty || deleting ? null : onDeleteAll,
            icon: const Icon(Icons.delete_sweep_outlined),
            label: const Text('Delete all logs'),
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Expanded(
          child: logs.isEmpty
              ? const EmptyPanel(
                  icon: Icons.inbox_outlined,
                  title: 'No live detection logs',
                  message: 'Start live surveillance to create history.',
                )
              : ListView.builder(
                  itemCount: logs.length,
                  itemBuilder: (context, index) {
                    final log = logs[index];
                    return _DetectionLogRow(
                      log: log,
                      selected: selectedIds.contains(log.id),
                      deleting: deleting,
                      onSelected: (selected) =>
                          onToggleSelection(log, selected),
                    );
                  },
                ),
        ),
      ],
    );
  }
}

class _AlertsTab extends StatelessWidget {
  const _AlertsTab({
    required this.alerts,
    required this.loading,
    required this.deleting,
    required this.selectedIds,
    required this.onToggleSelection,
    required this.onToggleRead,
    required this.onDeleteAll,
  });

  final List<AlertModel> alerts;
  final bool loading;
  final bool deleting;
  final Set<int> selectedIds;
  final void Function(AlertModel alert, bool selected) onToggleSelection;
  final ValueChanged<AlertModel> onToggleRead;
  final VoidCallback onDeleteAll;

  @override
  Widget build(BuildContext context) {
    if (loading && alerts.isEmpty) {
      return const _LoadingRows(label: 'Loading alerts');
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _TabActionRow(
          title: 'Alert inbox',
          subtitle: 'Unknown-person alerts requiring review.',
          action: OutlinedButton.icon(
            onPressed: alerts.isEmpty || deleting ? null : onDeleteAll,
            icon: const Icon(Icons.delete_sweep_outlined),
            label: const Text('Delete all alerts'),
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Expanded(
          child: alerts.isEmpty
              ? const EmptyPanel(
                  icon: Icons.notifications_none,
                  title: 'No persistent alerts',
                  message:
                      'Confirmed unknown people from live mode appear here.',
                )
              : ListView.builder(
                  itemCount: alerts.length,
                  itemBuilder: (context, index) {
                    final alert = alerts[index];
                    return _AlertRow(
                      alert: alert,
                      selected: selectedIds.contains(alert.id),
                      deleting: deleting,
                      onSelected: (selected) =>
                          onToggleSelection(alert, selected),
                      onToggleRead: () => onToggleRead(alert),
                    );
                  },
                ),
        ),
      ],
    );
  }
}

class _TabActionRow extends StatelessWidget {
  const _TabActionRow({
    required this.title,
    required this.subtitle,
    required this.action,
  });

  final String title;
  final String subtitle;
  final Widget action;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final text = Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w900,
                    color: AppColors.text,
                  ),
            ),
            const SizedBox(height: AppSpacing.xs),
            Text(
              subtitle,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppColors.textMuted,
                  ),
            ),
          ],
        );

        if (constraints.maxWidth < AppBreakpoints.compact) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              text,
              const SizedBox(height: AppSpacing.md),
              action,
            ],
          );
        }

        return Row(
          children: [
            Expanded(child: text),
            const SizedBox(width: AppSpacing.md),
            action,
          ],
        );
      },
    );
  }
}

class _DetectionLogRow extends StatelessWidget {
  const _DetectionLogRow({
    required this.log,
    required this.selected,
    required this.deleting,
    required this.onSelected,
  });

  final DetectionLogModel log;
  final bool selected;
  final bool deleting;
  final ValueChanged<bool> onSelected;

  bool get isKnown => log.status == 'known';

  @override
  Widget build(BuildContext context) {
    return _SelectableRecordCard(
      selected: selected,
      severe: !isKnown,
      checkbox: Checkbox(
        value: selected,
        onChanged: deleting ? null : (value) => onSelected(value ?? false),
      ),
      icon: Icon(
        isKnown ? Icons.verified_user : Icons.person_search,
        color: isKnown ? AppColors.success : AppColors.warning,
      ),
      title: log.memberName ?? 'Unknown person',
      subtitle: log.cameraName,
      timestamp: formatBackendTimestamp(log.detectedAt),
      badges: [
        StatusBadge(
          label: log.status,
          icon: isKnown ? Icons.check_circle_outline : Icons.warning_amber,
          tone: isKnown ? StatusBadgeTone.success : StatusBadgeTone.warning,
        ),
        if (log.confidence != null)
          StatusBadge(
            icon: Icons.percent,
            label: '${(log.confidence! * 100).toStringAsFixed(1)}%',
          ),
      ],
      onTap: deleting ? null : () => onSelected(!selected),
    );
  }
}

class _AlertRow extends StatelessWidget {
  const _AlertRow({
    required this.alert,
    required this.selected,
    required this.deleting,
    required this.onSelected,
    required this.onToggleRead,
  });

  final AlertModel alert;
  final bool selected;
  final bool deleting;
  final ValueChanged<bool> onSelected;
  final VoidCallback onToggleRead;

  @override
  Widget build(BuildContext context) {
    return _SelectableRecordCard(
      selected: selected,
      severe: !alert.isRead,
      checkbox: Checkbox(
        value: selected,
        onChanged: deleting ? null : (value) => onSelected(value ?? false),
      ),
      icon: Stack(
        clipBehavior: Clip.none,
        children: [
          Icon(
            alert.isRead
                ? Icons.notifications_none
                : Icons.notification_important,
            color: alert.isRead ? AppColors.textMuted : AppColors.danger,
          ),
          if (!alert.isRead)
            Positioned(
              right: -1,
              top: -1,
              child: Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(
                  color: AppColors.danger,
                  shape: BoxShape.circle,
                ),
              ),
            ),
        ],
      ),
      title: alert.message,
      subtitle: alert.cameraName,
      timestamp: formatBackendTimestamp(alert.createdAt),
      badges: [
        StatusBadge(
          label: alert.isRead ? 'Read' : 'Unread',
          icon: alert.isRead ? Icons.done : Icons.markunread,
          tone: alert.isRead ? StatusBadgeTone.neutral : StatusBadgeTone.danger,
        ),
        StatusBadge(
          label: alert.alertType.replaceAll('_', ' '),
          icon: Icons.label_outline,
          tone: StatusBadgeTone.warning,
        ),
      ],
      trailing: TextButton(
        onPressed: onToggleRead,
        child: Text(alert.isRead ? 'Mark unread' : 'Mark read'),
      ),
      onTap: deleting ? null : () => onSelected(!selected),
    );
  }
}

class _SelectableRecordCard extends StatelessWidget {
  const _SelectableRecordCard({
    required this.selected,
    required this.severe,
    required this.checkbox,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.timestamp,
    required this.badges,
    required this.onTap,
    this.trailing,
  });

  final bool selected;
  final bool severe;
  final Widget checkbox;
  final Widget icon;
  final String title;
  final String subtitle;
  final String timestamp;
  final List<Widget> badges;
  final VoidCallback? onTap;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final borderColor = selected
        ? AppColors.teal
        : severe
            ? AppColors.dangerBorder
            : AppColors.border;
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Card(
        color: severe ? AppColors.warning.withAlpha(10) : AppColors.surface,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(AppRadii.sm),
          child: Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(AppRadii.sm),
              border: Border.all(color: borderColor),
            ),
            padding: const EdgeInsets.all(AppSpacing.md),
            child: LayoutBuilder(
              builder: (context, constraints) {
                final content = Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    checkbox,
                    const SizedBox(width: AppSpacing.sm),
                    SizedBox(width: 32, child: Center(child: icon)),
                    const SizedBox(width: AppSpacing.md),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            title,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context)
                                .textTheme
                                .titleSmall
                                ?.copyWith(
                                  fontWeight: FontWeight.w900,
                                  color: AppColors.text,
                                ),
                          ),
                          const SizedBox(height: AppSpacing.xs),
                          Text(
                            '$subtitle · $timestamp',
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style:
                                Theme.of(context).textTheme.bodySmall?.copyWith(
                                      color: AppColors.textMuted,
                                    ),
                          ),
                          const SizedBox(height: AppSpacing.sm),
                          Wrap(
                            spacing: AppSpacing.sm,
                            runSpacing: AppSpacing.sm,
                            children: badges,
                          ),
                        ],
                      ),
                    ),
                  ],
                );

                if (trailing == null ||
                    constraints.maxWidth < AppBreakpoints.compact) {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      content,
                      if (trailing != null) ...[
                        const SizedBox(height: AppSpacing.sm),
                        Align(
                          alignment: Alignment.centerRight,
                          child: trailing!,
                        ),
                      ],
                    ],
                  );
                }

                return Row(
                  children: [
                    Expanded(child: content),
                    const SizedBox(width: AppSpacing.md),
                    trailing!,
                  ],
                );
              },
            ),
          ),
        ),
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
      color: AppColors.tealSoft,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Row(
          children: [
            Expanded(
              child: Text(
                label,
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      color: AppColors.tealDark,
                      fontWeight: FontWeight.w900,
                    ),
              ),
            ),
            TextButton(
              onPressed: deleting ? null : onClear,
              child: const Text('Clear selection'),
            ),
            const SizedBox(width: AppSpacing.sm),
            FilledButton.icon(
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.danger,
                foregroundColor: Colors.white,
              ),
              onPressed: deleting ? null : onDelete,
              icon: deleting
                  ? const SizedBox.square(
                      dimension: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.delete_outline),
              label: Text(deleting ? 'Deleting' : 'Delete selected'),
            ),
          ],
        ),
      ),
    );
  }
}

class _LoadingRows extends StatelessWidget {
  const _LoadingRows({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              label,
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w900,
                  ),
            ),
            const SizedBox(height: AppSpacing.md),
            const LinearProgressIndicator(),
            const SizedBox(height: AppSpacing.lg),
            ...List.generate(
              4,
              (_) => const Padding(
                padding: EdgeInsets.only(bottom: AppSpacing.md),
                child: LinearProgressIndicator(),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ErrorPanel extends StatelessWidget {
  const _ErrorPanel({required this.message, required this.onRetry});

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return EmptyPanel(
      icon: Icons.error_outline,
      title: 'Could not load logs',
      message: message,
      compact: true,
      action: OutlinedButton.icon(
        onPressed: onRetry,
        icon: const Icon(Icons.refresh),
        label: const Text('Retry'),
      ),
    );
  }
}
