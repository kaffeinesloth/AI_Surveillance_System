import 'package:flutter/material.dart';

import '../core/timestamp_formatter.dart';
import '../models/member_model.dart';
import '../services/member_service.dart';
import '../theme/app_tokens.dart';
import '../widgets/app_message.dart';
import '../widgets/app_page.dart';
import '../widgets/empty_panel.dart';
import '../widgets/header_block.dart';
import '../widgets/section_header.dart';
import '../widgets/status_badge.dart';

class MembersScreen extends StatefulWidget {
  const MembersScreen({
    super.key,
    required this.refreshToken,
  });

  final int refreshToken;

  @override
  State<MembersScreen> createState() => _MembersScreenState();
}

class _MembersScreenState extends State<MembersScreen> {
  final MemberService _memberService = const MemberService();
  final TextEditingController _searchController = TextEditingController();
  final Set<int> _deletingMemberIds = {};

  late Future<List<MemberModel>> _membersFuture;
  String _query = '';

  @override
  void initState() {
    super.initState();
    _membersFuture = _memberService.listMembers();
    _searchController.addListener(_updateQuery);
  }

  @override
  void didUpdateWidget(covariant MembersScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.refreshToken != widget.refreshToken) {
      _refreshMembers();
    }
  }

  @override
  void dispose() {
    _searchController
      ..removeListener(_updateQuery)
      ..dispose();
    super.dispose();
  }

  void _updateQuery() {
    final nextQuery = _searchController.text.trim().toLowerCase();
    if (nextQuery == _query) return;
    setState(() => _query = nextQuery);
  }

  void _refreshMembers() {
    setState(() => _membersFuture = _memberService.listMembers());
  }

  void _clearSearch() {
    _searchController.clear();
  }

  List<MemberModel> _filterMembers(List<MemberModel> members) {
    if (_query.isEmpty) return members;
    return members.where((member) {
      final registered = formatBackendTimestamp(member.createdAt).toLowerCase();
      return member.name.toLowerCase().contains(_query) ||
          member.imageCount.toString().contains(_query) ||
          registered.contains(_query);
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return AppPage(
      maxWidth: AppLayout.dataMaxWidth,
      children: [
        HeaderBlock(
          title: 'Members',
          subtitle: 'Review registered people and manage saved face images.',
          icon: Icons.people_alt,
          trailing: IconButton(
            onPressed: _refreshMembers,
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        FutureBuilder<List<MemberModel>>(
          future: _membersFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const _MembersLoadingState();
            }

            if (snapshot.hasError) {
              return _MembersErrorState(
                message:
                    friendlyErrorMessage(snapshot.error ?? 'Unknown error'),
                onRetry: _refreshMembers,
              );
            }

            final members = snapshot.data ?? const [];
            final visibleMembers = _filterMembers(members);

            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _MembersToolbar(
                  totalCount: members.length,
                  visibleCount: visibleMembers.length,
                  searchController: _searchController,
                  onRefresh: _refreshMembers,
                  onClearSearch: _query.isEmpty ? null : _clearSearch,
                ),
                const SizedBox(height: AppSpacing.lg),
                SectionHeader(
                  title: 'Registered people',
                  subtitle: members.isEmpty
                      ? 'No known people are available to recognition yet.'
                      : '${visibleMembers.length} of ${members.length} people shown.',
                ),
                if (members.isEmpty)
                  const EmptyPanel(
                    icon: Icons.people_outline,
                    title: 'No registered people',
                    message:
                        'Registered people will appear here after image registration.',
                  )
                else if (visibleMembers.isEmpty)
                  EmptyPanel(
                    icon: Icons.search_off,
                    title: 'No matching members',
                    message:
                        'No registered person matches the current search filter.',
                    action: OutlinedButton.icon(
                      onPressed: _clearSearch,
                      icon: const Icon(Icons.clear),
                      label: const Text('Clear search'),
                    ),
                  )
                else
                  _MembersList(
                    members: visibleMembers,
                    deletingMemberIds: _deletingMemberIds,
                    onDelete: _deleteMember,
                  ),
              ],
            );
          },
        ),
      ],
    );
  }

  Future<void> _deleteMember(MemberModel member) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          icon: const Icon(Icons.delete_outline, color: AppColors.danger),
          title: Text('Delete ${member.name}?'),
          content: Text(
            'This removes ${member.name} and ${member.imageCount} saved face image(s) from the recognition database.',
          ),
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
              label: const Text('Delete member'),
            ),
          ],
        );
      },
    );

    if (confirmed != true) {
      return;
    }

    setState(() => _deletingMemberIds.add(member.id));
    try {
      await _memberService.deleteMember(member.id);
      if (!mounted) return;
      _refreshMembers();
      showAppSnackBar(
        context,
        message: 'Deleted ${member.name}.',
        tone: AppMessageTone.success,
      );
    } catch (error) {
      if (!mounted) return;
      showAppSnackBar(
        context,
        message: friendlyErrorMessage(error),
        tone: toneForError(error),
      );
    } finally {
      if (mounted) {
        setState(() => _deletingMemberIds.remove(member.id));
      }
    }
  }
}

class _MembersToolbar extends StatelessWidget {
  const _MembersToolbar({
    required this.totalCount,
    required this.visibleCount,
    required this.searchController,
    required this.onRefresh,
    required this.onClearSearch,
  });

  final int totalCount;
  final int visibleCount;
  final TextEditingController searchController;
  final VoidCallback onRefresh;
  final VoidCallback? onClearSearch;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final searchField = TextField(
              controller: searchController,
              decoration: InputDecoration(
                prefixIcon: const Icon(Icons.search),
                labelText: 'Search members',
                hintText: 'Name, image count, or registered date',
                suffixIcon: onClearSearch == null
                    ? null
                    : IconButton(
                        onPressed: onClearSearch,
                        icon: const Icon(Icons.close),
                        tooltip: 'Clear search',
                      ),
              ),
            );
            final summary = Wrap(
              spacing: AppSpacing.sm,
              runSpacing: AppSpacing.sm,
              children: [
                StatusBadge(
                  icon: Icons.people_alt_outlined,
                  label: '$totalCount total',
                ),
                if (visibleCount != totalCount)
                  StatusBadge(
                    icon: Icons.filter_alt_outlined,
                    label: '$visibleCount shown',
                    tone: StatusBadgeTone.warning,
                  ),
              ],
            );
            final refresh = OutlinedButton.icon(
              onPressed: onRefresh,
              icon: const Icon(Icons.refresh),
              label: const Text('Refresh'),
            );

            if (constraints.maxWidth < AppBreakpoints.compact) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  searchField,
                  const SizedBox(height: AppSpacing.md),
                  summary,
                  const SizedBox(height: AppSpacing.md),
                  refresh,
                ],
              );
            }

            return Row(
              children: [
                Expanded(flex: 5, child: searchField),
                const SizedBox(width: AppSpacing.lg),
                Expanded(flex: 3, child: summary),
                const SizedBox(width: AppSpacing.lg),
                refresh,
              ],
            );
          },
        ),
      ),
    );
  }
}

class _MembersList extends StatelessWidget {
  const _MembersList({
    required this.members,
    required this.deletingMemberIds,
    required this.onDelete,
  });

  final List<MemberModel> members;
  final Set<int> deletingMemberIds;
  final ValueChanged<MemberModel> onDelete;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: members
          .map(
            (member) => Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.md),
              child: _MemberCard(
                member: member,
                deleting: deletingMemberIds.contains(member.id),
                onDelete: () => onDelete(member),
              ),
            ),
          )
          .toList(),
    );
  }
}

class _MemberCard extends StatelessWidget {
  const _MemberCard({
    required this.member,
    required this.deleting,
    required this.onDelete,
  });

  final MemberModel member;
  final bool deleting;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final identity = Row(
              children: [
                CircleAvatar(
                  radius: 24,
                  backgroundColor: AppColors.tealSoft,
                  foregroundColor: AppColors.teal,
                  child: Text(
                    _initialsFor(member.name),
                    style: const TextStyle(fontWeight: FontWeight.w900),
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        member.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w900,
                          color: AppColors.text,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.xs),
                      Text(
                        'Registered ${formatBackendTimestamp(member.createdAt)}',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: textTheme.bodySmall?.copyWith(
                          color: AppColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            );
            final metadata = Wrap(
              spacing: AppSpacing.sm,
              runSpacing: AppSpacing.sm,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                StatusBadge(
                  icon: Icons.image_outlined,
                  label:
                      '${member.imageCount} image${member.imageCount == 1 ? '' : 's'}',
                ),
                StatusBadge(
                  icon: Icons.calendar_today_outlined,
                  label: formatBackendTimestamp(
                    member.createdAt,
                    style: TimestampDisplayStyle.dateOnly,
                    fallback: 'Unknown date',
                  ),
                ),
              ],
            );
            final deleteButton = deleting
                ? const SizedBox.square(
                    dimension: 40,
                    child: Padding(
                      padding: EdgeInsets.all(AppSpacing.sm),
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                  )
                : IconButton(
                    onPressed: onDelete,
                    icon: const Icon(Icons.delete_outline),
                    color: AppColors.danger,
                    tooltip: 'Delete member',
                  );

            if (constraints.maxWidth < AppBreakpoints.compact) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  identity,
                  const SizedBox(height: AppSpacing.md),
                  metadata,
                  const SizedBox(height: AppSpacing.sm),
                  Align(
                    alignment: Alignment.centerRight,
                    child: deleteButton,
                  ),
                ],
              );
            }

            return Row(
              children: [
                Expanded(flex: 5, child: identity),
                const SizedBox(width: AppSpacing.lg),
                Expanded(flex: 4, child: metadata),
                const SizedBox(width: AppSpacing.md),
                deleteButton,
              ],
            );
          },
        ),
      ),
    );
  }

  static String _initialsFor(String name) {
    final parts = name.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty || parts.first.isEmpty) {
      return '?';
    }
    if (parts.length == 1) {
      return parts.first.characters.first.toUpperCase();
    }
    return '${parts.first.characters.first}${parts.last.characters.first}'
        .toUpperCase();
  }
}

class _MembersLoadingState extends StatelessWidget {
  const _MembersLoadingState();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const SectionHeader(
              title: 'Loading members',
              subtitle: 'Fetching registered people from the backend.',
            ),
            const LinearProgressIndicator(),
            const SizedBox(height: AppSpacing.lg),
            ...List.generate(
              3,
              (index) => const Padding(
                padding: EdgeInsets.only(bottom: AppSpacing.md),
                child: _LoadingMemberRow(),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _LoadingMemberRow extends StatelessWidget {
  const _LoadingMemberRow();

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border.all(color: AppColors.border),
        borderRadius: BorderRadius.circular(AppRadii.sm),
      ),
      child: const Padding(
        padding: EdgeInsets.all(AppSpacing.lg),
        child: Row(
          children: [
            CircleAvatar(backgroundColor: AppColors.tealSoft),
            SizedBox(width: AppSpacing.md),
            Expanded(child: LinearProgressIndicator()),
          ],
        ),
      ),
    );
  }
}

class _MembersErrorState extends StatelessWidget {
  const _MembersErrorState({
    required this.message,
    required this.onRetry,
  });

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return EmptyPanel(
      icon: Icons.error_outline,
      title: 'Could not load members',
      message: friendlyErrorMessage(message),
      action: FilledButton.icon(
        onPressed: onRetry,
        icon: const Icon(Icons.refresh),
        label: const Text('Retry'),
      ),
    );
  }
}
