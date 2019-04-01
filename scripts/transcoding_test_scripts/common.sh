function get_extension {
    local file_path="$1"

    local file_basename="$(basename "$file_path")"
    local file_extension="${file_basename##*.}"

    printf "%s" $file_extension
}


function strip_extension {
    local file_path="$1"

    printf "%s" "${file_path%.*}"
}


function strip_paths {
    local file_names="$@"

    result=""
    for file_name in $file_names; do
        result="$result $(basename "$file_name")"
    done

    printf "%s" "$result"
}


function strings_to_json_list {
    local prefix="$1"
    local values=("${@:2}")

    if [[ ${#values[@]} > 0 ]]; then
        result=\"$prefix${values[0]}\"
        unset values[0]

        for value in ${values[@]}; do
            result="$result,\"$prefix$value\""
        done

        printf "[%s]" "$result"
    fi
}


function run_ffmpeg_command {
    local output_dir="$1"
    local resource_subdir="$2"
    local work_subdir="$3"
    local output_subdir="$4"
    local input_file="$5"
    local input_file_in_container="$6"

    mkdir --parents "$output_dir/$resource_subdir"
    mkdir --parents "$output_dir/$work_subdir"
    mkdir --parents "$output_dir/$output_subdir"

    docker run                                                    \
        --rm                                                      \
        --volume "$output_dir/$resource_subdir:/golem/resources/" \
        --volume "$output_dir/$work_subdir:/golem/work/"          \
        --volume "$output_dir/$output_subdir:/golem/output/"      \
        --volume "$input_file:$input_file_in_container:ro"        \
        ffmpeg-debug                                              \
            python3 /golem/scripts/ffmpeg_task.py
}


function build_ffmpeg_image {
    base_dir=../../apps/transcoding/ffmpeg/resources
    docker build                                    \
        --file "$base_dir/images/ffmpeg.Dockerfile" \
        --tag ffmpeg-debug                          \
        "$base_dir"
}
