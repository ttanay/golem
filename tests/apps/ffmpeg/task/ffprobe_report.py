import json
import os

from apps.transcoding.ffmpeg.utils import StreamOperator


class FfprobeFormatReport:

    ATTRS_TO_CHECK = [
        'stream_types',
        'duration',
        'start_time',
    ]

    def __init__(self, raw_report: dict):
        self._raw_report = raw_report

    @property
    def stream_types(self):
        streams = self._raw_report['streams']
        streams_dict: Dict[str, int] = {}

        for stream in streams:
            codec_type = stream['codec_type']
            if codec_type in streams_dict:
                streams_dict[codec_type] = streams_dict[codec_type] + 1
            else:
                streams_dict.update({codec_type: 1})
        return streams_dict

    @property
    def duration(self):
        value = self._raw_report.get('format', {}).get('duration', None)
        return FuzzyDuration(value, 10)

    @property
    def start_time(self):
        try:
            return self._raw_report['format']['start_time']
        except KeyError:
            return 'not supported- key does not exists'


    def diff(self, format_report: dict, overrides: dict):
        differences = list()
        for attr in self.ATTRS_TO_CHECK:
            original_value = getattr(self, attr)
            modified_value = getattr(format_report, attr)

            if 'streams' in overrides and attr in overrides['streams']:
                modified_value = overrides['streams'][attr]

            if 'format' in overrides and attr in overrides['format']:
                modified_value = overrides['format'][attr]

            if modified_value != original_value:
                diff_dict = {
                    'location': 'format',
                    'attribute': attr,
                    'original value': str(original_value),
                    'modified value': str(modified_value),
                }
                differences.append(diff_dict)
        return differences

    def __eq__(self, other):
        return len(self.diff(other, {})) == 0

    @classmethod
    def build(cls, *video_paths: str) -> list:
        dirs_and_basenames: dict = {}
        for path in video_paths:
            dirname, basename = os.path.split(path)
            dirs_and_basenames[dirname] = (
                dirs_and_basenames.get(dirname, []) +
                [basename]
            )

        list_of_reports = []
        stream_operator = StreamOperator()

        for key in dirs_and_basenames:
            metadata = stream_operator.get_metadata(
                dirs_and_basenames[key],
                key
            )
            for path in metadata['data']:
                with open(path) as metadata_file:
                    list_of_reports.append(FfprobeFormatReport(
                        json.loads(metadata_file.read())
                    ))
        return list_of_reports

class FuzzyDuration:
    def __init__(self, duration, tolerance):
        self._duration = duration
        self._tolerance = tolerance

    @property
    def duration(self):
        return self._duration

    def __eq__(self, other):
        duration1 = float(self.duration)
        duration2 = float(other.duration)

        # We treat both fuzzy values as closed intervals:
        # [value - tolerance, value + tolerance]
        # If the intervals overlap at at least one point, we have a match.
        return abs(duration1 - duration2) <= self._tolerance + other._tolerance

    def __str__(self):
        if self._tolerance == 0:
            return f'{self._duration}'

        return f'{self._duration}+/-{self._tolerance}'

    def __repr__(self):
        return f'FuzzyDuration({self._duration}, {self._tolerance})'


class FfprobeVideoStreamReport:

    ATTRS_TO_CHECK = [
        'codec_name',
        'start_time',
        'duration',
        'resolution',
    ]

    def __init__(self, raw_report: dict):
        self._raw_report = raw_report

    @property
    def codec_name(self):
        try:
            return self._raw_report['codec_name']
        except KeyError:
            return None

    @property
    def start_time(self):
        return FuzzyDuration(self._raw_report['start_time'], 0)

    @property
    def duration(self):
        try:
            return FuzzyDuration(self._raw_report['duration'], 0)
        except KeyError:
            return 'not supported- key does not exists'

    @property
    def resolution(self):
        try:
            return self._raw_report['resolution']
        except KeyError:
            try:
                return self._raw_report['width'], self._raw_report['height']
            except:
                return 'not supported- key does not exists'

    def diff(self, format_report: dict, overrides: dict) -> list:
        differences = list()
        for attr in self.ATTRS_TO_CHECK:
            original_value = getattr(self, attr)
            modified_value = getattr(format_report, attr)

            if modified_value != original_value:
                diff_dict = {
                    'location': 'video',
                    'attribute': attr,
                    'original value': str(original_value),
                    'modified value': str(modified_value),
                }
                differences.append(diff_dict)
        return differences

    def __eq__(self, other):
        return len(self.diff(other, {})) == 0
