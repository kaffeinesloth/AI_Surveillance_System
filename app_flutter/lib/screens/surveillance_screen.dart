import 'package:flutter/material.dart';

import '../widgets/app_page.dart';
import '../widgets/camera_placeholder.dart';
import '../widgets/command_button.dart';
import '../widgets/empty_panel.dart';
import '../widgets/header_block.dart';
import '../widgets/status_dot.dart';

class SurveillanceScreen extends StatelessWidget {
  const SurveillanceScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return AppPage(
      children: [
        const HeaderBlock(
          title: 'Live Surveillance',
          subtitle:
              'This page is reserved for webcam preview and live recognition results.',
          icon: Icons.videocam,
        ),
        const SizedBox(height: 16),
        const CameraPlaceholder(),
        const SizedBox(height: 16),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    const StatusDot(color: Color(0xFF9CA3AF)),
                    const SizedBox(width: 8),
                    Text(
                      'Camera stopped',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                const EmptyPanel(
                  icon: Icons.face_retouching_off_outlined,
                  title: 'No live detection result',
                  message:
                      'Start the backend camera pipeline to show person name, status, and confidence.',
                  compact: true,
                ),
                const SizedBox(height: 16),
                const Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    CommandButton(
                      icon: Icons.play_arrow,
                      label: 'Start',
                      enabled: false,
                    ),
                    CommandButton(
                      icon: Icons.stop,
                      label: 'Stop',
                      enabled: false,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
