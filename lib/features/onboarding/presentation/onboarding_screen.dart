import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/glass_card.dart';
import '../../home/presentation/home_screen.dart';
import '../../profile/models/user_profile.dart';
import '../../profile/profile_providers.dart';
import '../../auth/auth_providers.dart';

class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _ageController = TextEditingController();
  final _heightController = TextEditingController();
  final _weightController = TextEditingController();
  final _occupationController = TextEditingController();

  String _gender = 'Female';
  String _activityLevel = 'Moderate';
  TimeOfDay _wakeUpTime = const TimeOfDay(hour: 7, minute: 0);
  TimeOfDay _sleepTime = const TimeOfDay(hour: 22, minute: 0);
  bool _isSaving = false;

  Future<void> _pickTime(BuildContext context, bool isWakeUp) async {
    final time = await showTimePicker(
      context: context,
      initialTime: isWakeUp ? _wakeUpTime : _sleepTime,
    );
    if (time != null) {
      setState(() {
        if (isWakeUp) {
          _wakeUpTime = time;
        } else {
          _sleepTime = time;
        }
      });
    }
  }

  Future<void> _saveProfile() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isSaving = true;
    });

    final user = ref.read(authRepositoryProvider).currentUser;
    if (user == null) {
      setState(() {
        _isSaving = false;
      });
      return;
    }

    final profile = UserProfile(
      uid: user.uid,
      name: _nameController.text.trim(),
      email: user.email ?? '',
      age: int.tryParse(_ageController.text.trim()) ?? 0,
      height: double.tryParse(_heightController.text.trim()) ?? 0,
      weight: double.tryParse(_weightController.text.trim()) ?? 0,
      gender: _gender,
      occupation: _occupationController.text.trim(),
      activityLevel: _activityLevel,
      wakeUpTime: _wakeUpTime.format(context),
      sleepTime: _sleepTime.format(context),
      onboarded: true,
    );

    try {
      await ref.read(userProfileRepositoryProvider).saveUserProfile(profile);
      if (context.mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => const HomeScreen()),
        );
      }
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(error.toString())),
        );
      }
    } finally {
      setState(() {
        _isSaving = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: const Text('Complete your onboarding'),
        backgroundColor: AppTheme.primary,
        elevation: 0,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
          child: GlassCard(
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    'Tell us a little about you',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 20),
                  TextFormField(
                    controller: _nameController,
                    decoration: const InputDecoration(labelText: 'Name'),
                    validator: (value) => value?.isEmpty == true ? 'Please enter your name' : null,
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _ageController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Age'),
                    validator: (value) => (value == null || value.isEmpty) ? 'Please enter your age' : null,
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: TextFormField(
                          controller: _heightController,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(labelText: 'Height (cm)'),
                          validator: (value) => (value == null || value.isEmpty) ? 'Enter height' : null,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextFormField(
                          controller: _weightController,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(labelText: 'Weight (kg)'),
                          validator: (value) => (value == null || value.isEmpty) ? 'Enter weight' : null,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<String>(
                    value: _gender,
                    items: const [
                      DropdownMenuItem(value: 'Female', child: Text('Female')),
                      DropdownMenuItem(value: 'Male', child: Text('Male')),
                      DropdownMenuItem(value: 'Other', child: Text('Other')),
                    ],
                    onChanged: (value) {
                      if (value != null) {
                        setState(() {
                          _gender = value;
                        });
                      }
                    },
                    decoration: const InputDecoration(labelText: 'Gender'),
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _occupationController,
                    decoration: const InputDecoration(labelText: 'Occupation'),
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<String>(
                    value: _activityLevel,
                    items: const [
                      DropdownMenuItem(value: 'Low', child: Text('Low')),
                      DropdownMenuItem(value: 'Moderate', child: Text('Moderate')),
                      DropdownMenuItem(value: 'High', child: Text('High')),
                    ],
                    onChanged: (value) {
                      if (value != null) {
                        setState(() {
                          _activityLevel = value;
                        });
                      }
                    },
                    decoration: const InputDecoration(labelText: 'Activity level'),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: _TimeField(
                          label: 'Wake-up',
                          time: _wakeUpTime,
                          onTap: () => _pickTime(context, true),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _TimeField(
                          label: 'Sleep',
                          time: _sleepTime,
                          onTap: () => _pickTime(context, false),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  ElevatedButton(
                    onPressed: _isSaving ? null : _saveProfile,
                    child: _isSaving ? const CircularProgressIndicator(color: Colors.white) : const Text('Save profile'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _TimeField extends StatelessWidget {
  final String label;
  final TimeOfDay time;
  final VoidCallback onTap;

  const _TimeField({required this.label, required this.time, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AbsorbPointer(
        child: TextFormField(
          decoration: InputDecoration(labelText: label, hintText: time.format(context)),
        ),
      ),
    );
  }
}
