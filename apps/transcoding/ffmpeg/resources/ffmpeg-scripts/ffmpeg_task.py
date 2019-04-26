import json
import re
import os

import ffmpeg_commands as ffmpeg

OUTPUT_DIR = "/golem/output"
WORK_DIR = "/golem/work"
RESOURCES_DIR = "/golem/resources"
PARAMS_FILE = "params.json"

TRANSCODED_VIDEO_REGEX = re.compile(r'_(\d+)_TC\.[^.]+')
FFCONCAT_LIST_BASENAME = "merge-input.ffconcat"


class InvalidCommand(Exception):
    pass


def do_extract(input_file, output_file, selected_streams):
    ffmpeg.extract_streams(input_file, output_file, selected_streams)


def do_split(path_to_stream, parts):
    video_length = ffmpeg.get_video_len(path_to_stream)

    segment_list_path = ffmpeg.split_video(
        path_to_stream,
        OUTPUT_DIR,
        video_length / parts)

    with open(segment_list_path) as segment_list_file:
        segment_filenames = segment_list_file.read().splitlines()

    results = {
        'main_list': segment_list_path,
        'segments': [{'video_segment': s} for s in segment_filenames],
    }

    results_file = os.path.join(OUTPUT_DIR, "split-results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f)


def do_extract_and_split(input_file, parts):
    input_basename = os.path.basename(input_file)
    [input_stem, input_extension] = os.path.splitext(input_basename)

    intermediate_file = os.path.join(
        WORK_DIR,
        f"{input_stem}[video-only]{input_extension}")

    do_extract(input_file, intermediate_file, ['v'])
    do_split(intermediate_file, parts)


def do_transcode(track, targs, output):
    ffmpeg.transcode_video(track, targs, output)


def do_merge(chunks, outputfilename):
    def select_transcoded_video_paths(output_file_paths, output_extension):
        return [path
                for path in output_file_paths
                if path.endswith(f'_TC{output_extension}')]


    def sorted_transcoded_video_paths(transcoded_video_paths):
        path_index = {int(re.findall(TRANSCODED_VIDEO_REGEX, path)[0]): path
                      for path in transcoded_video_paths}
        return [value for key, value in sorted(path_index.items())]


    def build_and_store_ffconcat_list(chunks, output_filename, list_basename):
        assert len(chunks) >= 1
        assert len(set(os.path.dirname(chunk) for chunk in chunks)) == 1, \
            "Merge won't work if chunks are not all in the same directory"

        # NOTE: The way the ffmpeg merge command works now, the list file
        # must be in the same directory as the chunks.
        list_filename = os.path.join(os.path.dirname(chunks[0]), list_basename)

        [_output_basename, output_extension] = os.path.splitext(
            os.path.basename(output_filename))

        merge_input_files = sorted_transcoded_video_paths(
            select_transcoded_video_paths(
                chunks,
                output_extension))

        ffconcat_entries = [
            "file '{}'".format(path.replace("'", "\\'"))
            for path in merge_input_files
        ]

        with open(list_filename, 'w') as file:
            file.write('\n'.join(ffconcat_entries))

        return list_filename

    ffconcat_list_filename = build_and_store_ffconcat_list(
        chunks,
        outputfilename,
        FFCONCAT_LIST_BASENAME)
    ffmpeg.merge_videos(ffconcat_list_filename, outputfilename)


def do_replace(input_file,
               replacement_source,
               output_file,
               stream_type):

    ffmpeg.replace_streams(
        input_file,
        replacement_source,
        output_file,
        stream_type)


def do_merge_and_replace(input_file, chunks, output_file):
    output_basename = os.path.basename(output_file)
    [output_stem, output_extension] = os.path.splitext(output_basename)

    intermediate_file = os.path.join(
        WORK_DIR,
        f"{output_stem}[video-only]{output_extension}")

    do_merge(chunks, intermediate_file)
    do_replace(input_file, intermediate_file, output_file, 'v')


def compute_metric(cmd, function):
    video_path = os.path.join(RESOURCES_DIR, cmd["video"])
    reference_path = os.path.join(RESOURCES_DIR, cmd["reference"])
    output = os.path.join(OUTPUT_DIR, cmd["output"])
    log = os.path.join(OUTPUT_DIR, cmd["log"])

    function(video_path, reference_path, output, log)


def get_metadata(cmd):
    video_path = os.path.join(RESOURCES_DIR, cmd["video"])
    output = os.path.join(OUTPUT_DIR, cmd["output"])

    ffmpeg.get_metadata(video_path, output)


def compute_metrics(metrics_params):
    if "ssim" in metrics_params:
        compute_metric(metrics_params["ssim"], ffmpeg.compute_ssim)

    if "psnr" in metrics_params:
        compute_metric(metrics_params["psnr"], ffmpeg.compute_psnr)

    if "metadata" in metrics_params:
        for metadata_request in metrics_params["metadata"]:
            get_metadata(metadata_request)


def run_ffmpeg(params):
    if params['command'] == "extract":
        do_extract(
            params['input_file'],
            params['output_file'],
            params['selected_streams'])
    elif params['command'] == "split":
        do_split(
            params['path_to_stream'],
            params['parts'])
    elif params['command'] == "extract-and-split":
        do_extract_and_split(
            params['input_file'],
            params['parts'])
    elif params['command'] == "transcode":
        do_transcode(
            params['track'],
            params['targs'],
            params['output_stream'])
    elif params['command'] == "merge":
        do_merge(
            params['chunks'],
            params['output_stream'])
    elif params['command'] == "replace":
        do_replace(
            params['input_file'],
            params['replacement_source'],
            params['output_file'],
            params['stream_type'])
    elif params['command'] == "merge-and-replace":
        do_merge_and_replace(
            params['input_file'],
            params['chunks'],
            params['output_file'])
    elif params['command'] == "compute-metrics":
        compute_metrics(
            params["metrics_params"])
    else:
        raise InvalidCommand(f"Invalid command: {params['command']}")


def run():
    params = None
    with open(PARAMS_FILE, 'r') as f:
        params = json.load(f)

    run_ffmpeg(params)


if __name__ == "__main__":
    run()
