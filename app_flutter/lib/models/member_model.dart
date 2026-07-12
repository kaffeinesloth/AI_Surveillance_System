class MemberModel {
  const MemberModel({
    required this.id,
    required this.name,
    required this.createdAt,
    required this.imageCount,
  });

  final int id;
  final String name;
  final String createdAt;
  final int imageCount;

  factory MemberModel.fromJson(Map<String, dynamic> json) {
    return MemberModel(
      id: json['id'] as int,
      name: json['name'] as String,
      createdAt: json['created_at'] as String,
      imageCount: json['image_count'] as int,
    );
  }
}

class RegistrationImageResult {
  const RegistrationImageResult({
    required this.filename,
    required this.status,
    required this.reason,
  });

  final String filename;
  final String status;
  final String reason;

  factory RegistrationImageResult.fromJson(Map<String, dynamic> json) {
    return RegistrationImageResult(
      filename: json['filename'] as String,
      status: json['status'] as String,
      reason: json['reason'] as String,
    );
  }
}

class RegisterMemberResult {
  const RegisterMemberResult({
    required this.member,
    required this.message,
    required this.acceptedImages,
    required this.rejectedImages,
  });

  final MemberModel member;
  final String message;
  final List<RegistrationImageResult> acceptedImages;
  final List<RegistrationImageResult> rejectedImages;

  factory RegisterMemberResult.fromJson(Map<String, dynamic> json) {
    return RegisterMemberResult(
      member: MemberModel.fromJson(json['member'] as Map<String, dynamic>),
      message: json['message'] as String,
      acceptedImages: _parseImageResults(json['accepted_images']),
      rejectedImages: _parseImageResults(json['rejected_images']),
    );
  }

  static List<RegistrationImageResult> _parseImageResults(dynamic value) {
    final items = value as List<dynamic>? ?? const [];
    return items
        .map(
          (item) => RegistrationImageResult.fromJson(
            item as Map<String, dynamic>,
          ),
        )
        .toList();
  }
}
