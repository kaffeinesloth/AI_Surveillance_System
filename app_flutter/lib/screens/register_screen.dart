import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';

import '../models/member_model.dart';
import '../services/member_service.dart';
import '../widgets/app_page.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final TextEditingController _nameController = TextEditingController();
  final MemberService _memberService = const MemberService();

  List<PlatformFile> _selectedImages = [];
  RegisterMemberResult? _lastResult;
  late Future<List<MemberModel>> _membersFuture;
  bool _isSubmitting = false;

  @override
  void initState() {
    super.initState();
    _membersFuture = _memberService.listMembers();
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  Future<void> _pickImages() async {
    final result = await FilePicker.platform.pickFiles(
      allowMultiple: true,
      type: FileType.custom,
      allowedExtensions: ['jpg', 'jpeg', 'png', 'webp'],
      withData: false,
    );

    if (result == null) {
      return;
    }

    setState(() => _selectedImages = result.files);
  }

  void _removeSelectedImage(int index) {
    setState(() => _selectedImages = [..._selectedImages]..removeAt(index));
  }

  void _clearSelectedImages() {
    setState(() => _selectedImages = []);
  }

  void _refreshMembers() {
    setState(() => _membersFuture = _memberService.listMembers());
  }

  Future<void> _registerMember() async {
    final name = _nameController.text.trim();
    if (name.isEmpty) {
      _showMessage('Enter a person name first.', isError: true);
      return;
    }
    if (_selectedImages.isEmpty) {
      _showMessage('Choose at least one face image.', isError: true);
      return;
    }

    setState(() => _isSubmitting = true);
    try {
      final result = await _memberService.registerMember(
        name: name,
        images: _selectedImages,
      );
      if (!mounted) return;
      _nameController.clear();
      setState(() {
        _selectedImages = [];
        _lastResult = result;
        _membersFuture = _memberService.listMembers();
      });
      _showMessage(result.message);
    } catch (error) {
      if (!mounted) return;
      setState(() => _lastResult = null);
      _showMessage(
        error.toString().replaceFirst('Exception: ', ''),
        isError: true,
      );
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  void _showMessage(String message, {bool isError = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError ? const Color(0xFFB91C1C) : null,
      ),
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
      _showMessage('Deleted ${member.name}.');
    } catch (error) {
      if (!mounted) return;
      _showMessage(
        error.toString().replaceFirst('Exception: ', ''),
        isError: true,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppPage(
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TextField(
                  controller: _nameController,
                  decoration: const InputDecoration(
                    labelText: 'Person name',
                    hintText: 'Enter name',
                  ),
                ),
                const SizedBox(height: 16),
                OutlinedButton.icon(
                  onPressed: _isSubmitting ? null : _pickImages,
                  icon: const Icon(Icons.upload_file_outlined),
                  label: const Text('Choose face images'),
                ),
                const SizedBox(height: 12),
                _ImageSelectionSummary(
                  images: _selectedImages,
                  onRemove: _isSubmitting ? null : _removeSelectedImage,
                  onClear: _isSubmitting ? null : _clearSelectedImages,
                ),
                if (_lastResult != null) ...[
                  const SizedBox(height: 16),
                  _RegistrationResultPanel(result: _lastResult!),
                ],
                const SizedBox(height: 16),
                FilledButton.icon(
                  onPressed: _isSubmitting ? null : _registerMember,
                  icon: _isSubmitting
                      ? const SizedBox.square(
                          dimension: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.save_outlined),
                  label: Text(_isSubmitting ? 'Registering...' : 'Register'),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        _RegisteredPeoplePanel(
          membersFuture: _membersFuture,
          onRefresh: _refreshMembers,
          onDelete: _deleteMember,
        ),
      ],
    );
  }
}

class _RegisteredPeoplePanel extends StatelessWidget {
  const _RegisteredPeoplePanel({
    required this.membersFuture,
    required this.onRefresh,
    required this.onDelete,
  });

  final Future<List<MemberModel>> membersFuture;
  final VoidCallback onRefresh;
  final ValueChanged<MemberModel> onDelete;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Registered people',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                ),
                IconButton.filledTonal(
                  onPressed: onRefresh,
                  icon: const Icon(Icons.refresh),
                  tooltip: 'Refresh',
                ),
              ],
            ),
            const SizedBox(height: 12),
            FutureBuilder<List<MemberModel>>(
              future: membersFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Padding(
                    padding: EdgeInsets.all(16),
                    child: Center(child: CircularProgressIndicator()),
                  );
                }

                if (snapshot.hasError) {
                  return _InlineErrorPanel(
                    message: snapshot.error.toString().replaceFirst(
                          'Exception: ',
                          '',
                        ),
                    onRetry: onRefresh,
                  );
                }

                final members = snapshot.data ?? const [];
                if (members.isEmpty) {
                  return const _InlineEmptyPanel();
                }

                return Column(
                  children: members
                      .map(
                        (member) => Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: _CompactMemberTile(
                            member: member,
                            onDelete: () => onDelete(member),
                          ),
                        ),
                      )
                      .toList(),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _CompactMemberTile extends StatelessWidget {
  const _CompactMemberTile({
    required this.member,
    required this.onDelete,
  });

  final MemberModel member;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border.all(color: const Color(0xFFE5E7EB)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
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
                    overflow: TextOverflow.ellipsis,
                    style: textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${member.imageCount} image(s) - ${_formatCreatedAt(member.createdAt)}',
                    overflow: TextOverflow.ellipsis,
                    style: textTheme.bodySmall?.copyWith(
                      color: const Color(0xFF6B7280),
                    ),
                  ),
                ],
              ),
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
}

class _InlineEmptyPanel extends StatelessWidget {
  const _InlineEmptyPanel();

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border.all(color: const Color(0xFFE5E7EB)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          children: [
            const Icon(
              Icons.people_outline,
              size: 32,
              color: Color(0xFF9CA3AF),
            ),
            const SizedBox(height: 8),
            Text(
              'No registered people',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class _InlineErrorPanel extends StatelessWidget {
  const _InlineErrorPanel({
    required this.message,
    required this.onRetry,
  });

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border.all(color: const Color(0xFFFCA5A5)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            Expanded(
              child: Text(
                message,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: const Color(0xFFB91C1C),
                    ),
              ),
            ),
            IconButton(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              tooltip: 'Retry',
            ),
          ],
        ),
      ),
    );
  }
}

class _RegistrationResultPanel extends StatelessWidget {
  const _RegistrationResultPanel({required this.result});

  final RegisterMemberResult result;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: const Color(0xFFF9FAFB),
        border: Border.all(color: const Color(0xFFE5E7EB)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              result.message,
              style: textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            _ResultCountRow(
              acceptedCount: result.acceptedImages.length,
              rejectedCount: result.rejectedImages.length,
            ),
            if (result.rejectedImages.isNotEmpty) ...[
              const SizedBox(height: 10),
              ...result.rejectedImages.map(
                (image) => _RejectedImageReason(image: image),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ResultCountRow extends StatelessWidget {
  const _ResultCountRow({
    required this.acceptedCount,
    required this.rejectedCount,
  });

  final int acceptedCount;
  final int rejectedCount;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        Chip(
          avatar: const Icon(Icons.check_circle_outline, size: 18),
          label: Text('$acceptedCount accepted'),
        ),
        Chip(
          avatar: const Icon(Icons.error_outline, size: 18),
          label: Text('$rejectedCount rejected'),
        ),
      ],
    );
  }
}

class _RejectedImageReason extends StatelessWidget {
  const _RejectedImageReason({required this.image});

  final RegistrationImageResult image;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(
            Icons.warning_amber_outlined,
            size: 18,
            color: Color(0xFFB45309),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              '${image.filename}: ${image.reason}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
        ],
      ),
    );
  }
}

class _ImageSelectionSummary extends StatelessWidget {
  const _ImageSelectionSummary({
    required this.images,
    required this.onRemove,
    required this.onClear,
  });

  final List<PlatformFile> images;
  final ValueChanged<int>? onRemove;
  final VoidCallback? onClear;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    if (images.isEmpty) {
      return Text(
        'No images selected',
        style: textTheme.bodyMedium?.copyWith(
          color: const Color(0xFF6B7280),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          '${images.length} image(s) selected',
          style: textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: images.take(8).toList().asMap().entries.map((entry) {
            final index = entry.key;
            final image = entry.value;
            return Chip(
              avatar: const Icon(Icons.image_outlined, size: 18),
              label: Text(
                image.name,
                overflow: TextOverflow.ellipsis,
              ),
              deleteIcon: const Icon(Icons.close, size: 18),
              onDeleted: onRemove == null ? null : () => onRemove!(index),
            );
          }).toList(),
        ),
        if (images.length > 8) ...[
          const SizedBox(height: 8),
          Text(
            '+${images.length - 8} more',
            style: textTheme.bodySmall?.copyWith(
              color: const Color(0xFF6B7280),
            ),
          ),
        ],
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            onPressed: onClear,
            icon: const Icon(Icons.clear_all),
            label: const Text('Clear selection'),
          ),
        ),
      ],
    );
  }
}

String _initialsFor(String name) {
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

String _formatCreatedAt(String value) {
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
