import 'package:flutter/material.dart';

class AppTheme {
  static const Color primary = Color(0xFF2196F3);
  static const Color accent = Color(0xFF3DD6FF);
  static const Color background = Color(0xFFF4FBFF);
  static const Color surface = Colors.white;
  static const Color success = Color(0xFF2E7D32);
  static const Color textPrimary = Color(0xFF0F172A);
  static const Color textSecondary = Color(0xFF64748B);

  static final ThemeData lightTheme = ThemeData(
    colorScheme: const ColorScheme.light(
      primary: primary,
      secondary: accent,
      background: background,
      surface: surface,
    ),
    scaffoldBackgroundColor: background,
    textTheme: const TextTheme(
      headlineLarge: TextStyle(fontSize: 34, fontWeight: FontWeight.bold, color: textPrimary),
      headlineMedium: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: textPrimary),
      headlineSmall: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: textPrimary),
      titleLarge: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: textPrimary),
      bodyLarge: TextStyle(fontSize: 16, color: textPrimary),
      bodyMedium: TextStyle(fontSize: 14, color: textSecondary),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: primary,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: primary,
        backgroundColor: Colors.white,
        side: const BorderSide(color: primary, width: 1.5),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
      ),
    ),
  );
}
