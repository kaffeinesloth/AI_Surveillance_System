import 'package:flutter/material.dart';

class ConnectionChip extends StatelessWidget {
  const ConnectionChip({super.key});

  @override
  Widget build(BuildContext context) {
    return Chip(
      avatar: const Icon(Icons.circle, size: 12, color: Color(0xFF9CA3AF)),
      label: const Text('Offline'),
      visualDensity: VisualDensity.compact,
      side: const BorderSide(color: Color(0xFFE5E7EB)),
      backgroundColor: Colors.white,
      labelStyle: const TextStyle(fontWeight: FontWeight.w700),
    );
  }
}
