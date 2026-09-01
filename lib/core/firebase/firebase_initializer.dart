import 'package:firebase_core/firebase_core.dart';

class FirebaseInitializer {
  static Future<FirebaseApp> initialize() async {
    return Firebase.initializeApp();
  }
}
