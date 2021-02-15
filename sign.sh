#!/bin/sh

TOOLS=~/Android/Sdk/build-tools/30.0.3/
KEYSTORE=release-key.jks
DIR=bin
APK=$(echo "$DIR"/*release*)

ALIGNED="$DIR/aligned.apk"
SIGNED="$DIR/signed.apk"

echo Signing $APK

[ -e "$ALIGNED" ] && rm "$ALIGNED"
"$TOOLS/zipalign" -v -p 4 "$APK" "$ALIGNED"

[ -e "$SIGNED" ] && rm "$SIGNED"
"$TOOLS/apksigner" sign --ks "$KEYSTORE" --ks-pass="pass:helloworld" --out "$SIGNED" "$ALIGNED"
