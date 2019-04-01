#!/bin/bash -e

source "$(dirname ${BASH_SOURCE[0]})/common.sh"
source "$(dirname ${BASH_SOURCE[0]})/transcoding-steps.sh"

input_file="$1"
output_dir="$2"

input_file_in_container="/tmp/$(basename "$input_file")"


build_ffmpeg_image

do_split                       \
    "$output_dir"              \
    split/resources            \
    split/work                 \
    split/output               \
    "$input_file"              \
    "$input_file_in_container" \
    5

chunk_stem="$(strip_extension "$(basename "$input_file")")"

do_transcode                   \
    "$output_dir"              \
    split/output/              \
    transcode/work             \
    transcode/output           \
    "$input_file"              \
    "$input_file_in_container" \
    "$chunk_stem"              \
    true                       \
    mpeg2video                 \
    1000k                      \
    mp3                        \
    128k                       \
    "[160, 120]"               \
    25

do_merge                       \
    "$output_dir"              \
    transcode/output           \
    merge/work                 \
    merge/output               \
    "$input_file"              \
    "$input_file_in_container" \
    "$(basename $input_file)"
