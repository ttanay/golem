import json
import os
from typing import Any, Collection, Dict, List, Optional

from apps.transcoding.ffmpeg.utils import StreamOperator


DiffDict = Dict[str, Any]
Diff = List[DiffDict]
StreamOverrides = Dict[str, Any]
FileOverrides = Dict[str, StreamOverrides]


class UnsupportedCodecType(Exception):
    pass


class FfprobeFormatReport:
    ATTRIBUTES_TO_COMPARE = {
        'stream_types',
        'duration',
        'start_time',
    }

    def __init__(self, raw_report: dict):
        self._raw_report = raw_report
        self._stream_reports = self._create_stream_reports(raw_report)

    @classmethod
    def _create_stream_report(cls, raw_stream_report):
        codec_type_to_report_class = {
            'video':    FfprobeVideoStreamReport,
            'audio':    FfprobeAudioStreamReport,
            'subtitle': FfprobeSubtitleStreamReport,
            'data':     FfprobeDataStreamReport,
        }

        codec_type = raw_stream_report['codec_type']
        if codec_type not in codec_type_to_report_class:
            raise UnsupportedCodecType(
                f"Unexpected codec type: {codec_type}. "
                f"A new stream report class is needed to handle it."
            )

        report_class = codec_type_to_report_class[codec_type]
        return report_class(raw_stream_report)

    @classmethod
    def _create_stream_reports(cls, raw_report):
        if 'streams' not in raw_report:
            return []

        return [
            cls._create_stream_report(raw_stream_report)
            for raw_stream_report in raw_report['streams']
        ]

    @property
    def stream_reports(self):
        return self._stream_reports

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
        value = self._raw_report.get('format', {}).get('start_time', None)
        return FuzzyDuration(value, 0)

    @classmethod
    def _classify_streams(cls,
                          stream_reports: List['FfprobeStreamReport'],
                         ) -> Dict[str, List['FfprobeStreamReport']]:
        reports_by_type: Dict[str, List['FfprobeStreamReport']] = {}
        for report in stream_reports:
            reports_by_type[report.codec_type] = (
                reports_by_type.get(report.codec_type, []) + [report]
            )

        return reports_by_type

    @classmethod
    def _diff_streams_same_type(cls,
                                original_stream_reports:
                                List['FfprobeStreamReport'],
                                modified_stream_reports:
                                List['FfprobeStreamReport'],
                                overrides: Optional[FileOverrides] = None
                               ) -> Diff:
        assert len(
            set(r.codec_type for r in original_stream_reports) |
            set(r.codec_type for r in modified_stream_reports)
        ) == 1, "All stream reports must have the same codec type"

        if overrides is None:
            overrides = {}

        diffs: Diff = []

        unmatched_reports = set(range(len(modified_stream_reports)))
        for original_idx, original_report in enumerate(original_stream_reports):
            shortest_diff: Optional[Diff] = None
            for modified_idx in unmatched_reports:
                stream_overrides = overrides.get(
                    modified_stream_reports[modified_idx].codec_type,
                    {}
                )

                new_diff = original_report.diff(
                    modified_stream_reports[modified_idx],
                    stream_overrides,
                )

                if shortest_diff is None or len(shortest_diff) > len(new_diff):
                    assert new_diff is not None
                    shortest_diff = new_diff

                if len(shortest_diff) == 0:  # pylint: disable=len-as-condition
                    break

            if shortest_diff is not None:
                for diff_dict in shortest_diff:
                    diff_dict['original_stream_index'] = original_idx

                    # shortest_diff not being None guarantees that the loop
                    # ran at least once so modified_idx is not undefined
                    diff_dict[
                        'modified_stream_index'
                    ] = modified_idx  # pylint: disable=undefined-loop-variable

                diffs += shortest_diff
                unmatched_reports.remove(
                    modified_idx  # pylint: disable=undefined-loop-variable
                )
            else:
                diffs.append({
                    'location': original_stream_reports[0].codec_type,
                    'original_stream_index': original_idx,
                    'modified_stream_index': None,
                    'reason': "No matching stream",
                })

        for modified_idx in unmatched_reports:
            diffs.append({
                'location': modified_stream_reports[0].codec_type,
                'original_stream_index': None,
                'modified_stream_index': modified_idx,
                'reason': "No matching stream",
            })

        return diffs

    @classmethod
    def _diff_streams(cls,
                      original_stream_reports: List['FfprobeStreamReport'],
                      modified_stream_reports: List['FfprobeStreamReport'],
                      overrides: Optional[FileOverrides] = None
                     ) -> Diff:

        original_reports_by_type = cls._classify_streams(
            original_stream_reports
        )
        modified_reports_by_type = cls._classify_streams(
            modified_stream_reports
        )
        codec_types_in_buckets = (
            set(original_reports_by_type) |
            set(modified_reports_by_type)
        )

        stream_differences: Diff = []
        for codec_type in codec_types_in_buckets:
            stream_differences += cls._diff_streams_same_type(
                original_reports_by_type.get(codec_type, []),
                modified_reports_by_type.get(codec_type, []),
                overrides,
            )

        return stream_differences

    # pylint: disable=unsubscriptable-object
    # FIXME: pylint bug, see https://github.com/PyCQA/pylint/issues/2377
    @classmethod
    def _diff_attributes(cls,
                         attributes_to_compare: Collection[str],
                         original_report: 'FfprobeFormatReport',
                         modified_report: 'FfprobeFormatReport',
                         overrides: Optional[StreamOverrides] = None) -> Diff:
        if overrides is None:
            overrides = {}

        differences = []
        for attribute in attributes_to_compare:
            original_value = getattr(original_report, attribute)

            if attribute in overrides:
                modified_value = overrides[attribute]
            else:
                modified_value = getattr(modified_report, attribute)

            if modified_value != original_value:
                diff_dict = {
                    'location': 'format',
                    'attribute': attribute,
                    'original_value': original_value,
                    'modified_value': modified_value,
                    'reason': "Different attribute values",
                }
                differences.append(diff_dict)

        return differences

    def diff(self,
             modified_report: 'FfprobeFormatReport',
             overrides: Optional[FileOverrides] = None) -> Diff:

        format_differences = self._diff_attributes(
            self.ATTRIBUTES_TO_COMPARE,
            self,
            modified_report,
            overrides.get('format', {}) if overrides is not None else None,
        )

        stream_differences = self._diff_streams(
            self.stream_reports,
            modified_report.stream_reports,
            overrides,
        )

        return format_differences + stream_differences

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
        try:
            duration1 = float(self.duration)
            duration2 = float(other.duration)
        except ValueError:
            return self.duration == other.duration

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


class FuzzyInt:
    def __init__(self, value, tolerance_percent):
        self._value = value
        self._tolerance_percent = tolerance_percent

    @property
    def value(self):
        return self._value

    @property
    def tolerance_percent(self):
        return self._tolerance_percent

    def __eq__(self, other):
        try:
            duration1 = float(self.value)
            duration2 = float(other.value)
        except TypeError:
            return self.value == other.value

        tolerance = (abs(self.tolerance_percent*self.value) +
                     abs(other.tolerance_percent*other.value)) / 100
        return abs(duration1 - duration2) <= tolerance

    def __str__(self):
        if self.tolerance_percent == 0:
            return f'{self._value}'

        return f'{self._value}+/-{self.tolerance_percent}%'

    def __repr__(self):
        return f'FuzzyDuration({self._value}, {self.tolerance_percent})'


class FfprobeStreamReport:
    ATTRIBUTES_TO_COMPARE = {
        'codec_type',
        'codec_name',
        'start_time'
    }

    def __init__(self, raw_report: dict):
        self._raw_report = raw_report

    @property
    def codec_type(self):
        return self._raw_report.get('codec_type', None)

    @property
    def codec_name(self):
        return self._raw_report.get('codec_name', None)

    @property
    def start_time(self):
        return FuzzyDuration(self._raw_report['start_time'], 0.05)

    # pylint: disable=unsubscriptable-object
    # FIXME: pylint bug, see https://github.com/PyCQA/pylint/issues/2377
    @classmethod
    def _diff_attributes(cls,
                         attributes_to_compare: Collection[str],
                         original_stream_report: 'FfprobeStreamReport',
                         modified_stream_report: 'FfprobeStreamReport',
                         overrides: Optional[StreamOverrides] = None) -> Diff:

        assert (original_stream_report.codec_type ==
                modified_stream_report.codec_type)

        if overrides is None:
            overrides = {}

        differences = []
        for attribute in attributes_to_compare:
            original_value = getattr(original_stream_report, attribute)

            if attribute in overrides:
                modified_value = overrides[attribute]
            else:
                modified_value = getattr(modified_stream_report, attribute)

            if modified_value != original_value:
                diff_dict = {
                    'location': original_stream_report.codec_type,
                    'attribute': attribute,
                    'original_value': original_value,
                    'modified_value': modified_value,
                    'reason': "Different attribute values",
                }
                differences.append(diff_dict)

        return differences

    def diff(self,
             modified_stream_report: 'FfprobeStreamReport',
             overrides: Optional[StreamOverrides] = None) -> Diff:

        return self._diff_attributes(
            self.ATTRIBUTES_TO_COMPARE,
            self,
            modified_stream_report,
            overrides,
        )

    def __eq__(self, other):
        return len(self.diff(other, {})) == 0


class FfprobeMediaStreamReport(FfprobeStreamReport):
    ATTRIBUTES_TO_COMPARE = FfprobeStreamReport.ATTRIBUTES_TO_COMPARE | {
        'duration',
        'bitrate',
        'frame_count',
    }

    @property
    def duration(self):
        if 'duration' not in self._raw_report:
            return None

        return FuzzyDuration(self._raw_report['duration'], 0.05)

    @property
    def bitrate(self):
        return FuzzyInt(self._raw_report.get('bit_rate'), 5)

    @property
    def frame_count(self):
        return self._raw_report.get('nb_frames')


class FfprobeVideoStreamReport(FfprobeMediaStreamReport):
    ATTRIBUTES_TO_COMPARE = FfprobeMediaStreamReport.ATTRIBUTES_TO_COMPARE | {
        'resolution',
        'pixel_format',
        'frame_rate',
    }

    def __init__(self, raw_report: dict):
        assert raw_report['codec_type'] == 'video'
        super().__init__(raw_report)

    @property
    def resolution(self):
        return (
            self._raw_report.get('resolution', None),
            self._raw_report.get('width', None),
            self._raw_report.get('height', None),
        )

    @property
    def pixel_format(self):
        return self._raw_report.get('pix_fmt')

    @property
    def frame_rate(self):
        frame_rate = self._raw_report.get('r_frame_rate')
        if isinstance(frame_rate, (int, float)):
            return frame_rate
        elif isinstance(frame_rate, str):
            splited = frame_rate.split('/')
            try:
                return float(splited[0])/float(splited[1])
            except (ValueError, TypeError):
                pass
        return self._raw_report.get('r_frame_rate')


class FfprobeAudioStreamReport(FfprobeMediaStreamReport):
    def __init__(self, raw_report: dict):
        assert raw_report['codec_type'] == 'audio'
        super().__init__(raw_report)

    ATTRIBUTES_TO_COMPARE = FfprobeMediaStreamReport.ATTRIBUTES_TO_COMPARE | {
        'sample_rate',
        'sample_format',
        'channel_count',
        'channel_layout',
    }

    @property
    def sample_rate(self):
        return int(self._raw_report.get('sample_rate'))

    @property
    def sample_format(self):
        return self._raw_report.get('sample_format')

    @property
    def channel_count(self):
        return self._raw_report.get('channels')

    @property
    def channel_layout(self):
        return self._raw_report.get('channel_layout')


class FfprobeSubtitleStreamReport(FfprobeStreamReport):
    def __init__(self, raw_report: dict):
        assert raw_report['codec_type'] == 'subtitle'
        super().__init__(raw_report)
        print()

    ATTRIBUTES_TO_COMPARE = FfprobeStreamReport.ATTRIBUTES_TO_COMPARE | {
        'language',
    }

    @property
    def language(self):
        return self._raw_report.get('tags').get('language')


class FfprobeDataStreamReport(FfprobeStreamReport):
    def __init__(self, raw_report: dict):
        assert raw_report['codec_type'] == 'data'
        super().__init__(raw_report)
