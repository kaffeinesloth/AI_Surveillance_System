import 'dart:typed_data';

import 'package:app_flutter/services/member_service.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('registerMember uploads byte-backed picked images', () async {
    late http.Request capturedRequest;
    final client = MockClient((request) async {
      capturedRequest = request;
      return http.Response(
        '{"member":{"id":1,"name":"Tuan","created_at":"now",'
        '"image_count":1},'
        '"accepted_images":[{"filename":"face.jpg","status":"accepted",'
        '"reason":"Face crop and embedding saved."}],'
        '"rejected_images":[],"message":"Registered Tuan with 1 image(s)."}',
        200,
      );
    });
    final service = MemberService(client: client);

    final result = await service.registerMember(
      name: 'Tuan',
      images: [
        PlatformFile(
          name: 'face.jpg',
          size: 3,
          bytes: Uint8List.fromList([1, 2, 3]),
        ),
      ],
    );

    expect(result.acceptedImages.single.filename, 'face.jpg');
    expect(capturedRequest.method, 'POST');
    expect(capturedRequest.url.path, '/members/register');
    expect(
      capturedRequest.headers['content-type'],
      contains('multipart/form-data'),
    );
    expect(
        String.fromCharCodes(capturedRequest.bodyBytes), contains('face.jpg'));
  });
}
