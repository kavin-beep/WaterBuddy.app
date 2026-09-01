import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/glass_card.dart';
import '../auth_providers.dart';
import 'email_auth_screen.dart';

class AuthScreen extends ConsumerWidget {
  const AuthScreen({super.key});

  void _openEmailAuth(BuildContext context) {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const EmailAuthScreen()),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 24),
              const Text(
                'Welcome back to Water Buddy',
                style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
              ),
              const SizedBox(height: 12),
              const Text(
                'Sign in with your email or Google account to continue tracking your hydration.',
                style: TextStyle(fontSize: 16, color: AppTheme.textSecondary, height: 1.5),
              ),
              const SizedBox(height: 32),
              GlassCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    ElevatedButton.icon(
                      onPressed: () async {
                        final auth = ref.read(authRepositoryProvider);
                        try {
                          await auth.signInWithGoogle();
                          if (context.mounted) {
                            Navigator.of(context).pop();
                          }
                        } catch (error) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text(error.toString())),
                          );
                        }
                      },
                      icon: const Icon(Icons.login),
                      label: const Text('Continue with Google'),
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton(
                      onPressed: () => _openEmailAuth(context),
                      child: const Text('Sign in with Email'),
                    ),
                  ],
                ),
              ),
              const Spacer(),
              TextButton(
                onPressed: () {},
                child: const Text('Continue as guest'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
