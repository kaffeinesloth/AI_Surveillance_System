import 'package:flutter/material.dart';

import '../widgets/connection_chip.dart';
import 'dashboard_screen.dart';
import 'logs_screen.dart';
import 'register_screen.dart';
import 'surveillance_screen.dart';

class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _selectedIndex = 0;

  late final List<_NavPage> _pages = [
    _NavPage(
      title: 'Dashboard',
      icon: Icons.dashboard_outlined,
      selectedIcon: Icons.dashboard,
      child: DashboardScreen(),
    ),
    const _NavPage(
      title: 'Register',
      icon: Icons.person_add_alt_1_outlined,
      selectedIcon: Icons.person_add_alt_1,
      child: RegisterScreen(),
    ),
    const _NavPage(
      title: 'Surveillance',
      icon: Icons.videocam_outlined,
      selectedIcon: Icons.videocam,
      child: SurveillanceScreen(),
    ),
    const _NavPage(
      title: 'Logs',
      icon: Icons.receipt_long_outlined,
      selectedIcon: Icons.receipt_long,
      child: LogsScreen(),
    ),
  ];

  void _selectPage(int index) {
    setState(() => _selectedIndex = index);
  }

  @override
  Widget build(BuildContext context) {
    final page = _pages[_selectedIndex];

    return Scaffold(
      appBar: AppBar(
        title: Text(page.title),
        actions: const [
          Padding(
            padding: EdgeInsets.only(right: 16),
            child: ConnectionChip(),
          ),
        ],
      ),
      body: SafeArea(
        child: IndexedStack(
          index: _selectedIndex,
          children: _pages.map((page) => page.child).toList(),
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: _selectPage,
        destinations: _pages
            .map(
              (page) => NavigationDestination(
                icon: Icon(page.icon),
                selectedIcon: Icon(page.selectedIcon),
                label: page.title,
              ),
            )
            .toList(),
      ),
    );
  }
}

class _NavPage {
  const _NavPage({
    required this.title,
    required this.icon,
    required this.selectedIcon,
    required this.child,
  });

  final String title;
  final IconData icon;
  final IconData selectedIcon;
  final Widget child;
}
