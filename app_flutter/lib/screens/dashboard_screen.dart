import 'package:flutter/material.dart';

import '../widgets/app_page.dart';
import '../widgets/empty_panel.dart';
import '../widgets/header_block.dart';
import '../widgets/status_tile.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return AppPage(
      children: [
        const HeaderBlock(
          title: 'AI Face Recognition Security System',
          subtitle:
              'Register known people, run webcam surveillance, and review saved alerts.',
          icon: Icons.security,
        ),
        const SizedBox(height: 16),
        LayoutBuilder(
          builder: (context, constraints) {
            final isWide = constraints.maxWidth >= 720;
            final crossAxisCount = isWide ? 4 : 2;
            final cards = [
              const StatusTile(
                label: 'Backend',
                value: 'Not connected',
                icon: Icons.cloud_off_outlined,
              ),
              const StatusTile(
                label: 'Camera',
                value: 'Stopped',
                icon: Icons.videocam_off_outlined,
              ),
              const StatusTile(
                label: 'Registered people',
                value: 'No data yet',
                icon: Icons.groups_outlined,
              ),
              const StatusTile(
                label: 'Unknown alerts',
                value: 'No data yet',
                icon: Icons.warning_amber_outlined,
              ),
            ];

            return GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: crossAxisCount,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
                mainAxisExtent: isWide ? 132 : 152,
              ),
              itemCount: cards.length,
              itemBuilder: (context, index) => cards[index],
            );
          },
        ),
        const SizedBox(height: 16),
        const EmptyPanel(
          icon: Icons.fact_check_outlined,
          title: 'Latest detection will appear here',
          message:
              'Connect the FastAPI backend to show the newest recognition result.',
        ),
      ],
    );
  }
}
