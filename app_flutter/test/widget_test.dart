import 'package:app_flutter/app.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('shows the five-page security UI shell', (tester) async {
    await tester.pumpWidget(const FaceSecurityApp());

    expect(find.text('AI Face Recognition Security System'), findsOneWidget);
    expect(find.text('Dashboard'), findsWidgets);
    expect(find.text('Register'), findsOneWidget);
    expect(find.text('Surveillance'), findsOneWidget);
    expect(find.text('Logs'), findsOneWidget);

    await tester.tap(find.byIcon(Icons.person_add_alt_1_outlined));
    await tester.pumpAndSettle();

    expect(find.text('Person name'), findsOneWidget);
    expect(find.text('No images selected'), findsOneWidget);
  });
}
