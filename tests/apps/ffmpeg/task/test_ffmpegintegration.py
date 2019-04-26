import os

from parameterized import parameterized
import pytest

from apps.transcoding.common import TranscodingTaskBuilderException, \
    ffmpegException
from apps.transcoding.ffmpeg.task import ffmpegTaskTypeInfo
from apps.transcoding.common import VideoCodec, Container
from golem.testutils import TestTaskIntegration
from tests.apps.ffmpeg.task.ffprobe_report import FuzzyDuration, \
    parse_ffprobe_frame_rate
from tests.apps.ffmpeg.task.ffprobe_report_set import FfprobeReportSet
from tests.apps.ffmpeg.task.simulated_transcoding_operation import \
    SimulatedTranscodingOperation


class FfmpegIntegrationTestCase(TestTaskIntegration):

    # pylint: disable=line-too-long
    GOOD_VIDEO_FILES = [
        'test_video.mp4',
        'test_video2.mp4',

        'videos/good/basen-out8[vp8,512x288,10s,v1a0s0d0,i248p494b247,25fps].webm',
        'videos/good/basen-out9[vp9,512x288,10s,v1a0s0d0,i248p494b247,25fps].webm',
        'videos/good/beachfront-dandelion[mpeg2video+mp2,1920x1080,20s,v1a1s0d0,i1765p1925b1604,23.976fps][segment1of5].mpeg',
        'videos/good/beachfront-mooncloseup[wmv3,1920x1080,34s,v1a0s0d0,i799p1578b792,24fps][segment1of7].wmv',
        'videos/good/beachfront-sleepingbee[wmv3+wmapro,1920x1080,47s,v1a1s0d0,i1135p2241b1125,24fps][segment1of10].wmv',
        'videos/good/h265files-alps[hevc+aac,1920x960,16s,v1a1s0d0,i401p478b718,25fps][segment1of2].mkv',
        'videos/good/matroska-test5[h264+aac+aac,1024x576,47s,v1a2s0d8,i1149p1655b1609,24fps][segment1of10].mkv',
        'videos/good/natureclip-fireandembers[wmv3+wmav2,1280x720,63s,v1a1s0d0,i2240p3428b1889,29.97fps][segment1of13].wmv',
        'videos/good/sample-bigbuckbunny[h263+amr_nb,176x144,41s,v1a1s0d0,i1269p1777b1218,15fps][segment1of9].3gp',
        'videos/good/sample-bigbuckbunny[mpeg4+aac,1280x720,4s,v1a1s0d0,i293p438b292,25fps].mkv',
        'videos/good/sample-bigbuckbunny[mpeg4+aac,320x240,15s,v1a1s0d0,i780p1091b748,25fps][segment1of3].3gp',
        'videos/good/sample-bigbuckbunny[mpeg4+aac,640x368,6s,v1a1s0d0,i319p477b318,25fps].mp4',
        'videos/good/standalone-bigbuckbunny[mpeg4+mp3,560x320,6s,v1a1s0d0,i344p482b330,30fps][segment1of2].avi',
        'videos/good/standalone-catherine[wmv3+wmav2,180x140,42s,v1a1s0d0,i637p1257b631,_][segment1of6].wmv',
        'videos/good/standalone-dlppart2[h264+aac,400x300,129s,v1a1s0d0,i3874p4884b6671,29.97fps][segment1of17].mov',
        'videos/good/standalone-dolbycanyon[h264+aac,720x480,38s,v1a1s0d0,i1147p1466b1948,29.97fps][segment1of5].m4v',
        'videos/good/standalone-grb2[flv1,720x480,28s,v1a0s0d0,i1743p2428b1668,29.9697fps][segment1of6].flv',
        'videos/good/standalone-grb2[h264,720x480,28s,v1a0s0d0,i840p1060b1437,29.97fps][segment1of4].m4v',
        'videos/good/standalone-grb2[mpeg2video,720x480,28s,v1a0s0d0,i2596p2783b3103,29.97fps].mpg',
        'videos/good/standalone-grb2[mpeg2video,720x480,28s,v1a0s0d0,i2656p3337b2579,29.97fps][segment1of6].vob',
        'videos/good/standalone-grb2[wmv2,720x480,28s,v1a0s0d0,i1744p2427b1668,29.97fps][segment1of6].wmv',
        'videos/good/standalone-jellyfish[flv1,1920x1080,30s,v1a0s0d0,i1874p2622b1798,29.9697fps][segment1of6].flv',
        'videos/good/standalone-jellyfish[h263,1408x1152,30s,v1a0s0d0,i1874p2622b1798,29.97fps][segment1of6].3gp',
        'videos/good/standalone-jellyfish[hevc,1920x1080,30s,v1a0s0d0,i903p1123b1571,29.97fps][segment1of4].mkv',
        'videos/good/standalone-lion[mpeg1video+mp2,384x288,117s,v1a1s0d0,i8738p9088b10660,23.976fps][segment1of24].mpeg',
        'videos/good/standalone-p6090053[h264+aac,320x240,30s,v1a1s0d0,i376p468b653,12.5fps][segment1of2].mp4',
        'videos/good/standalone-p6090053[mjpeg+pcm_u8,320x240,30s,v1a1s0d0,i1123p748b748,12.5fps][segment1of6].mov',
        'videos/good/standalone-page18[flv1+mp3,480x270,216s,v1a1s0d0,i11252p15749b10800,25fps][segment1of44].flv',
        'videos/good/standalone-page18[h263+amr_nb,352x288,216s,v1a1s0d0,i11252p15749b10800,25fps][segment1of44].3gp',
        'videos/good/standalone-page18[h264+aac,480x270,216s,v1a1s0d0,i5446p10755b5400,25fps][segment1of43].m4v',
        'videos/good/standalone-page18[mpeg4+mp3,480x270,216s,v1a1s0d0,i11252p15749b10800,25fps][segment1of44].avi',
        'videos/good/standalone-panasonic[h264+ac3,1920x1080,46s,v1a1s0d1,i1247p1439b1919,25fps][segment1of10].mts',
        'videos/good/standalone-panasonic[mpeg4+mp3,1920x1080,46s,v1a1s0d0,i2401p3355b2302,25fps][segment1of10].avi',
        'videos/good/standalone-small[h263+amr_nb,352x288,6s,v1a1s0d0,i344p482b330,30fps][segment1of2].3gp',
        'videos/good/standalone-small[h264+ac3,560x320,6s,v1a1s0d0,i166p211b284,29.97fps].mts',
        'videos/good/standalone-small[h264+vorbis,560x320,6s,v1a1s0d0,i166p211b284,30fps].mkv',
        'videos/good/standalone-small[mpeg2video+mp2,560x320,6s,v1a1s0d0,i523p661b509,30fps][segment1of2].vob',
        'videos/good/standalone-small[vp8+vorbis,560x320,6s,v1a1s0d0,i166p330b165,30fps].webm',
        'videos/good/standalone-small[wmv2+wmav2,560x320,6s,v1a1s0d0,i344p482b330,30fps][segment1of2].wmv',
        'videos/good/standalone-startrails[flv1+mp3,1280x720,21s,v1a1s0d0,i1101p1540b1056,25fps][segment1of5].flv',
        'videos/good/standalone-startrails[h263+amr_nb,704x576,21s,v1a1s0d0,i1101p1540b1056,25fps][segment1of5].3gp',
        'videos/good/standalone-startrails[vp9+opus,1280x720,21s,v1a1s0d0,i533p1052b528,25fps][segment1of5].webm',
        'videos/good/standalone-tra3106[h263,704x576,17s,v1a0s0d0,i1069p1472b1016,29.97fps][segment1of4].3gp',
        'videos/good/standalone-tra3106[mjpeg,720x496,17s,v1a0s0d0,i1525p1016b1016,29.97fps][segment1of4].avi',
        'videos/good/standalone-video1[wmv1+wmav2,320x240,12s,v1a1s0d0,i703p1048b700,30fps][segment1of2].wmv',
        'videos/good/standalone-videosample[flv1,320x240,59s,v1a0s0d0,i491p625b446,_][segment1of12].flv',
        'videos/good/standalone-videosample[h264,320x240,59s,v1a0s0d0,i224p279b390,29.97fps].mts',
        'videos/good/techslides-small[wmv2+wmav2,320x240,6s,v1a1s0d0,i331p495b330,30fps].wmv',
        'videos/good/webmfiles-bigbuckbunny[vp8+vorbis,640x360,32s,v1a1s0d0,i837p1597b811,25fps][segment1of7].webm',
        'videos/good/wfu-katamari[wmv3+wmav2,640x480,10s,v1a1s0d0,i301p597b299,29.97fps][segment1of2].wmv',
        'videos/good/wikipedia-tractor[vp8+vorbis,1920x1080,28s,v1a1s0d0,i695p1373b689,1000fps][segment1of5].webm',
        'videos/good/wikipedia-tractor[vp9+opus,854x480,28s,v1a1s0d0,i692p1376b689,25fps][segment1of3].webm',
        'videos/good/woolyss-llamadrama[av1+opus,854x480,87s,v1a1s0d0,i1879p1879b1879,24fps].webm',
    ]

    BAD_VIDEO_FILES = [
        'invalid_test_video.mp4',

        'videos/bad/beachfront-moonandclouds[mjpeg,1920x1080,50s,v1a0s0d0,i3574p2382b2382,24fps].mov',
        'videos/bad/beachfront-mooncloseup[mjpeg,1920x1080,33s,v1a0s0d0,i2374p1582b1582,23.976fps].mov',
        'videos/bad/matroska-test1[msmpeg4v2+mp3,854x480,87s,v1a1s0d0,i4215p6261b4190,24fps].mkv',
        'videos/bad/matroska-test4[theora+vorbis,1280x720,_,v1a1s0d0,i1677p3247b1641,24fps].mkv',
        'videos/bad/natureclip-relaxriver[h264+aac,1920x1080,20s,v1a1s0d0,i606p1192b599,29.97fps].mov',
        'videos/bad/standalone-dolbycanyon[h263+amr_nb,704x576,38s,v1a1s0d0,i2376p3325b2280,29.97fps].3gp',
        'videos/bad/standalone-dolbycanyon[mpeg2video+ac3,720x480,38s,v1a1s0d0,i3574p3801b4257,29.97fps].vob',
        'videos/bad/standalone-small[mpeg2video+mp2,560x320,6s,v1a1s0d0,i523p661b509,30fps].mpg',
        'videos/bad/standalone-tra3106[mpeg2video,720x496,17s,v1a0s0d0,i1642p2033b1583,29.97fps].mpeg',
        'videos/bad/standalone-videosample[mpeg2video,320x240,59s,v1a0s0d0,i45135p57013b43947,240fps].mpg',
        'videos/bad/techslides-small[theora+vorbis,560x320,6s,v1a1s0d0,i168p328b165,30fps].ogv',
    ]
    # pylint: enable=line-too-long

    VIDEO_FILES = GOOD_VIDEO_FILES + BAD_VIDEO_FILES

    def setUp(self):
        super(FfmpegIntegrationTestCase, self).setUp()

        # We'll be comparing output from FfprobeFormatReport.diff() which
        # can be long but we still want to see it all.
        self.maxDiff = None

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

        cls._ffprobe_report_set = None
        # Uncomment this enable report generation:
        #cls._ffprobe_report_set = FfprobeReportSet()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        if cls._ffprobe_report_set is not None:
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
        if video_codec not in container.get_supported_video_codecs():
            pytest.skip("Unsupported container/video codec combination")

        operation = SimulatedTranscodingOperation(
            task_executor=self,
            experiment_name="codec change",
            resource_dir=self.RESOURCES,
            tmp_dir=self.tempdir)
        operation.attach_to_report_set(self._ffprobe_report_set)
        operation.request_video_codec_change(video_codec)
        operation.request_container_change(container)
        operation.exclude_from_diff({'video': {'pixel_format'}})
        operation.exclude_from_diff({'audio': {'codec_name'}})
        operation.enable_treating_missing_attributes_as_unchanged()
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
        operation.exclude_from_diff({'video': {'pixel_format'}})
        operation.exclude_from_diff({'audio': {'codec_name'}})
        operation.enable_treating_missing_attributes_as_unchanged()
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
        operation.exclude_from_diff({'video': {'pixel_format'}})
        operation.exclude_from_diff({'audio': {'codec_name'}})
        fuzzy_rate = FuzzyDuration(parse_ffprobe_frame_rate(frame_rate), 0.5)
        operation.set_override({'video': {'frame_rate': fuzzy_rate}})
        operation.enable_treating_missing_attributes_as_unchanged()
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
        operation.exclude_from_diff({'video': {'pixel_format'}})
        operation.exclude_from_diff({'audio': {'codec_name'}})
        operation.enable_treating_missing_attributes_as_unchanged()
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
        operation.exclude_from_diff({'video': {'pixel_format'}})
        operation.exclude_from_diff({'audio': {'codec_name'}})
        operation.enable_treating_missing_attributes_as_unchanged()
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
