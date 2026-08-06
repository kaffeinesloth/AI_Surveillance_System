class CameraModel {
  const CameraModel({
    required this.id,
    required this.name,
    required this.source,
    required this.isActive,
    this.location,
  });

  factory CameraModel.fromJson(Map<String, dynamic> json) => CameraModel(
        id: json['id'] as int,
        name: json['name'] as String,
        source: json['source'] as String,
        location: json['location'] as String?,
        isActive: json['is_active'] as bool,
      );

  final int id;
  final String name;
  final String source;
  final String? location;
  final bool isActive;
}

class SurveillanceStatusModel {
  const SurveillanceStatusModel({
    required this.state,
    required this.running,
    required this.framesProcessed,
    required this.fps,
    this.cameraId,
    this.sessionId,
    this.errorMessage,
  });

  factory SurveillanceStatusModel.fromJson(Map<String, dynamic> json) =>
      SurveillanceStatusModel(
        state: json['state'] as String,
        running: json['running'] as bool,
        cameraId: json['camera_id'] as int?,
        sessionId: json['session_id'] as int?,
        framesProcessed: json['frames_processed'] as int,
        fps: (json['fps'] as num).toDouble(),
        errorMessage: json['error_message'] as String?,
      );

  final String state;
  final bool running;
  final int? cameraId;
  final int? sessionId;
  final int framesProcessed;
  final double fps;
  final String? errorMessage;
}

class AnalysisTrackModel {
  const AnalysisTrackModel({
    required this.trackId,
    required this.status,
    required this.personConfidence,
    this.memberName,
    this.similarity,
  });

  factory AnalysisTrackModel.fromJson(Map<String, dynamic> json) =>
      AnalysisTrackModel(
        trackId: json['track_id'] as int,
        status: json['status'] as String,
        personConfidence: (json['person_confidence'] as num).toDouble(),
        memberName: json['member_name'] as String?,
        similarity: (json['similarity'] as num?)?.toDouble(),
      );

  final int trackId;
  final String status;
  final double personConfidence;
  final String? memberName;
  final double? similarity;
}

class LatestAnalysisModel {
  const LatestAnalysisModel({required this.frameIndex, required this.tracks});

  factory LatestAnalysisModel.fromJson(Map<String, dynamic> json) =>
      LatestAnalysisModel(
        frameIndex: json['frame_index'] as int,
        tracks: (json['tracks'] as List<dynamic>)
            .map(
              (item) =>
                  AnalysisTrackModel.fromJson(item as Map<String, dynamic>),
            )
            .toList(),
      );

  final int frameIndex;
  final List<AnalysisTrackModel> tracks;
}

class VideoAnalysisStatusModel {
  const VideoAnalysisStatusModel({
    required this.jobId,
    required this.filename,
    required this.state,
    required this.persistent,
    required this.processedFrames,
    required this.processingFps,
    this.totalFrames,
    this.progress,
    this.errorMessage,
  });

  factory VideoAnalysisStatusModel.fromJson(Map<String, dynamic> json) =>
      VideoAnalysisStatusModel(
        jobId: json['job_id'] as String,
        filename: json['filename'] as String,
        state: json['state'] as String,
        persistent: json['persistent'] as bool,
        processedFrames: json['processed_frames'] as int,
        totalFrames: json['total_frames'] as int?,
        progress: (json['progress'] as num?)?.toDouble(),
        processingFps: (json['processing_fps'] as num).toDouble(),
        errorMessage: json['error_message'] as String?,
      );

  bool get isActive => state == 'queued' || state == 'running';

  final String jobId;
  final String filename;
  final String state;
  final bool persistent;
  final int processedFrames;
  final int? totalFrames;
  final double? progress;
  final double processingFps;
  final String? errorMessage;
}

class TemporaryVideoEventModel {
  const TemporaryVideoEventModel({
    required this.frameIndex,
    required this.timestampSeconds,
    required this.trackId,
    required this.status,
    required this.eventType,
    this.memberName,
    this.similarity,
  });

  factory TemporaryVideoEventModel.fromJson(Map<String, dynamic> json) =>
      TemporaryVideoEventModel(
        frameIndex: json['frame_index'] as int,
        timestampSeconds: (json['timestamp_seconds'] as num).toDouble(),
        trackId: json['track_id'] as int,
        status: json['status'] as String,
        eventType: json['event_type'] as String,
        memberName: json['member_name'] as String?,
        similarity: (json['similarity'] as num?)?.toDouble(),
      );

  final int frameIndex;
  final double timestampSeconds;
  final int trackId;
  final String status;
  final String eventType;
  final String? memberName;
  final double? similarity;
}

class VideoAnalysisResultsModel {
  const VideoAnalysisResultsModel({
    required this.state,
    required this.persistent,
    required this.knownEvents,
    required this.unknownEvents,
    required this.events,
  });

  factory VideoAnalysisResultsModel.fromJson(Map<String, dynamic> json) {
    final summary = json['summary'] as Map<String, dynamic>;
    return VideoAnalysisResultsModel(
      state: json['state'] as String,
      persistent: json['persistent'] as bool,
      knownEvents: summary['known_events'] as int,
      unknownEvents: summary['unknown_events'] as int,
      events: (json['events'] as List<dynamic>)
          .map(
            (item) =>
                TemporaryVideoEventModel.fromJson(item as Map<String, dynamic>),
          )
          .toList(),
    );
  }

  final String state;
  final bool persistent;
  final int knownEvents;
  final int unknownEvents;
  final List<TemporaryVideoEventModel> events;
}

class DetectionLogModel {
  const DetectionLogModel({
    required this.id,
    required this.status,
    required this.cameraName,
    required this.detectedAt,
    this.memberName,
    this.confidence,
  });

  factory DetectionLogModel.fromJson(Map<String, dynamic> json) =>
      DetectionLogModel(
        id: json['id'] as int,
        status: json['status'] as String,
        memberName: json['member_name'] as String?,
        cameraName: json['camera_name'] as String,
        confidence: (json['confidence'] as num?)?.toDouble(),
        detectedAt: json['detected_at'] as String,
      );

  final int id;
  final String status;
  final String? memberName;
  final String cameraName;
  final double? confidence;
  final String detectedAt;
}

class AlertModel {
  const AlertModel({
    required this.id,
    required this.alertType,
    required this.message,
    required this.cameraName,
    required this.isRead,
    required this.createdAt,
    this.snapshotUrl,
  });

  factory AlertModel.fromJson(Map<String, dynamic> json) => AlertModel(
        id: json['id'] as int,
        alertType: json['alert_type'] as String,
        message: json['message'] as String,
        cameraName: json['camera_name'] as String,
        isRead: json['is_read'] as bool,
        createdAt: json['created_at'] as String,
        snapshotUrl: json['snapshot_url'] as String?,
      );

  final int id;
  final String alertType;
  final String message;
  final String cameraName;
  final bool isRead;
  final String createdAt;
  final String? snapshotUrl;
}
