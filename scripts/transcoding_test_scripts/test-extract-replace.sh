#!/bin/bash -e

source "$(dirname ${BASH_SOURCE[0]})/common.sh"
source "$(dirname ${BASH_SOURCE[0]})/transcoding-steps.sh"

input_file="$1"
output_dir="$2"

input_file_in_container="/tmp/$(basename "$input_file")"


build_ffmpeg_image


do_extract                     \
    "$output_dir"              \
    extract/resources          \
    extract/work               \
    extract/output             \
    "$input_file"              \
    "$input_file_in_container"

do_replace                     \
    "$output_dir"              \
    extract/output             \
    replace/work               \
    replace/output             \
    "$input_file"              \
    "$input_file_in_container" \
    "/golem/resources/$(strip_extension "$(basename $input_file)")[video-only].$(get_extension "$(basename $input_file)")"
