import 'dart:async';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../models/security_models.dart';
import '../services/security_service.dart';
import '../widgets/app_page.dart';
import '../widgets/empty_panel.dart';
import '../widgets/header_block.dart';
import '../widgets/status_dot.dart';

enum _SurveillanceMode { live, uploadedVideo }

class SurveillanceScreen extends StatefulWidget {
  const SurveillanceScreen({super.key, this.service});

  final SecurityService? service;

  @override
  State<SurveillanceScreen> createState() => _SurveillanceScreenState();
}

class _SurveillanceScreenState extends State<SurveillanceScreen> {
  late final SecurityService _service = widget.service ?? SecurityService();
  _SurveillanceMode _mode = _SurveillanceMode.live;
  List<CameraModel> _cameras = const [];
  int? _selectedCameraId;
  SurveillanceStatusModel? _liveStatus;
  LatestAnalysisModel? _latest;
  Uint8List? _frame;
  VideoAnalysisStatusModel? _videoStatus;
  VideoAnalysisResultsModel? _videoResults;
  Timer? _liveTimer;
  Timer? _videoTimer;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadLive();
  }

  @override
  void dispose() {
    _liveTimer?.cancel();
    _videoTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadLive() async {
    await _guard(() async {
      final values = await Future.wait([
        _service.listCameras(),
        _service.surveillanceStatus(),
      ]);
      final cameras = values[0] as List<CameraModel>;
      final status = values[1] as SurveillanceStatusModel;
      if (!mounted) return;
      setState(() {
        _cameras = cameras;
        _liveStatus = status;
        _selectedCameraId =
            status.cameraId ??
            _selectedCameraId ??
            (cameras.isEmpty ? null : cameras.first.id);
      });
      if (status.running) _startLivePolling();
    });
  }

  Future<void> _addWebcam() async {
    await _guard(() async {
      final camera = await _service.addLaptopWebcam();
      final cameras = await _service.listCameras();
      if (!mounted) return;
      setState(() {
        _cameras = cameras;
        _selectedCameraId = camera.id;
      });
    });
  }

  Future<void> _startLive() async {
    final cameraId = _selectedCameraId;
    if (cameraId == null) return;
    await _guard(() async {
      final status = await _service.startSurveillance(cameraId);
      if (!mounted) return;
      setState(() => _liveStatus = status);
      _startLivePolling();
    });
  }

  Future<void> _stopLive() async {
    await _guard(() async {
      final status = await _service.stopSurveillance();
      _liveTimer?.cancel();
      if (!mounted) return;
      setState(() => _liveStatus = status);
    });
  }

  void _startLivePolling() {
    _liveTimer?.cancel();
    _pollLive();
    _liveTimer = Timer.periodic(
      const Duration(milliseconds: 700),
      (_) => _pollLive(),
    );
  }

  Future<void> _pollLive() async {
    try {
      final status = await _service.surveillanceStatus();
      LatestAnalysisModel? latest;
      Uint8List? frame;
      if (status.running) {
        latest = await _service.latestAnalysis();
        frame = await _service.liveFrame();
      }
      if (!mounted) return;
      setState(() {
        _liveStatus = status;
        if (latest != null) _latest = latest;
        if (frame != null) _frame = frame;
      });
      if (!status.running) _liveTimer?.cancel();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    }
  }

  Future<void> _pickAndAnalyze() async {
    final picked = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['mp4', 'avi', 'mov', 'mkv', 'webm'],
    );
    final file = picked?.files.single;
    if (file == null) return;
    if (file.path == null) {
      setState(() => _error = 'The selected video has no local file path.');
      return;
    }
    await _guard(() async {
      final status = await _service.submitVideo(
        path: file.path!,
        filename: file.name,
      );
      if (!mounted) return;
      setState(() {
        _videoStatus = status;
        _videoResults = null;
        _frame = null;
      });
      _startVideoPolling();
    });
  }

  void _startVideoPolling() {
    _videoTimer?.cancel();
    _pollVideo();
    _videoTimer = Timer.periodic(
      const Duration(milliseconds: 700),
      (_) => _pollVideo(),
    );
  }

  Future<void> _pollVideo() async {
    final jobId = _videoStatus?.jobId;
    if (jobId == null) return;
    try {
      final status = await _service.videoStatus(jobId);
      final results = await _service.videoResults(jobId);
      final frame = await _service.videoFrame(jobId);
      if (!mounted) return;
      setState(() {
        _videoStatus = status;
        _videoResults = results;
        if (frame != null) _frame = frame;
      });
      if (!status.isActive) _videoTimer?.cancel();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    }
  }

  Future<void> _deleteVideo() async {
    final jobId = _videoStatus?.jobId;
    if (jobId == null) return;
    await _guard(() async {
      await _service.deleteVideoJob(jobId);
      _videoTimer?.cancel();
      if (!mounted) return;
      setState(() {
        _videoStatus = null;
        _videoResults = null;
        _frame = null;
      });
    });
  }

  Future<void> _guard(Future<void> Function() operation) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await operation();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppPage(
      children: [
        const HeaderBlock(
          title: 'Surveillance',
          subtitle:
              'Run persistent laptop-webcam monitoring or temporary uploaded-video analysis.',
          icon: Icons.videocam,
        ),
        const SizedBox(height: 16),
        SegmentedButton<_SurveillanceMode>(
          segments: const [
            ButtonSegment(
              value: _SurveillanceMode.live,
              icon: Icon(Icons.videocam),
              label: Text('Live webcam'),
            ),
            ButtonSegment(
              value: _SurveillanceMode.uploadedVideo,
              icon: Icon(Icons.video_file),
              label: Text('Upload video'),
            ),
          ],
          selected: {_mode},
          onSelectionChanged: (value) => setState(() => _mode = value.single),
        ),
        if (_error != null) ...[
          const SizedBox(height: 12),
          MaterialBanner(
            content: Text(_error!),
            actions: [
              TextButton(
                onPressed: () => setState(() => _error = null),
                child: const Text('Dismiss'),
              ),
            ],
          ),
        ],
        const SizedBox(height: 16),
        if (_mode == _SurveillanceMode.live)
          _buildLive(context)
        else
          _buildVideo(context),
      ],
    );
  }

  Widget _buildLive(BuildContext context) {
    final running = _liveStatus?.running ?? false;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Wrap(
              spacing: 12,
              runSpacing: 12,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                if (_cameras.isNotEmpty)
                  SizedBox(
                    width: 280,
                    child: DropdownButtonFormField<int>(
                      initialValue: _selectedCameraId,
                      decoration: const InputDecoration(labelText: 'Camera'),
                      items: _cameras
                          .map(
                            (camera) => DropdownMenuItem(
                              value: camera.id,
                              child: Text(camera.name),
                            ),
                          )
                          .toList(),
                      onChanged: running
                          ? null
                          : (value) =>
                                setState(() => _selectedCameraId = value),
                    ),
                  )
                else
                  OutlinedButton.icon(
                    onPressed: _busy ? null : _addWebcam,
                    icon: const Icon(Icons.add_a_photo_outlined),
                    label: const Text('Add laptop webcam'),
                  ),
                FilledButton.icon(
                  onPressed: !_busy && !running && _selectedCameraId != null
                      ? _startLive
                      : null,
                  icon: const Icon(Icons.play_arrow),
                  label: const Text('Start'),
                ),
                OutlinedButton.icon(
                  onPressed: !_busy && running ? _stopLive : null,
                  icon: const Icon(Icons.stop),
                  label: const Text('Stop'),
                ),
                StatusDot(
                  color: running
                      ? const Color(0xFF22C55E)
                      : const Color(0xFF9CA3AF),
                ),
                Text(
                  running
                      ? '${_liveStatus!.fps.toStringAsFixed(1)} FPS · ${_liveStatus!.framesProcessed} frames'
                      : 'Camera stopped',
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        _framePanel(),
        const SizedBox(height: 12),
        if (_latest == null || _latest!.tracks.isEmpty)
          const EmptyPanel(
            icon: Icons.face_retouching_off_outlined,
            title: 'No live detection result',
            message: 'Start the camera to see recognized and unknown people.',
            compact: true,
          )
        else
          ..._latest!.tracks.map(_trackTile),
      ],
    );
  }

  Widget _buildVideo(BuildContext context) {
    final status = _videoStatus;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  'Temporary mode: events and frames are not saved to history.',
                  style: TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    FilledButton.icon(
                      onPressed: !_busy && status == null
                          ? _pickAndAnalyze
                          : null,
                      icon: const Icon(Icons.upload_file),
                      label: const Text('Choose video'),
                    ),
                    OutlinedButton.icon(
                      onPressed: !_busy && status != null ? _deleteVideo : null,
                      icon: Icon(
                        status?.isActive == true
                            ? Icons.cancel
                            : Icons.delete_outline,
                      ),
                      label: Text(
                        status?.isActive == true
                            ? 'Cancel analysis'
                            : 'Clear result',
                      ),
                    ),
                  ],
                ),
                if (status != null) ...[
                  const SizedBox(height: 12),
                  Text('${status.filename} · ${status.state}'),
                  const SizedBox(height: 8),
                  LinearProgressIndicator(
                    value: status.progress?.clamp(0, 1),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    '${status.processedFrames} frames · '
                    '${status.processingFps.toStringAsFixed(1)} FPS',
                  ),
                ],
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        _framePanel(),
        const SizedBox(height: 12),
        if (_videoResults == null || _videoResults!.events.isEmpty)
          const EmptyPanel(
            icon: Icons.manage_search,
            title: 'No temporary events',
            message: 'Choose a video to show analysis events here.',
            compact: true,
          )
        else ...[
          Text(
            '${_videoResults!.knownEvents} known · '
            '${_videoResults!.unknownEvents} unknown',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          ..._videoResults!.events.reversed
              .take(30)
              .map(
                (event) => Card(
                  child: ListTile(
                    leading: Icon(
                      event.status == 'known'
                          ? Icons.verified_user
                          : Icons.warning_amber,
                    ),
                    title: Text(event.memberName ?? 'Unknown person'),
                    subtitle: Text(
                      '${event.timestampSeconds.toStringAsFixed(1)}s · '
                      'track ${event.trackId} · ${event.eventType}',
                    ),
                  ),
                ),
              ),
        ],
      ],
    );
  }

  Widget _framePanel() => AspectRatio(
    aspectRatio: 16 / 9,
    child: ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: ColoredBox(
        color: const Color(0xFF111827),
        child: _frame == null
            ? const Center(
                child: Icon(
                  Icons.videocam_off,
                  color: Colors.white54,
                  size: 52,
                ),
              )
            : Image.memory(_frame!, fit: BoxFit.contain, gaplessPlayback: true),
      ),
    ),
  );

  Widget _trackTile(AnalysisTrackModel track) => Card(
    child: ListTile(
      leading: Icon(
        track.status == 'known' ? Icons.verified_user : Icons.person_search,
      ),
      title: Text(track.memberName ?? 'Unknown person'),
      subtitle: Text(
        'Track ${track.trackId} · '
        '${((track.similarity ?? track.personConfidence) * 100).toStringAsFixed(1)}%',
      ),
    ),
  );
}
