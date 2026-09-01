import 'package:flutter/material.dart';

class MascotWidget extends StatefulWidget {
  final String emotion;

  const MascotWidget({super.key, required this.emotion});

  @override
  State<MascotWidget> createState() => _MascotWidgetState();
}

class _MascotWidgetState extends State<MascotWidget> with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _bounceAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 700),
    );
    _bounceAnimation = CurvedAnimation(parent: _controller, curve: Curves.easeOutBack);
    _controller.forward();
  }

  @override
  void didUpdateWidget(covariant MascotWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.emotion != widget.emotion) {
      _controller.forward(from: 0);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isHappy = widget.emotion == 'happy' || widget.emotion == 'celebrate';
    final baseColor = isHappy ? const Color(0xFF4DD0E1) : const Color(0xFF1E88E5);
    final accentColor = isHappy ? const Color(0xFF87F7FF) : const Color(0xFF3DD6FF);

    return AnimatedBuilder(
      animation: _bounceAnimation,
      builder: (context, child) {
        final scale = isHappy ? 1.0 + (_bounceAnimation.value * 0.08) : 1.0 + (_bounceAnimation.value * 0.03);
        final offset = isHappy ? -8 + (_bounceAnimation.value * 6) : -4 + (_bounceAnimation.value * 2);

        return Transform.translate(
          offset: Offset(0, offset),
          child: Transform.scale(
            scale: scale,
            child: ClipPath(
              clipper: _DropClipper(),
              child: Container(
                width: 118,
                height: 132,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [baseColor, accentColor],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.16),
                      blurRadius: 18,
                      offset: const Offset(0, 10),
                    ),
                  ],
                ),
                child: Stack(
                  children: [
                    Positioned(
                      top: 24,
                      left: 24,
                      child: Icon(
                        Icons.water_drop_rounded,
                        color: Colors.white.withOpacity(0.8),
                        size: 28,
                      ),
                    ),
                    Center(
                      child: Text(
                        isHappy ? '😊' : '💧',
                        style: TextStyle(fontSize: isHappy ? 42 : 38),
                      ),
                    ),
                    if (isHappy)
                      Positioned(
                        top: 20,
                        right: 18,
                        child: Text('✨', style: const TextStyle(fontSize: 20)),
                      ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

class _DropClipper extends CustomClipper<Path> {
  @override
  Path getClip(Size size) {
    final path = Path();
    path.moveTo(size.width / 2, 0);
    path.quadraticBezierTo(size.width * 0.95, size.height * 0.25, size.width * 0.62, size.height);
    path.quadraticBezierTo(size.width * 0.5, size.height * 0.95, size.width * 0.38, size.height);
    path.quadraticBezierTo(size.width * 0.05, size.height * 0.25, size.width / 2, 0);
    return path..close();
  }

  @override
  bool shouldReclip(covariant CustomClipper<Path> oldClipper) => false;
}
