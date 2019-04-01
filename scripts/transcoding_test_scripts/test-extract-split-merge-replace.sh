#!/bin/bash -e

source "$(dirname ${BASH_SOURCE[0]})/common.sh"
source "$(dirname ${BASH_SOURCE[0]})/transcoding-steps.sh"

input_file="$1"
output_dir="$2"

input_file_in_container="/tmp/$(basename "$input_file")"


build_ffmpeg_image

mkdir --parents "$output_dir/tmp/work"
mkdir --parents "$output_dir/tmp/merge/work"


do_extract                     \
    "$output_dir"              \
    resources                  \
    .                          \
    output                     \
    "$input_file"              \
    "$input_file_in_container"

input_video_only_basename="$(strip_extension "$(basename $input_file)")[video-only].$(get_extension "$(basename $input_file)")"

do_split                                       \
    "$output_dir"                              \
    resources                                  \
    .                                          \
    output                                     \
    "$input_file"                              \
    "/golem/output/$input_video_only_basename" \
    5

input_format="$(get_extension $input_file)"
output_format="$input_format"
mkdir --parents "$output_dir/tmp/"{resources,work}
cp "$output_dir/output/"*".$output_format" "$output_dir/tmp/resources/"

chunk_stem="$(strip_extension "$input_video_only_basename")"

do_transcode                   \
    "$output_dir"              \
    tmp/resources              \
    tmp/work                   \
    tmp                        \
    "$input_file"              \
    "$input_file_in_container" \
    "$chunk_stem"              \
    false                      \
    mpeg2video                 \
    1000k                      \
    mp3                        \
    128k                       \
    "[160, 120]"               \
    25

do_merge                       \
    "$output_dir"              \
    tmp                        \
    tmp/merge/work             \
    tmp/merge/output           \
    "$input_file"              \
    "$input_file_in_container" \
    "$input_video_only_basename"

do_replace                     \
    "$output_dir"              \
    tmp                        \
    tmp/merge/work             \
    tmp/merge/output           \
    "$input_file"              \
    "$input_file_in_container" \
    "/golem/output/$input_video_only_basename"
