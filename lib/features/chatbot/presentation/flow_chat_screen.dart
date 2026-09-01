import 'dart:async';

import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/glass_card.dart';
import '../../mascot/mascot_widget.dart';

class FlowChatScreen extends StatefulWidget {
  const FlowChatScreen({super.key});

  @override
  State<FlowChatScreen> createState() => _FlowChatScreenState();
}

class _FlowChatScreenState extends State<FlowChatScreen> {
  final _controller = TextEditingController();
  Timer? _mascotResetTimer;
  String _mascotEmotion = 'wave';
  final List<Map<String, String>> _messages = [
    {'sender': 'flow', 'message': 'Hi Jordan! I\'m FLOW, your hydration coach. How can I help you today?'},
  ];

  void _triggerMascotReaction(String message) {
    final shouldCelebrate = RegExp(r'water|hydrate|drink|sip|bottle|wet|liquid', caseSensitive: false).hasMatch(message);
    if (!shouldCelebrate) return;

    setState(() => _mascotEmotion = 'happy');
    _mascotResetTimer?.cancel();
    _mascotResetTimer = Timer(const Duration(milliseconds: 1200), () {
      if (mounted) {
        setState(() => _mascotEmotion = 'wave');
      }
    });
  }

  void _sendMessage() {
    final text = _controller.text.trim();
    if (text.isEmpty) return;

    _triggerMascotReaction(text);

    setState(() {
      _messages.add({'sender': 'user', 'message': text});
      _messages.add({'sender': 'flow', 'message': 'That sounds great! Remember to hydrate regularly and keep your streak going.'});
      _controller.clear();
    });
  }

  @override
  void dispose() {
    _mascotResetTimer?.cancel();
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      appBar: AppBar(
        title: const Text('FLOW Chat'),
        backgroundColor: AppTheme.primary,
        elevation: 0,
      ),
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.only(top: 16, bottom: 8),
              child: Column(
                children: [
                  MascotWidget(emotion: _mascotEmotion),
                  const SizedBox(height: 8),
                  Text(
                    'Water drops make FLOW smile ✨',
                    style: TextStyle(color: AppTheme.textPrimary.withOpacity(0.8), fontSize: 13),
                  ),
                ],
              ),
            ),
            Expanded(
              child: ListView.builder(
                padding: const EdgeInsets.all(20),
                itemCount: _messages.length,
                itemBuilder: (context, index) {
                  final message = _messages[index];
                  final isFlow = message['sender'] == 'flow';
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Align(
                      alignment: isFlow ? Alignment.centerLeft : Alignment.centerRight,
                      child: GlassCard(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Text(
                            message['message']!,
                            style: TextStyle(color: isFlow ? AppTheme.textPrimary : AppTheme.primary),
                          ),
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      decoration: InputDecoration(
                        hintText: 'Ask FLOW a question',
                        filled: true,
                        fillColor: Colors.white,
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(18), borderSide: BorderSide.none),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  ElevatedButton(
                    onPressed: _sendMessage,
                    style: ElevatedButton.styleFrom(shape: const CircleBorder(), padding: const EdgeInsets.all(16)),
                    child: const Icon(Icons.send),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
