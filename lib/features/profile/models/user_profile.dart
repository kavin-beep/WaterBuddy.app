class UserProfile {
  final String uid;
  final String name;
  final String email;
  final int age;
  final double height;
  final double weight;
  final String gender;
  final String occupation;
  final String activityLevel;
  final String wakeUpTime;
  final String sleepTime;
  final bool onboarded;

  UserProfile({
    required this.uid,
    required this.name,
    required this.email,
    required this.age,
    required this.height,
    required this.weight,
    required this.gender,
    required this.occupation,
    required this.activityLevel,
    required this.wakeUpTime,
    required this.sleepTime,
    this.onboarded = false,
  });

  Map<String, dynamic> toMap() {
    return {
      'uid': uid,
      'name': name,
      'email': email,
      'age': age,
      'height': height,
      'weight': weight,
      'gender': gender,
      'occupation': occupation,
      'activityLevel': activityLevel,
      'wakeUpTime': wakeUpTime,
      'sleepTime': sleepTime,
      'onboarded': onboarded,
    };
  }

  factory UserProfile.fromMap(Map<String, dynamic> data) {
    return UserProfile(
      uid: data['uid'] as String,
      name: data['name'] as String? ?? '',
      email: data['email'] as String? ?? '',
      age: (data['age'] as num?)?.toInt() ?? 0,
      height: (data['height'] as num?)?.toDouble() ?? 0,
      weight: (data['weight'] as num?)?.toDouble() ?? 0,
      gender: data['gender'] as String? ?? '',
      occupation: data['occupation'] as String? ?? '',
      activityLevel: data['activityLevel'] as String? ?? '',
      wakeUpTime: data['wakeUpTime'] as String? ?? '',
      sleepTime: data['sleepTime'] as String? ?? '',
      onboarded: data['onboarded'] as bool? ?? false,
    );
  }
}
