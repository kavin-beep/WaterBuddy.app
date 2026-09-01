import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'data/user_profile_repository.dart';

final userProfileRepositoryProvider = Provider<UserProfileRepository>((ref) {
  return UserProfileRepository();
});

final userProfileStatusProvider = FutureProvider.family<bool, String>((ref, uid) async {
  final repository = ref.read(userProfileRepositoryProvider);
  return repository.userHasProfile(uid);
});
