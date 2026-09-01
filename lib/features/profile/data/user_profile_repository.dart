import 'package:cloud_firestore/cloud_firestore.dart';
import '../models/user_profile.dart';

class UserProfileRepository {
  final FirebaseFirestore _firestore;

  UserProfileRepository({FirebaseFirestore? firestore}) : _firestore = firestore ?? FirebaseFirestore.instance;

  CollectionReference get _users => _firestore.collection('users');

  Future<bool> userHasProfile(String uid) async {
    final snapshot = await _users.doc(uid).get();
    return snapshot.exists && (snapshot.data() as Map<String, dynamic>?)?['onboarded'] == true;
  }

  Future<UserProfile?> fetchUserProfile(String uid) async {
    final snapshot = await _users.doc(uid).get();
    if (!snapshot.exists) return null;
    final data = snapshot.data() as Map<String, dynamic>;
    return UserProfile.fromMap(data);
  }

  Future<void> saveUserProfile(UserProfile profile) async {
    await _users.doc(profile.uid).set(profile.toMap(), SetOptions(merge: true));
  }
}
