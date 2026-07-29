#!/bin/zsh
set -euo pipefail

ROOT="${0:A:h:h}"
VERSION="1.0.31"
RELEASE_DIR="$ROOT/release/v$VERSION"
STAGE_DIR="$RELEASE_DIR/dmg-root"
APP_SOURCE="$ROOT/desktop/dist/影序 YINGXU.app"
DMG_PATH="$RELEASE_DIR/YINGXU-macOS-v$VERSION.dmg"

[[ -d "$APP_SOURCE" ]] || { print -u2 "缺少已构建应用：$APP_SOURCE"; exit 1; }
mkdir -p "$STAGE_DIR"
ditto "$APP_SOURCE" "$STAGE_DIR/影序 YINGXU.app"
ln -sfn /Applications "$STAGE_DIR/Applications"
codesign --force --deep --sign - "$STAGE_DIR/影序 YINGXU.app"
codesign --verify --deep --strict "$STAGE_DIR/影序 YINGXU.app"
hdiutil create -volname "影序 YINGXU" -srcfolder "$STAGE_DIR" -ov -format UDZO "$DMG_PATH"
hdiutil verify "$DMG_PATH"
(cd "$RELEASE_DIR" && shasum -a 256 "$(basename "$DMG_PATH")" > SHA256SUMS.txt)
print "已生成：$DMG_PATH"
cat "$RELEASE_DIR/SHA256SUMS.txt"
