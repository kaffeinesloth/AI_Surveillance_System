enum TimestampDisplayStyle { dateTime, dateOnly }

String formatBackendTimestamp(
  String? value, {
  TimestampDisplayStyle style = TimestampDisplayStyle.dateTime,
  String fallback = 'Unknown time',
}) {
  final normalized = value?.trim();
  if (normalized == null || normalized.isEmpty) return fallback;

  final parsed = DateTime.tryParse(normalized.replaceFirst(' ', 'T'));
  if (parsed == null) return fallback;

  final local = parsed.toLocal();
  return switch (style) {
    TimestampDisplayStyle.dateTime => _formatDateTime(local),
    TimestampDisplayStyle.dateOnly => _formatDateOnly(local),
  };
}

String _formatDateTime(DateTime value) {
  final hour = value.hour.toString().padLeft(2, '0');
  final minute = value.minute.toString().padLeft(2, '0');
  return '${_monthName(value.month)} ${value.day}, ${value.year} at $hour:$minute';
}

String _formatDateOnly(DateTime value) {
  return '${value.year.toString().padLeft(4, '0')}-'
      '${value.month.toString().padLeft(2, '0')}-'
      '${value.day.toString().padLeft(2, '0')}';
}

String _monthName(int month) {
  const months = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ];
  if (month < 1 || month > months.length) return 'Unknown';
  return months[month - 1];
}
