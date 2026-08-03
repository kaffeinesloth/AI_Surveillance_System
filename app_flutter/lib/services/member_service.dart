import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:http/http.dart' as http;

import '../core/api_config.dart';
import '../models/member_model.dart';

class MemberService {
  const MemberService({http.Client? client}) : _client = client;

  final http.Client? _client;

  Future<List<MemberModel>> listMembers() async {
    final client = _client ?? http.Client();
    final response = await client.get(
      Uri.parse('${ApiConfig.baseUrl}/members'),
    );

    if (response.statusCode < 200 || response.statusCode >= 300) {
      final message = _extractErrorMessage(response.body);
      throw Exception(message);
    }

    final body = jsonDecode(response.body) as List<dynamic>;
    return body
        .map((item) => MemberModel.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<RegisterMemberResult> registerMember({
    required String name,
    required List<PlatformFile> images,
  }) async {
    final client = _client ?? http.Client();
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('${ApiConfig.baseUrl}/members/register'),
    )..fields['name'] = name;

    for (final image in images) {
      final bytes = image.bytes;
      if (bytes != null) {
        request.files.add(
          http.MultipartFile.fromBytes('images', bytes, filename: image.name),
        );
        continue;
      }

      final path = image.path;
      if (path == null) {
        throw Exception('Image data is not available for ${image.name}.');
      }
      request.files.add(
        await http.MultipartFile.fromPath('images', path, filename: image.name),
      );
    }

    final streamedResponse = await client.send(request);
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode < 200 || response.statusCode >= 300) {
      final message = _extractErrorMessage(response.body);
      throw Exception(message);
    }

    final body = jsonDecode(response.body) as Map<String, dynamic>;
    return RegisterMemberResult.fromJson(body);
  }

  Future<void> deleteMember(int memberId) async {
    final client = _client ?? http.Client();
    final response = await client.delete(
      Uri.parse('${ApiConfig.baseUrl}/members/$memberId'),
    );

    if (response.statusCode < 200 || response.statusCode >= 300) {
      final message = _extractErrorMessage(response.body);
      throw Exception(message);
    }
  }

  static String _extractErrorMessage(String body) {
    try {
      final json = jsonDecode(body) as Map<String, dynamic>;
      final detail = json['detail'];
      if (detail is String && detail.isNotEmpty) {
        return detail;
      }
      if (detail is List && detail.isNotEmpty) {
        return detail
            .map((item) {
              if (item is Map<String, dynamic>) {
                final message = item['msg'];
                final location = item['loc'];
                if (message is String && location is List) {
                  return '${location.join('.')}: $message';
                }
                if (message is String) {
                  return message;
                }
              }
              return item.toString();
            })
            .join('\n');
      }
    } catch (_) {
      // Fall through to the generic message below.
    }
    return 'Registration failed. Please check the backend and try again.';
  }
}
