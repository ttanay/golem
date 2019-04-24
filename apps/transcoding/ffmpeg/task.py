import logging
import os

from apps.core.task.coretask import CoreTaskTypeInfo
from apps.core.task.coretaskstate import TaskDefaults
from apps.transcoding.common import Container, VideoCodec, AudioCodec
from apps.transcoding.ffmpeg.environment import ffmpegEnvironment
from apps.transcoding.ffmpeg.utils import Commands, FFMPEG_BASE_SCRIPT
from apps.transcoding.task import TranscodingTaskOptions, \
    TranscodingTaskBuilder, TranscodingTaskDefinition, TranscodingTask
from golem.docker.job import DockerJob
from golem.verificator.ffmpeg_verifier import FFmpegVerifier

logger = logging.getLogger(__name__)


class ffmpegTaskTypeInfo(CoreTaskTypeInfo):
    def __init__(self):
        super().__init__('FFMPEG', TranscodingTaskDefinition,
                         ffmpegTaskOptions, ffmpegTaskBuilder)


class ffmpegTask(TranscodingTask):
    ENVIRONMENT_CLASS = ffmpegEnvironment
    VERIFIER_CLASS = FFmpegVerifier

    def _get_extra_data(self, subtask_num: int):
        transcoding_options = self.task_definition.options
        video_params = transcoding_options.video_params
        audio_params = transcoding_options.audio_params
        if subtask_num >= len(self.task_resources) // 2:
            raise AssertionError('Requested number subtask {} is greater than '
                                 'number of resources [size={}]'
                                 .format(subtask_num, len(self.task_resources)))

        chunk = os.path.relpath(self.chunks[subtask_num],
                                self._get_resources_root_dir())
        chunk = DockerJob.get_absolute_resource_path(chunk)

        filename = os.path.splitext(os.path.basename(
            self.chunks[subtask_num]))[0]
        output_extension = os.path.splitext(self.task_definition.output_file)[1]

        output_stream = os.path.join(
            DockerJob.OUTPUT_DIR,
            filename + '_TC' + output_extension)

        resolution = video_params.resolution
        resolution = [resolution[0], resolution[1]] if resolution else None
        vc = video_params.codec.value if video_params.codec else None
        ac = audio_params.codec.value if audio_params.codec else None
        extra_data = {
            'track': chunk,
            'targs': {
                'video': {
                    'codec': vc,
                    'bitrate': video_params.bitrate
                },
                'audio': {
                    'codec': ac,
                    'bitrate': audio_params.bitrate
                },
                'resolution': resolution,
                'frame_rate': video_params.frame_rate
            },
            'output_stream': output_stream,
            'use_playlist': transcoding_options.use_playlist,
            'command': Commands.TRANSCODE.value[0],
            'script_filepath': FFMPEG_BASE_SCRIPT
        }
        return self._clear_none_values(extra_data)

    def _clear_none_values(self, d: dict):
        return {k: v if not isinstance(v, dict) else self._clear_none_values(v)
                for k, v in d.items() if v is not None}


class ffmpegDefaults(TaskDefaults):
    pass


class ffmpegTaskBuilder(TranscodingTaskBuilder):
    SUPPORTED_FILE_TYPES = [Container.MKV, Container.AVI,
                            Container.MP4]
    SUPPORTED_VIDEO_CODECS = [VideoCodec.MPEG_2, VideoCodec.H_264]
    SUPPORTED_AUDIO_CODECS = [AudioCodec.MP3, AudioCodec.AAC]
    TASK_CLASS = ffmpegTask
    DEFAULTS = ffmpegDefaults


class ffmpegTaskDefinition(TranscodingTaskDefinition):
    pass


class ffmpegTaskOptions(TranscodingTaskOptions):
    def __init__(self):
        super(ffmpegTaskOptions, self).__init__()
        self.environment = ffmpegEnvironment()
