import json
import os
import re
import subprocess

FFMPEG_COMMAND = "ffmpeg"
FFPROBE_COMMAND = "ffprobe"

TMP_DIR = "/golem/work/tmp/"


def flatten_list(list_of_lists):
    return [item for sublist in list_of_lists for item in sublist]


def exec_cmd(cmd, file=None):
    print("Executing command:")
    print(cmd)

    pc = subprocess.Popen(cmd, stdout=file, stderr=file)

    ret = pc.wait()
    if ret != 0:
        exit(ret)


def exec_cmd_to_file(cmd, filepath):
    # Ensure directory exists
    filedir = os.path.dirname(filepath)
    if not os.path.exists(filedir):
        os.makedirs(filedir)

    # Execute command and send results to file.
    with open(filepath, "w") as result_file:
        exec_cmd(cmd, result_file)


def exec_cmd_to_string(cmd):
    # Execute command and send results to file.
    tmp_command_result_file = os.path.join(TMP_DIR,
                                           "tmp-command-result.txt")
    exec_cmd_to_file(cmd, tmp_command_result_file)

    data_string = ""
    with open(tmp_command_result_file, "r") as result_file:
        data_string = result_file.read()

    return data_string


def extract_streams(input_file, output_file, selected_streams):
    assert os.path.isfile(input_file)
    assert not os.path.exists(output_file)

    cmd = extract_streams_command(
        input_file,
        output_file,
        selected_streams)

    exec_cmd(cmd)


def extract_streams_command(input_file,
                            output_file,
                            selected_streams):
    """
    Builds a ffmpeg command that can be used to extract a selected streams
    from a container and put them in a newly created container of the same type

    :param input_file: Existing container. Must exist.
    :param output_file: Container to put the streams in. Must not exist.
    :param selected_streams: List of streams to extract.
        List items should be valid stream selectors when prefixed with `0:`
        See https://trac.ffmpeg.org/wiki/Map.
        A few examples:
           [0, 1, 2]     - first three streams
           ['v']         - all video streams
           ['a', 'd']    - all audio and data streams
           ['v', 'a:2']  - all video streams and third audio stream
    """

    map_options = [
        ["-map", f"0:{index}"]
        for index in selected_streams
    ]

    cmd = (
        [
            FFMPEG_COMMAND,
            "-nostdin",
            "-i", input_file,
        ] +
        flatten_list(map_options) +
        [
            "-codec", "copy",
            output_file,
        ]
    )

    return cmd


def split_video(input_file, output_dir, split_len):
    [_, filename] = os.path.split(input_file)
    [basename, _] = os.path.splitext(filename)

    output_list_file = os.path.join(output_dir, basename + "_.m3u8")

    split_list_file = split(input_file, output_list_file, split_len)

    return split_list_file


def split(input_file, output_list_file, segment_time):
    cmd, file_list = split_video_command(input_file, output_list_file,
                                         segment_time)
    exec_cmd(cmd)

    return file_list


def split_video_command(input_file, output_list_file, segment_time):
    (_, input_filename) = os.path.split(input_file)
    (input_basename, input_extension) = os.path.splitext(input_filename)

    (output_dir, _) = os.path.split(output_list_file)

    cmd = [
        FFMPEG_COMMAND,
        "-nostdin",
        "-i", input_file,
        "-codec", "copy",
        "-f", "segment",
        "-reset_timestamps", "1",
        "-segment_time", f"{segment_time}",
        "-segment_list_type", "m3u8",
        "-segment_list", output_list_file,
        f"{output_dir}/{input_basename}_%d{input_extension}",
    ]

    return cmd, output_list_file


def transcode_video(track, targs, output):
    cmd = transcode_video_command(track, output, targs)
    return exec_cmd(cmd)


def transcode_video_command(track, output_file, targs):
    cmd = [
        FFMPEG_COMMAND,
        "-nostdin",
        # process an input file
        "-i",
        # input file
        "{}".format(track)
    ]

    # video settings
    if 'video' in targs and 'codec' in targs['video']:
        vcodec = targs['video']['codec']
        cmd.append("-c:v")
        cmd.append(get_video_encoder(vcodec))

    if 'frame_rate' in targs:
        fps = str(targs['frame_rate'])
        cmd.append("-r")
        cmd.append(fps)

    if 'video' in targs and 'bitrate' in targs['video']:
        vbitrate = targs['video']['bitrate']
        cmd.append("-b:v")
        cmd.append(vbitrate)

    # audio settings
    if 'audio' in targs and 'codec' in targs['audio']:
        acodec = targs['audio']['codec']
        cmd.append("-c:a")
        cmd.append(get_audio_encoder(acodec))

    if 'audio' in targs and 'bitrate' in targs['audio']:
        abitrate = targs['audio']['bitrate']
        cmd.append("-b:a")
        cmd.append(abitrate)

    if 'resolution' in targs:
        res = targs['resolution']
        cmd.append("-vf")
        cmd.append("scale={}:{}".format(res[0], res[1]))

    if 'scaling_alg' in targs:
        scale = targs["scaling_alg"]
        cmd.append("-sws_flags")
        cmd.append("{}".format(scale))

    cmd.append("{}".format(output_file))

    return cmd


def get_video_encoder(target_codec):
    encoders = {
        "h264": "libx264",
        "h265": "libx265",
        "hevc": "libx265",
        "mpeg1video": "mpeg1video",
        "mpeg2video": "mpeg2video",
        "mpeg4": "libxvid"
    }

    return encoders.get(target_codec, target_codec)


def get_audio_encoder(target_codec):
    encoders = {
        "aac": "aac",
        "mp3": "libmp3lame"
    }

    return encoders.get(target_codec, target_codec)


def merge_videos(input_files, output):
    cmd, _list_file = merge_videos_command(input_files, output)
    exec_cmd(cmd)


def merge_videos_command(input_file, output):
    cmd = [
        FFMPEG_COMMAND,
        "-nostdin",
        "-f", "concat",
        "-safe", "0",
        "-i", input_file,
        "-c", "copy",
        output
    ]

    return cmd, input_file


def replace_streams(input_file,
                    replacement_source,
                    output_file,
                    stream_type):

    assert os.path.isfile(input_file)
    assert os.path.isfile(replacement_source)
    assert not os.path.exists(output_file)

    cmd = replace_streams_command(
        input_file,
        replacement_source,
        output_file,
        stream_type)

    exec_cmd(cmd)


def replace_streams_command(input_file,
                            replacement_source,
                            output_file,
                            stream_type):
    assert stream_type in ['v', 'V', 'a', 's', 'd', 't']

    cmd = [
        FFMPEG_COMMAND,
        "-nostdin",
        "-i", input_file,
        "-i", replacement_source,
        "-map", f"1:{stream_type}",
        "-map", "0",
        "-map", f"-0:{stream_type}",
        "-copy_unknown",
        "-codec", "copy",
        output_file,
    ]

    return cmd

def compute_psnr_command(video, reference_video, psnr_frames_file):
    cmd = [
        FFMPEG_COMMAND,
        "-nostdin",
        "-i", video,
        "-i", reference_video,
        "-lavfi",
        "psnr=" + psnr_frames_file,
        "-f", "null", "-"
    ]

    return cmd


def compute_ssim_command(video, reference_video, ssim_frames_file):
    cmd = [
        FFMPEG_COMMAND,
        "-nostdin",
        "-i", video,
        "-i", reference_video,
        "-lavfi",
        "ssim=" + ssim_frames_file,
        "-f", "null", "-"
    ]

    return cmd


def get_metadata_command(video):
    cmd = [
        FFPROBE_COMMAND,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video
    ]

    return cmd


def get_video_len(input_file):
    cmd = get_metadata_command(input_file)
    result = exec_cmd_to_string(cmd)

    # result should be json
    metadata = json.loads(result)
    format_meta = metadata["format"]

    return float(format_meta["duration"])


def filter_metric(cmd, regex, log_file):
    psnr = exec_cmd_to_string(cmd).splitlines()
    psnr = [line for line in psnr if re.search(regex, line)]

    with open(log_file, "w") as result_file:
        result_file.writelines(psnr)

    return psnr


def compute_psnr(video, reference_video, psnr_frames_file, psnr_log_file):
    cmd = compute_psnr_command(video, reference_video, psnr_frames_file)
    psnr = filter_metric(cmd, r'PSNR', psnr_log_file)

    return psnr


def compute_ssim(video, reference_video, ssim_frames_file, ssim_log_file):
    cmd = compute_ssim_command(video, reference_video, ssim_frames_file)
    ssim = filter_metric(cmd, r'SSIM', ssim_log_file)

    return ssim


def get_metadata(video, outputfile):
    cmd = get_metadata_command(video)
    exec_cmd_to_file(cmd, outputfile)
