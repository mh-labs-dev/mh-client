#!/bin/bash
set -euo pipefail
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"
tools_root="$project_root/.cache/mh-tools/macos"
mkdir -p "$tools_root"
export CARGO_HOME="$tools_root/cargo" RUSTUP_HOME="$tools_root/rustup"
export PUB_CACHE="$tools_root/pub-cache"
export PATH="$CARGO_HOME/bin:$tools_root/flutter/bin:$tools_root/native-tools/bin:$PATH"
export MACOSX_DEPLOYMENT_TARGET=12.3
export HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_CLEANUP=1

xcodebuild -version
brew install cmake ninja pkg-config autoconf automake libtool cocoapods
if [ ! -x "$CARGO_HOME/bin/rustup" ]; then
    curl --fail --location --retry 3 "https://static.rust-lang.org/rustup/dist/$(uname -m | sed 's/arm64/aarch64/')-apple-darwin/rustup-init" -o "$tools_root/rustup-init"
    chmod +x "$tools_root/rustup-init"
    "$tools_root/rustup-init" -y --no-modify-path --profile minimal --default-toolchain 1.81.0
else
    rustup toolchain install 1.81.0 --profile minimal
fi
if [ ! -d "$tools_root/flutter" ]; then
    git clone --depth 1 --branch 3.24.5 https://github.com/flutter/flutter.git "$tools_root/flutter"
fi
flutter config --no-analytics
flutter precache --macos --no-android --no-ios --no-linux --no-windows --no-web
patch="$project_root/.github/patches/flutter_3.24.4_dropdown_menu_enableFilter.diff"
if ! git -C "$tools_root/flutter" apply --reverse --check "$patch" 2>/dev/null; then
    git -C "$tools_root/flutter" apply "$patch"
fi

# Upstream video ports require NASM 2.x, including when building on Apple Silicon.
if [ ! -x "$tools_root/native-tools/bin/nasm" ]; then
    curl --fail --location --retry 3 https://www.nasm.us/pub/nasm/releasebuilds/2.16.03/nasm-2.16.03.tar.xz -o "$tools_root/nasm-2.16.03.tar.xz"
    python3 - "$tools_root/nasm-2.16.03.tar.xz" <<'PY'
import hashlib, pathlib, sys
assert hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest() == '1412a1c760bbd05db026b6c0d1657affd6631cd0a63cddb6f73cc6d4aa616148', 'NASM archive checksum mismatch'
PY
    tar -xf "$tools_root/nasm-2.16.03.tar.xz" -C "$tools_root"
    (
        cd "$tools_root/nasm-2.16.03"
        ./configure --prefix="$tools_root/native-tools"
        make -j8
        make install
    )
fi
if [ ! -d "$tools_root/vcpkg" ]; then
    git clone --no-checkout https://github.com/microsoft/vcpkg.git "$tools_root/vcpkg"
fi
git -C "$tools_root/vcpkg" checkout --detach 9e593bb18ea69cc5095e012465dcd675a822ed0d
"$tools_root/vcpkg/bootstrap-vcpkg.sh" -disableMetrics
export VCPKG_ROOT="$tools_root/vcpkg"
export VCPKG_OVERLAY_TRIPLETS="$project_root/tools/macos/triplets"
mkdir -p "$tools_root/vcpkg-binary-cache"
export VCPKG_BINARY_SOURCES="clear;files,$tools_root/vcpkg-binary-cache,readwrite"
if [ "$(uname -m)" = arm64 ]; then triplet=arm64-osx; else triplet=x64-osx; fi
export VCPKG_DEFAULT_TRIPLET="$triplet" VCPKG_DEFAULT_HOST_TRIPLET="$triplet"
export VCPKG_MAX_CONCURRENCY=8
"$VCPKG_ROOT/vcpkg" install --triplet "$triplet" --host-triplet "$triplet" --x-install-root="$VCPKG_ROOT/installed"
python3 tools/macos/prepare-bridge.py
cd flutter
flutter pub get
