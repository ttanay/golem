source "$(dirname ${BASH_SOURCE[0]})/common.sh"


function do_extract {
    local output_dir="$1"
    local resources_subdir="$2"
    local work_subdir="$3"
    local output_subdir="$4"
    local input_file="$5"
    local input_file_in_container="$6"

    mkdir --parents "$output_dir/$work_subdir/"

    cat <<EOF > "$output_dir/$work_subdir/params.json"
    {
        "script_filepath":  "/golem/scripts/ffmpeg_task.py",
        "command":          "extract",
        "input_file":       "$input_file_in_container",
        "output_file":      "/golem/output/$(strip_extension "$(basename $input_file)")[video-only].$(get_extension "$(basename $input_file)")",
        "selected_streams": ["v"]
    }
EOF

    run_ffmpeg_command      \
        "$output_dir"       \
        "$resources_subdir" \
        "$work_subdir"      \
        "$output_subdir"    \
        "$input_file"       \
        "$input_file_in_container"
}


function do_split {
    local output_dir="$1"
    local resources_subdir="$2"
    local work_subdir="$3"
    local output_subdir="$4"
    local input_file="$5"
    local input_file_in_container="$6"
    local parts="$7"

    mkdir --parents "$output_dir/$work_subdir/"

    cat <<EOF > "$output_dir/$work_subdir/params.json"
    {
        "script_filepath": "/golem/scripts/ffmpeg_task.py",
        "command":         "split",
        "path_to_stream":  "$input_file_in_container",
        "parts":           $parts
    }
EOF

    run_ffmpeg_command      \
        "$output_dir"       \
        "$resources_subdir" \
        "$work_subdir"      \
        "$output_subdir"    \
        "$input_file"       \
        "$input_file_in_container"
}


function do_transcode {
    local output_dir="$1"
    local resources_subdir="$2"
    local work_subdir="$3"
    local output_subdir="$4"
    local input_file="$5"
    local input_file_in_container="$6"
    local chunk_stem="$7"
    local use_playlist="$8"
    local video_codec="$9"
    local video_bitrate="${10}"
    local audio_codec="${11}"
    local audio_bitrate="${12}"
    local resolution="${13}"
    local frame_rate="${14}"

    local input_format="$(get_extension $input_file)"
    local output_format="$input_format"
    local chunks="$(find "$output_dir/$resources_subdir" -name "$(printf "%q" "$chunk_stem")_*.$input_format")"

    mkdir --parents "$output_dir/$work_subdir/"

    for chunk in $chunks; do
        cat <<EOF > "$output_dir/$work_subdir/params.json"
        {
            "script_filepath": "/golem/scripts/ffmpeg_task.py",
            "command":         "transcode",
            "track":           "/golem/resources/$(basename "$chunk")",
            "output_stream":   "/golem/output/$(strip_extension "$(basename "$chunk")")_TC.$output_format",
            "use_playlist":    $use_playlist,
            "targs": {
                "video": {
                    "codec":   "$video_codec",
                    "bitrate": "$video_bitrate"
                },
                "audio": {
                    "codec":   "$audio_codec",
                    "bitrate": "$audio_bitrate"
                },
                "resolution":  $resolution,
                "frame_rate":  "$frame_rate"
            }
        }
EOF

        run_ffmpeg_command      \
            "$output_dir"       \
            "$resources_subdir" \
            "$work_subdir"      \
            "$output_subdir"    \
            "$input_file"       \
            "$input_file_in_container"
    done
}


function do_merge {
    local output_dir="$1"
    local resources_subdir="$2"
    local work_subdir="$3"
    local output_subdir="$4"
    local input_file="$5"
    local input_file_in_container="$6"
    local output_file_basename="$7"

    # Golem just grabs all files from the output. The merge command in the image has
    # to be able to filter out things that are not videos to be merged on its own.
    local chunks="$(find "$output_dir/$resources_dir" -name '*')"

    mkdir --parents "$output_dir/$work_subdir/"

    cat <<EOF > "$output_dir/$work_subdir/params.json"
    {
        "script_filepath": "/golem/scripts/ffmpeg_task.py",
        "command":         "merge",
        "output_stream":   "/golem/output/$output_file_basename",
        "chunks":          $(strings_to_json_list /golem/resources/ $(strip_paths "$chunks"))
    }
EOF

    run_ffmpeg_command      \
        "$output_dir"       \
        "$resources_subdir" \
        "$work_subdir"      \
        "$output_subdir"    \
        "$input_file"       \
        "$input_file_in_container"
}


function do_replace {
    local output_dir="$1"
    local resources_subdir="$2"
    local work_subdir="$3"
    local output_subdir="$4"
    local input_file="$5"
    local input_file_in_container="$6"
    local replacement_source_in_container="$7"

    mkdir --parents "$output_dir/$work_subdir/"

    cat <<EOF > "$output_dir/$work_subdir/params.json"
    {
        "script_filepath":    "/golem/scripts/ffmpeg_task.py",
        "command":            "replace",
        "input_file":         "$input_file_in_container",
        "replacement_source": "$replacement_source_in_container",
        "output_file":        "/golem/output/$(basename $input_file)",
        "stream_type":        "v"
    }
EOF

    run_ffmpeg_command      \
        "$output_dir"       \
        "$resources_subdir" \
        "$work_subdir"      \
        "$output_subdir"    \
        "$input_file"       \
        "$input_file_in_container"
}
