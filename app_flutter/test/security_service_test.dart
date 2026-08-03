import 'dart:typed_data';

import 'package:app_flutter/services/security_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('parses camera and surveillance contracts', () async {
    final client = MockClient((request) async {
      if (request.url.path == '/cameras') {
        return http.Response(
          '[{"id":1,"name":"Laptop webcam","source":"0",'
          '"location":"Desk","is_active":true,'
          '"created_at":"now","updated_at":"now"}]',
          200,
        );
      }
      return http.Response(
        '{"state":"running","running":true,"camera_id":1,"session_id":4,'
        '"frames_processed":25,"fps":12.5,"started_at":"now",'
        '"error_message":null}',
        200,
      );
    });
    final service = SecurityService(
      client: client,
      baseUrl: 'http://backend.test',
    );

    final cameras = await service.listCameras();
    final status = await service.surveillanceStatus();

    expect(cameras.single.source, '0');
    expect(status.running, isTrue);
    expect(status.sessionId, 4);
    expect(status.fps, 12.5);
  });

  test('temporary video results preserve the non-persistent marker', () async {
    final client = MockClient(
      (request) async => http.Response(
        '{"job_id":"job-1","filename":"demo.mp4","state":"completed",'
        '"persistent":false,"summary":{"total_frames":5,'
        '"duration_seconds":1.0,"average_processing_fps":5.0,'
        '"known_events":1,"unknown_events":0,"events_truncated":false},'
        '"events":[{"frame_index":3,"timestamp_seconds":0.6,"track_id":2,'
        '"status":"known","member_id":1,"member_name":"Tuan",'
        '"similarity":0.91,"event_type":"known_identity"}],'
        '"error_message":null}',
        200,
      ),
    );
    final service = SecurityService(
      client: client,
      baseUrl: 'http://backend.test',
    );

    final results = await service.videoResults('job-1');

    expect(results.persistent, isFalse);
    expect(results.knownEvents, 1);
    expect(results.events.single.memberName, 'Tuan');
  });

  test('submitVideo uploads byte-backed picked videos', () async {
    late http.Request capturedRequest;
    final client = MockClient((request) async {
      capturedRequest = request;
      return http.Response(
        '{"job_id":"job-1","filename":"demo.mp4","state":"queued",'
        '"persistent":true,"processed_frames":0,"total_frames":null,'
        '"progress":null,"processing_fps":0.0,"error_message":null}',
        200,
      );
    });
    final service = SecurityService(
      client: client,
      baseUrl: 'http://backend.test',
    );

    final status = await service.submitVideo(
      bytes: Uint8List.fromList([1, 2, 3]),
      filename: 'demo.mp4',
    );

    expect(status.jobId, 'job-1');
    expect(capturedRequest.method, 'POST');
    expect(capturedRequest.url.path, '/video-analysis');
    expect(
      capturedRequest.headers['content-type'],
      contains('multipart/form-data'),
    );
    expect(
      String.fromCharCodes(capturedRequest.bodyBytes),
      contains('demo.mp4'),
    );
  });

  test('submitVideo uploads stream-backed picked videos', () async {
    late http.Request capturedRequest;
    final client = MockClient((request) async {
      capturedRequest = request;
      return http.Response(
        '{"job_id":"job-2","filename":"stream.mp4","state":"queued",'
        '"persistent":true,"processed_frames":0,"total_frames":null,'
        '"progress":null,"processing_fps":0.0,"error_message":null}',
        200,
      );
    });
    final service = SecurityService(
      client: client,
      baseUrl: 'http://backend.test',
    );

    final status = await service.submitVideo(
      stream: Stream<List<int>>.fromIterable([
        [1, 2],
        [3],
      ]),
      length: 3,
      filename: 'stream.mp4',
    );

    expect(status.jobId, 'job-2');
    expect(capturedRequest.method, 'POST');
    expect(capturedRequest.url.path, '/video-analysis');
    expect(
      capturedRequest.headers['content-type'],
      contains('multipart/form-data'),
    );
    expect(
      String.fromCharCodes(capturedRequest.bodyBytes),
      contains('stream.mp4'),
    );
  });

  test('backend detail becomes an ApiException', () async {
    final client = MockClient(
      (request) async =>
          http.Response('{"detail":"Stop live surveillance first"}', 409),
    );
    final service = SecurityService(
      client: client,
      baseUrl: 'http://backend.test',
    );

    expect(
      service.startSurveillance(1),
      throwsA(
        isA<ApiException>().having(
          (error) => error.message,
          'message',
          'Stop live surveillance first',
        ),
      ),
    );
  });

  test('deleteLog calls the persistent log delete endpoint', () async {
    Uri? requestedUrl;
    final client = MockClient((request) async {
      requestedUrl = request.url;
      return http.Response(
        '{"message":"Detection log deleted",'
        '"deleted_log_id":7,"deleted_snapshot":true}',
        200,
      );
    });
    final service = SecurityService(
      client: client,
      baseUrl: 'http://backend.test',
    );

    await service.deleteLog(7);

    expect(requestedUrl?.path, '/logs/7');
  });

  test('delete helpers call persistent delete endpoints', () async {
    final requestedPaths = <String>[];
    final client = MockClient((request) async {
      requestedPaths.add(request.url.path);
      return http.Response('{}', 200);
    });
    final service = SecurityService(
      client: client,
      baseUrl: 'http://backend.test',
    );

    await service.deleteAllLogs();
    await service.deleteAlert(8);
    await service.deleteAllAlerts();

    expect(requestedPaths, ['/logs/all', '/alerts/8', '/alerts/all']);
  });
}
