import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/glass_card.dart';
import '../auth/auth_providers.dart';
import '../../home/presentation/home_screen.dart';
import '../../onboarding/presentation/onboarding_screen.dart';
import '../../profile/profile_providers.dart';
import '../../welcome/welcome_screen.dart';

class AuthGate extends ConsumerWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authStateProvider);
    return authState.when(
      data: (user) {
        if (user == null) {
          return const WelcomeScreen();
        }
        final profileStatus = ref.watch(userProfileStatusProvider(user.uid));
        return profileStatus.when(
          data: (hasProfile) => hasProfile ? const HomeScreen() : const OnboardingScreen(),
          loading: () => const _LoadingScreen(),
          error: (error, _) => _ErrorScreen(message: error.toString()),
        );
      },
      loading: () => const _LoadingScreen(),
      error: (error, _) => _ErrorScreen(message: error.toString()),
    );
  }
}

class _LoadingScreen extends StatelessWidget {
  const _LoadingScreen();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: const Center(child: CircularProgressIndicator()),
    );
  }
}

class _ErrorScreen extends StatelessWidget {
  final String message;

  const _ErrorScreen({required this.message});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: Center(
        child: GlassCard(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              'Something went wrong:\n$message',
              style: const TextStyle(color: AppTheme.textPrimary, fontSize: 16),
              textAlign: TextAlign.center,
            ),
          ),
        ),
      ),
    );
  }
}
