import os

from parameterized import parameterized
import pytest

from apps.transcoding.common import TranscodingTaskBuilderException, \
    ffmpegException
from apps.transcoding.ffmpeg.task import ffmpegTaskTypeInfo
from apps.transcoding.common import VideoCodec, Container
from golem.testutils import TestTaskIntegration
from tests.apps.ffmpeg.task.ffprobe_report_set import FfprobeReportSet
from tests.apps.ffmpeg.task.simulated_transcoding_operation import \
    SimulatedTranscodingOperation


class FfmpegIntegrationTestCase(TestTaskIntegration):

    VIDEO_FILES = [
        "test_video.mp4",
        "test_video2.mp4",
    ]

    def setUp(self):
        super(FfmpegIntegrationTestCase, self).setUp()
        self.RESOURCES = os.path.join(os.path.dirname(
            os.path.dirname(os.path.realpath(__file__))), 'resources')
        self.tt = ffmpegTaskTypeInfo()

    @classmethod
    def _create_task_def_for_transcoding(
            cls,
            resource_stream,
            result_file,
            video_options=None,
            subtasks_count=2,
    ):
        task_def_for_transcoding = {
            'type': 'FFMPEG',
            'name': os.path.splitext(os.path.basename(result_file))[0],
            'timeout': '0:10:00',
            'subtask_timeout': '0:09:50',
            'subtasks_count': subtasks_count,
            'bid': 1.0,
            'resources': [resource_stream],
            'options': {
                'output_path': os.path.dirname(result_file),
                'video': video_options if video_options is not None else {},
                'container': os.path.splitext(result_file)[1][1:]
            }
        }

        return task_def_for_transcoding


class TestffmpegIntegration(FfmpegIntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._ffprobe_report_set = FfprobeReportSet()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        print(cls._ffprobe_report_set.to_markdown())

    @parameterized.expand(
        (video_file, video_codec, container)
        for video_file in FfmpegIntegrationTestCase.VIDEO_FILES
        for video_codec, container in [
            (VideoCodec.AV1, Container.WEBM),
            (VideoCodec.FLV1, Container.FLV),
            (VideoCodec.H_263, Container.MKV),
            (VideoCodec.H_264, Container.MP4),
            (VideoCodec.HEVC, Container.MP4),
            (VideoCodec.MJPEG, Container.MOV),
            (VideoCodec.MPEG_1, Container.MPEG),
            (VideoCodec.MPEG_2, Container.MPG),
            (VideoCodec.MPEG_4, Container.MTS),
            (VideoCodec.THEORA, Container.OGV),
            (VideoCodec.VP8, Container.WEBM),
            (VideoCodec.VP9, Container.MKV),
            (VideoCodec.WMV1, Container.WMV),
            (VideoCodec.WMV2, Container.ASF),
        ]
    )
    @pytest.mark.slow
    def test_split_and_merge_with_codec_change(self,
                                               video_file,
                                               video_codec,
                                               container):
        operation = SimulatedTranscodingOperation(
            task_executor=self,
            experiment_name="codec change",
            resource_dir=self.RESOURCES,
            tmp_dir=self.tempdir)
        operation.attach_to_report_set(self._ffprobe_report_set)
        operation.request_video_codec_change(video_codec)
        operation.request_container_change(container)
        (_input_report, _output_report, diff) = operation.run(video_file)
        self.assertEqual(diff, [])

    @parameterized.expand(
        (video_file, resolution)
        for video_file in FfmpegIntegrationTestCase.VIDEO_FILES
        for resolution in (
            # NOTE: 176x144 is one of the few resolutions supported by H.263
            (176, 144),
            (20, 600),
            (1000, 1000),
        )
    )
    @pytest.mark.slow
    def test_split_and_merge_with_resolution_change(self,
                                                    video_file,
                                                    resolution):
        operation = SimulatedTranscodingOperation(
            task_executor=self,
            experiment_name="resolution change",
            resource_dir=self.RESOURCES,
            tmp_dir=self.tempdir)
        operation.attach_to_report_set(self._ffprobe_report_set)
        operation.request_resolution_change(resolution)
        (_input_report, _output_report, diff) = operation.run(video_file)
        self.assertEqual(diff, [])

    @parameterized.expand(
        (video_file, frame_rate)
        for video_file in FfmpegIntegrationTestCase.VIDEO_FILES
        for frame_rate in ('25/1', '25/2')
    )
    @pytest.mark.slow
    def test_split_and_merge_with_frame_rate_change(self,
                                                    video_file,
                                                    frame_rate):
        operation = SimulatedTranscodingOperation(
            task_executor=self,
            experiment_name="frame rate change",
            resource_dir=self.RESOURCES,
            tmp_dir=self.tempdir)
        operation.attach_to_report_set(self._ffprobe_report_set)
        operation.request_frame_rate_change(frame_rate)
        (_input_report, _output_report, diff) = operation.run(video_file)
        self.assertEqual(diff, [])

    @parameterized.expand(
        (video_file, bitrate)
        for video_file in FfmpegIntegrationTestCase.VIDEO_FILES
        for bitrate in ('1000000',)
    )
    @pytest.mark.slow
    def test_split_and_merge_with_bitrate_change(self, video_file, bitrate):
        operation = SimulatedTranscodingOperation(
            task_executor=self,
            experiment_name="bitrate change",
            resource_dir=self.RESOURCES,
            tmp_dir=self.tempdir)
        operation.attach_to_report_set(self._ffprobe_report_set)
        operation.request_video_bitrate_change(bitrate)
        (_input_report, _output_report, diff) = operation.run(video_file)
        self.assertEqual(diff, [])

    @parameterized.expand(
        (video_file, subtasks_count)
        for video_file in FfmpegIntegrationTestCase.VIDEO_FILES
        for subtasks_count in (1, 6, 10)
    )
    @pytest.mark.slow
    def test_split_and_merge_with_different_subtask_counts(self,
                                                           video_file,
                                                           subtasks_count):
        operation = SimulatedTranscodingOperation(
            task_executor=self,
            experiment_name="number of subtasks",
            resource_dir=self.RESOURCES,
            tmp_dir=self.tempdir)
        operation.attach_to_report_set(self._ffprobe_report_set)
        operation.request_subtasks_count(subtasks_count)
        (_input_report, _output_report, diff) = operation.run(video_file)
        self.assertEqual(diff, [])

    def test_simple_case(self):
        resource_stream = os.path.join(self.RESOURCES, 'test_video2.mp4')
        result_file = os.path.join(self.root_dir, 'test_simple_case.mp4')
        task_def = self._create_task_def_for_transcoding(
            resource_stream,
            result_file,
            video_options={
                'codec': 'h265',
                'resolution': [320, 240],
                'frame_rate': "25",
            })

        self.execute_task(task_def)

        self.run_asserts([
            self.check_file_existence(result_file)])

    def test_nonexistent_output_dir(self):
        resource_stream = os.path.join(self.RESOURCES, 'test_video2.mp4')
        result_file = os.path.join(self.root_dir, 'nonexistent', 'path',
                                   'test_invalid_task_definition.mp4')
        task_def = self._create_task_def_for_transcoding(
            resource_stream,
            result_file,
            video_options={
                'codec': 'h265',
                'resolution': [320, 240],
                'frame_rate': "25",
            })

        self.execute_task(task_def)

        self.run_asserts([
            self.check_dir_existence(os.path.dirname(result_file)),
            self.check_file_existence(result_file)])

    def test_nonexistent_resource(self):
        resource_stream = os.path.join(self.RESOURCES,
                                       'test_nonexistent_video.mp4')

        result_file = os.path.join(self.root_dir, 'test_nonexistent_video.mp4')
        task_def = self._create_task_def_for_transcoding(
            resource_stream,
            result_file,
            video_options={
                'codec': 'h265',
                'resolution': [320, 240],
                'frame_rate': "25",
            })

        with self.assertRaises(TranscodingTaskBuilderException):
            self.execute_task(task_def)

    def test_invalid_resource_stream(self):
        resource_stream = os.path.join(self.RESOURCES, 'invalid_test_video.mp4')
        result_file = os.path.join(self.root_dir,
                                   'test_invalid_resource_stream.mp4')

        task_def = self._create_task_def_for_transcoding(
            resource_stream,
            result_file,
            video_options={
                'codec': 'h265',
                'resolution': [320, 240],
                'frame_rate': "25",
            })

        with self.assertRaises(ffmpegException):
            self.execute_task(task_def)

    def test_task_invalid_params(self):
        resource_stream = os.path.join(self.RESOURCES, 'test_video2.mp4')
        result_file = os.path.join(self.root_dir, 'test_invalid_params.mp4')
        task_def = self._create_task_def_for_transcoding(
            resource_stream,
            result_file,
            video_options={
                'codec': 'abcd',
                'resolution': [320, 240],
                'frame_rate': "25",
            })

        with self.assertRaises(TranscodingTaskBuilderException):
            self.execute_task(task_def)
