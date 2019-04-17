#!/bin/bash -e

input_file="$1"

log_level=error
function ffprobe_show_entries {
    local input_file="$1"
    local query="$2"

    printf "%s" $(
        ffprobe                                              \
            -v            error                              \
            -show_entries "$query"                           \
            -of           default=noprint_wrappers=1:nokey=1 \
            "$input_file"
    )
}

function ffprobe_get_stream_attribute {
    local input_file="$1"
    local stream="$2"
    local attribute="$3"

    printf "%s" $(
        ffprobe                                                \
            -v              error                              \
            -select_streams "$stream"                          \
            -show_entries   "stream=$attribute"                \
            -of             default=noprint_wrappers=1:nokey=1 \
            "$input_file"
    )
}

video_codec="$(ffprobe_get_stream_attribute "$input_file" "v:0" codec_name)"

width="$(ffprobe_get_stream_attribute "$input_file" "v:0" width)"
height="$(ffprobe_get_stream_attribute "$input_file" "v:0" height)"

duration="$(ffprobe_show_entries "$input_file" format=duration)"

video_stream_count="$(ffprobe -show_entries stream=codec_type -select_streams v -of default=noprint_wrappers=1:nokey=1 -hide_banner -v error "$input_file" | wc -l)"
audio_stream_count="$(ffprobe -show_entries stream=codec_type -select_streams a -of default=noprint_wrappers=1:nokey=1 -hide_banner -v error "$input_file" | wc -l)"
sub_stream_count="$(ffprobe -show_entries stream=codec_type -select_streams s -of default=noprint_wrappers=1:nokey=1 -hide_banner -v error "$input_file" | wc -l)"
data_stream_count="$(ffprobe -show_entries stream=codec_type -select_streams d -of default=noprint_wrappers=1:nokey=1 -hide_banner -v error "$input_file" | wc -l)"

if (( $audio_stream_count > 0 )); then
    for (( index=0; index < ${audio_stream_count}; index=index+1 )); do
        audio_codec="$(ffprobe_get_stream_attribute "$input_file" "a:$index" codec_name)"
        video_codec="$video_codec+$audio_codec"
    done
fi

stream_count="$(printf "v%sa%ss%sd%s" "$video_stream_count" "$audio_stream_count" "$sub_stream_count" "$data_stream_count")"

frames=$(ffprobe -show_frames "$input_file" 2> /dev/null | grep "pict_type=" | sed 's/pict_type=\(.*\)$/\1/' | tr -d '\n')
frame_count="$(echo -n "$frames"                   | wc --chars)"
i_frame_count="$(echo -n "$frames" | sed 's/[^I]//g' | wc --chars)"
p_frame_count="$(echo -n "$frames" | sed 's/[^P]//g' | wc --chars)"
b_frame_count="$(echo -n "$frames" | sed 's/[^B]//g' | wc --chars)"

frame_rate="$(ffprobe_get_stream_attribute "$input_file" "v:0" r_frame_rate)"
frame_rate_float=$(
    python -c "print($frame_rate)"
)

printf "[%s,%sx%s,%.0fs,%s,i%dp%db%d,fps%.2f]\n" "$video_codec" "$width" "$height" "$duration" "$stream_count" "$i_frame_count" "$p_frame_count" "$b_frame_count" "$frame_rate_float"
