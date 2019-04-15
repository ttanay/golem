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
