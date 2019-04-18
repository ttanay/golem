#!/bin/bash -e

input_file="$1"

log_level=error

function ffprobe_show_entries {
    local input_file="$1"
    local query="$2"
    local stream="$3"
    local extra_format="$4"

    if [[ "$stream" != "" ]]; then
        stream_selector="-select_streams $stream"
    else
        stream_selector=""
    fi

    raw_result="$(
        ffprobe                                          \
            -v            error                          \
            $stream_selector                             \
            -show_entries "$query"                       \
            -of           "compact=nokey=1$extra_format" \
            "$input_file"                                   |
            grep --invert-match --regexp "^program|stream|" |
            grep --invert-match --regexp "^$"               |
            cut --delimiter '|' --field 2
    )"

    # NOTE: If the file contains side data `ffprobe -show_entries stream` prints [SIDE_DATA] section in addition to the usual [STREAM].
    # When using the `compact` output format it gets attached to the end of the last value without a separating newline.
    # I don't see a way to tell ffprobe not to do it so we'll just strip it from the end of the string if present.
    result="${raw_result%side_data}"

    printf "%s" "$result"
}

width="$(ffprobe_show_entries  "$input_file" stream=width  "v:0")"
height="$(ffprobe_show_entries "$input_file" stream=height "v:0")"

duration="$(ffprobe_show_entries "$input_file" format=duration)"
if [[ "$duration" == "N/A" ]]; then
    duration_string="_"
else
    duration_string="$(printf "%.0fs" "$duration")"
fi

video_stream_count="$(ffprobe_show_entries   "$input_file" stream=codec_type v | grep --count "")" || true
audio_stream_count="$(ffprobe_show_entries   "$input_file" stream=codec_type a | grep --count "")" || true
subitle_stream_count="$(ffprobe_show_entries "$input_file" stream=codec_type d | grep --count "")" || true
data_stream_count="$(ffprobe_show_entries    "$input_file" stream=codec_type s | grep --count "")" || true

stream_counts="$(printf "v%da%ds%dd%d" "$video_stream_count" "$audio_stream_count" "$subtitle_stream_count" "$data_stream_count")"

codecs="$(ffprobe_show_entries "$input_file" stream=codec_name "v:0" )"
for (( index=0; index < ${audio_stream_count}; index=index+1 )); do
    codec="$(ffprobe_show_entries "$input_file" stream=codec_name "a:$index")"
    codecs="$codecs+$codec"
done

frames=$(ffprobe_show_entries "$input_file" frame=pict_type v:0)
frame_count="$(echo   -n "$frames"                   | wc --chars)"
i_frame_count="$(echo -n "$frames" | sed 's/[^I]//g' | wc --chars)"
p_frame_count="$(echo -n "$frames" | sed 's/[^P]//g' | wc --chars)"
b_frame_count="$(echo -n "$frames" | sed 's/[^B]//g' | wc --chars)"

frame_rate="$(ffprobe_show_entries "$input_file" stream=avg_frame_rate "v:0")"
if [[ "$frame_rate" != "0/0" ]]; then
    frame_rate_string="$(printf "%gfps" "$(python -c "print($frame_rate)")")"
else
    frame_rate_string="_"
fi

printf "[%s,%sx%s,%s,%s,i%dp%db%d,%s]\n" "$codecs" "$width" "$height" "$duration_string" "$stream_counts" "$i_frame_count" "$p_frame_count" "$b_frame_count" "$frame_rate_string"
