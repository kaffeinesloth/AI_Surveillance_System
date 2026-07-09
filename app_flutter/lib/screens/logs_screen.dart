import 'package:flutter/material.dart';

import '../widgets/app_page.dart';
import '../widgets/empty_panel.dart';
import '../widgets/header_block.dart';

class LogsScreen extends StatelessWidget {
  const LogsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const AppPage(
      children: [
        HeaderBlock(
          title: 'Logs & Alerts',
          subtitle:
              'Detection history and unknown-person alerts will be listed here after backend integration.',
          icon: Icons.receipt_long,
        ),
        SizedBox(height: 16),
        EmptyPanel(
          icon: Icons.inbox_outlined,
          title: 'No logs or alerts yet',
          message:
              'Run surveillance and connect the log APIs to populate this page.',
        ),
      ],
    );
  }
}
