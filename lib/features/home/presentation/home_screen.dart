import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/glass_card.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  int _currentIntake = 950;
  final int _dailyGoal = 2500;

  void _incrementIntake(int amount) {
    setState(() {
      _currentIntake += amount;
    });
  }

  @override
  Widget build(BuildContext context) {
    final progress = (_currentIntake / _dailyGoal).clamp(0.0, 1.0);
    final percent = (progress * 100).round();

    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: const Text('Water Buddy'),
        backgroundColor: AppTheme.primary,
        elevation: 0,
        actions: [
          IconButton(
            onPressed: () {},
            icon: const Icon(Icons.settings_outlined),
          ),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Good morning, Jordan',
                style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
              ),
              const SizedBox(height: 8),
              const Text(
                'Your hydration summary for today',
                style: TextStyle(fontSize: 16, color: AppTheme.textSecondary),
              ),
              const SizedBox(height: 24),
              GlassCard(
                padding: const EdgeInsets.all(22),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: const [
                            Text('Daily goal', style: TextStyle(fontSize: 12, color: AppTheme.textSecondary)),
                            SizedBox(height: 6),
                            Text('2,500 ml', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                          ],
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 14),
                          decoration: BoxDecoration(
                            color: AppTheme.accent.withOpacity(0.18),
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: const Text('Streak: 7 days', style: TextStyle(fontWeight: FontWeight.w600, color: AppTheme.primary)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 22),
                    Row(
                      children: [
                        Expanded(
                          flex: 2,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('$_currentIntake ml', style: Theme.of(context).textTheme.displaySmall?.copyWith(fontSize: 38)),
                              const SizedBox(height: 6),
                              Text('$percent% completed', style: const TextStyle(color: AppTheme.textSecondary)),
                            ],
                          ),
                        ),
                        Expanded(
                          child: Container(
                            height: 160,
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(34),
                              gradient: const LinearGradient(
                                colors: [Color(0xFF3DD6FF), Color(0xFF2196F3)],
                                begin: Alignment.topCenter,
                                end: Alignment.bottomCenter,
                              ),
                              boxShadow: [
                                BoxShadow(color: AppTheme.primary.withOpacity(0.22), blurRadius: 24, offset: const Offset(0, 14)),
                              ],
                            ),
                            child: Stack(
                              alignment: Alignment.bottomCenter,
                              children: [
                                Positioned(
                                  top: 16,
                                  left: 0,
                                  right: 0,
                                  child: Column(
                                    children: const [
                                      Icon(Icons.water_drop, color: Colors.white, size: 34),
                                      SizedBox(height: 6),
                                      Text('FLOW', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                                    ],
                                  ),
                                ),
                                FractionallySizedBox(
                                  heightFactor: progress,
                                  child: Container(
                                    width: double.infinity,
                                    decoration: BoxDecoration(
                                      color: Colors.white.withOpacity(0.32),
                                      borderRadius: const BorderRadius.vertical(bottom: Radius.circular(34)),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              GlassCard(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Text('Quick log', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 14),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: [250, 500, 750, 1000].map((amount) {
                        return ElevatedButton(
                          onPressed: () => _incrementIntake(amount),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.white,
                            foregroundColor: AppTheme.primary,
                            elevation: 0,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                          ),
                          child: Text('+$amount ml'),
                        );
                      }).toList(),
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      keyboardType: TextInputType.number,
                      decoration: InputDecoration(
                        filled: true,
                        fillColor: AppTheme.background,
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide.none),
                        hintText: 'Custom amount',
                        suffixIcon: IconButton(
                          icon: const Icon(Icons.add),
                          onPressed: () {},
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              GlassCard(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Text('Daily hydration tip', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 12),
                    const Text(
                      'FLOW says: drink a glass of water before every meal to improve digestion and keep your energy steady.',
                      style: TextStyle(color: AppTheme.textSecondary, height: 1.5),
                    ),
                    const SizedBox(height: 20),
                    ElevatedButton(
                      onPressed: () {},
                      style: ElevatedButton.styleFrom(backgroundColor: AppTheme.accent, foregroundColor: AppTheme.textPrimary),
                      child: const Text('Chat with FLOW'),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              GlassCard(
                padding: const EdgeInsets.all(20),
                child: Row(
                  children: [
                    Container(
                      height: 68,
                      width: 68,
                      decoration: BoxDecoration(
                        color: AppTheme.accent,
                        borderRadius: BorderRadius.circular(22),
                      ),
                      child: const Icon(Icons.water_drop, size: 36, color: Colors.white),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: const [
                          Text('FLOW is cheering for you!', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                          SizedBox(height: 6),
                          Text('Keep logging water and your animated buddy will celebrate your streak.', style: TextStyle(color: AppTheme.textSecondary, height: 1.5)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
