#!/bin/bash -e

resource_dir="tests/apps/ffmpeg/resources/"
package_name="transcoding-video-bundle-v3.zip"

mkdir --parents "$resource_dir/videos/"
cd "$resource_dir"

curl --remote-name "http://builder.concent.golem.network/download/$package_name"
unzip "$package_name" -d videos/

# Remove the top-level directory
mv "videos/transcoding-video-bundle/"* "videos/"
rm -r "videos/transcoding-video-bundle/"
