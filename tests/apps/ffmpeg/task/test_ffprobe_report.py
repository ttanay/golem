from unittest import TestCase

from tests.apps.ffmpeg.task.ffprobe_report import FfprobeFormatReport
from tests.apps.ffmpeg.task.ffprobe_report_sample_reports import \
    RAW_REPORT_ORIGINAL, RAW_REPORT_TRANSCODED, \
    RAW_REPORT_ORIGINAL_WITH_REMOVED_SUBTITLES, RAW_REPORT_WITH_MPEG4


class TestFfprobeFormatReport(TestCase):

    def test_reports_with_shuffled_streams_should_be_compared_as_equal(self):
        report_original = FfprobeFormatReport(
            RAW_REPORT_ORIGINAL_WITH_REMOVED_SUBTITLES)
        report_transcoded = FfprobeFormatReport(RAW_REPORT_TRANSCODED)
        self.assertEqual(report_original, report_transcoded)

    def test_missing_streams_should_be_reported(self):
        report_original = FfprobeFormatReport(RAW_REPORT_ORIGINAL)
        report_transcoded = FfprobeFormatReport(RAW_REPORT_TRANSCODED)
        diff = (report_transcoded.diff(report_original))

        expected_diff = [
            {
                'location': 'format',
                'attribute': 'stream_types',
                'original_value': {
                    'audio': 2,
                    'video': 1
                },
                'modified_value': {
                    'video': 1,
                    'audio': 2,
                    'subtitle': 8
                },
                'reason': 'Different attribute values'
            },
            {
                'location': 'subtitle',
                'original_stream_index': None,
                'modified_stream_index': 0,
                'reason': 'No matching stream'
            },
            {
                'location': 'subtitle',
                'original_stream_index': None,
                'modified_stream_index': 1,
                'reason': 'No matching stream'
            },
            {
                'location': 'subtitle',
                'original_stream_index': None,
                'modified_stream_index': 2,
                'reason': 'No matching stream'
            },
            {
                'location': 'subtitle',
                'original_stream_index': None,
                'modified_stream_index': 3,
                'reason': 'No matching stream'
            },
            {
                'location': 'subtitle',
                'original_stream_index': None,
                'modified_stream_index': 4,
                'reason': 'No matching stream'
            },
            {
                'location': 'subtitle',
                'original_stream_index': None,
                'modified_stream_index': 5,
                'reason': 'No matching stream'
            },
            {
                'location': 'subtitle',
                'original_stream_index': None,
                'modified_stream_index': 6,
                'reason': 'No matching stream'
            },
            {
                'location': 'subtitle',
                'original_stream_index': None,
                'modified_stream_index': 7,
                'reason': 'No matching stream'
            }
        ]
        self.assertCountEqual(diff, expected_diff)

    def test_report_should_have_video_fields_with_proper_values(self):
        assert RAW_REPORT_WITH_MPEG4['streams'][0]['width'] == 560
        assert RAW_REPORT_WITH_MPEG4['streams'][0]['height'] == 320
        assert RAW_REPORT_WITH_MPEG4['streams'][0]['pix_fmt'] == 'yuv420p'
        assert RAW_REPORT_WITH_MPEG4['streams'][0]['r_frame_rate'] == '30/1'

        report = FfprobeFormatReport(RAW_REPORT_WITH_MPEG4)

        self.assertEqual(report.stream_reports[0].resolution, (560, 320))
        self.assertEqual(report.stream_reports[0].pixel_format, 'yuv420p')
        self.assertEqual(report.stream_reports[0].frame_rate, 30)

    def test_report_should_have_audio_fields_with_proper_values(self):
        assert RAW_REPORT_WITH_MPEG4['streams'][1]['sample_rate'] == '48000'
        assert RAW_REPORT_WITH_MPEG4['streams'][1]['channels'] == 1
        assert RAW_REPORT_WITH_MPEG4['streams'][1]['channel_layout'] == 'mono'
        assert not hasattr(RAW_REPORT_WITH_MPEG4['streams'][1], 'sample_format')

        report = FfprobeFormatReport(RAW_REPORT_WITH_MPEG4)

        self.assertEqual(report.stream_reports[1].sample_rate, 48000)
        self.assertEqual(report.stream_reports[1].sample_format, None)
        self.assertEqual(report.stream_reports[1].channel_count, 1)
        self.assertEqual(report.stream_reports[1].channel_layout, 'mono')

    def test_report_should_have_audio_and_video_fields_with_proper_values(self):
        assert RAW_REPORT_WITH_MPEG4['streams'][0]['duration'] == '5.566667'
        assert RAW_REPORT_WITH_MPEG4['streams'][0]['bit_rate'] == '499524'
        assert RAW_REPORT_WITH_MPEG4['streams'][0]['nb_frames'] == '167'

        assert RAW_REPORT_WITH_MPEG4['streams'][1]['duration'] == '5.640000'
        assert RAW_REPORT_WITH_MPEG4['streams'][1]['bit_rate'] == '64275'
        assert RAW_REPORT_WITH_MPEG4['streams'][1]['nb_frames'] == '235'

        report = FfprobeFormatReport(RAW_REPORT_WITH_MPEG4)

        self.assertEqual(report.stream_reports[0].duration.duration, 5.566667)
        self.assertEqual(report.stream_reports[0].bitrate.value, 499524)
        self.assertEqual(report.stream_reports[0].frame_count, 167)

        self.assertEqual(report.stream_reports[1].duration.duration, 5.64)
        self.assertEqual(report.stream_reports[1].bitrate.value, 64275)
        self.assertEqual(report.stream_reports[1].frame_count, 235)

    def test_report_should_have_stream_fields_with_proper_values(self):
        assert RAW_REPORT_WITH_MPEG4['streams'][0]['codec_type'] == 'video'
        assert RAW_REPORT_WITH_MPEG4['streams'][0]['codec_name'] == 'mpeg4'
        assert RAW_REPORT_WITH_MPEG4['streams'][0]['start_time'] == '0.000000'

        assert RAW_REPORT_WITH_MPEG4['streams'][1]['codec_type'] == 'audio'
        assert RAW_REPORT_WITH_MPEG4['streams'][1]['codec_name'] == 'mp3'
        assert RAW_REPORT_WITH_MPEG4['streams'][1]['start_time'] == '0.000000'

        report = FfprobeFormatReport(RAW_REPORT_WITH_MPEG4)

        self.assertEqual(report.stream_reports[0].codec_type, 'video')
        self.assertEqual(report.stream_reports[0].codec_name, 'mpeg4')
        self.assertEqual(report.stream_reports[0].start_time.duration, 0)

        self.assertEqual(report.stream_reports[1].codec_type, 'audio')
        self.assertEqual(report.stream_reports[1].codec_name, 'mp3')
        self.assertEqual(report.stream_reports[1].start_time.duration, 0)

    def test_report_should_have_format_fields_with_proper_values(self):
        assert RAW_REPORT_WITH_MPEG4['streams'][0]['codec_type'] == 'video'
        assert RAW_REPORT_WITH_MPEG4['streams'][1]['codec_type'] == 'audio'
        assert len(RAW_REPORT_WITH_MPEG4['streams']) == 2
        assert RAW_REPORT_WITH_MPEG4['format']['duration'] == '5.640000'
        assert RAW_REPORT_WITH_MPEG4['format']['start_time'] == '0.000000'
        assert RAW_REPORT_WITH_MPEG4['format']['nb_programs'] == 0

        report = FfprobeFormatReport(RAW_REPORT_WITH_MPEG4)

        self.assertEqual(report.stream_types, {'audio': 1, 'video': 1})
        self.assertEqual(report.duration.duration, 5.64)
        self.assertEqual(report.start_time.duration, 0)
        self.assertEqual(report.program_count, 0)
