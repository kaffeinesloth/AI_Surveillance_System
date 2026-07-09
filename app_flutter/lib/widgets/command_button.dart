import 'package:flutter/material.dart';

class CommandButton extends StatelessWidget {
  const CommandButton({
    super.key,
    required this.icon,
    required this.label,
    required this.enabled,
  });

  final IconData icon;
  final String label;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    return FilledButton.icon(
      onPressed: enabled ? () {} : null,
      icon: Icon(icon),
      label: Text(label),
    );
  }
}
