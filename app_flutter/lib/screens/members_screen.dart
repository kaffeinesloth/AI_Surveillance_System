import 'package:flutter/material.dart';

import '../models/member_model.dart';
import '../services/member_service.dart';
import '../widgets/app_page.dart';
import '../widgets/empty_panel.dart';

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

  late Future<List<MemberModel>> _membersFuture;

  @override
  void initState() {
    super.initState();
    _membersFuture = _memberService.listMembers();
  }

  @override
  void didUpdateWidget(covariant MembersScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.refreshToken != widget.refreshToken) {
      _refreshMembers();
    }
  }

  void _refreshMembers() {
    setState(() => _membersFuture = _memberService.listMembers());
  }

  @override
  Widget build(BuildContext context) {
    return AppPage(
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                'Registered people',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
            ),
            IconButton.filledTonal(
              onPressed: _refreshMembers,
              icon: const Icon(Icons.refresh),
              tooltip: 'Refresh',
            ),
          ],
        ),
        const SizedBox(height: 12),
        FutureBuilder<List<MemberModel>>(
          future: _membersFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const _MembersLoadingCard();
            }

            if (snapshot.hasError) {
              return _MembersErrorCard(
                message: snapshot.error.toString().replaceFirst(
                      'Exception: ',
                      '',
                    ),
                onRetry: _refreshMembers,
              );
            }

            final members = snapshot.data ?? const [];
            if (members.isEmpty) {
              return const EmptyPanel(
                icon: Icons.people_outline,
                title: 'No registered people',
                message: 'Registered people will appear here after image registration.',
              );
            }

            return Column(
              children: members
                  .map(
                    (member) => Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: _MemberCard(
                        member: member,
                        onDelete: () => _deleteMember(member),
                      ),
                    ),
                  )
                  .toList(),
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
          title: const Text('Delete member'),
          content: Text('Delete ${member.name} and saved registration files?'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Delete'),
            ),
          ],
        );
      },
    );

    if (confirmed != true) {
      return;
    }

    try {
      await _memberService.deleteMember(member.id);
      if (!mounted) return;
      _refreshMembers();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Deleted ${member.name}.')),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(error.toString().replaceFirst('Exception: ', '')),
          backgroundColor: const Color(0xFFB91C1C),
        ),
      );
    }
  }
}

class _MemberCard extends StatelessWidget {
  const _MemberCard({
    required this.member,
    required this.onDelete,
  });

  final MemberModel member;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            CircleAvatar(
              backgroundColor: const Color(0xFFE0F2F1),
              foregroundColor: const Color(0xFF0F766E),
              child: Text(_initialsFor(member.name)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    member.name,
                    style: textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Registered ${_formatCreatedAt(member.createdAt)}',
                    style: textTheme.bodySmall?.copyWith(
                      color: const Color(0xFF6B7280),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Chip(
              avatar: const Icon(Icons.image_outlined, size: 18),
              label: Text('${member.imageCount} image(s)'),
            ),
            IconButton(
              onPressed: onDelete,
              icon: const Icon(Icons.delete_outline),
              tooltip: 'Delete',
            ),
          ],
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

  static String _formatCreatedAt(String value) {
    final parsed = DateTime.tryParse(value.replaceFirst(' ', 'T'));
    if (parsed == null) {
      return value;
    }
    final date = '${parsed.year.toString().padLeft(4, '0')}-'
        '${parsed.month.toString().padLeft(2, '0')}-'
        '${parsed.day.toString().padLeft(2, '0')}';
    final time = '${parsed.hour.toString().padLeft(2, '0')}:'
        '${parsed.minute.toString().padLeft(2, '0')}';
    return '$date $time';
  }
}

class _MembersLoadingCard extends StatelessWidget {
  const _MembersLoadingCard();

  @override
  Widget build(BuildContext context) {
    return const Card(
      child: Padding(
        padding: EdgeInsets.all(20),
        child: Center(child: CircularProgressIndicator()),
      ),
    );
  }
}

class _MembersErrorCard extends StatelessWidget {
  const _MembersErrorCard({
    required this.message,
    required this.onRetry,
  });

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              message,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: const Color(0xFFB91C1C),
                  ),
            ),
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerRight,
              child: OutlinedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
