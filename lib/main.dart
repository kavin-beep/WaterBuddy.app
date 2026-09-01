import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/firebase/firebase_initializer.dart';
import 'core/theme/app_theme.dart';
import 'features/auth/presentation/auth_gate.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await FirebaseInitializer.initialize();
  runApp(const ProviderScope(child: WaterBuddyApp()));
}

class WaterBuddyApp extends StatelessWidget {
  const WaterBuddyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Water Buddy',
      theme: AppTheme.lightTheme,
      debugShowCheckedModeBanner: false,
      home: const AuthGate(),
    );
  }
}
