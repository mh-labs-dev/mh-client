get_filename_component(MH_SOURCE_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
# __FILE__ in Opus/FFmpeg assertions survives symbol stripping. Apply the mapping
# while compiling the static dependencies as well as the application itself.
set(VCPKG_C_FLAGS "-ffile-prefix-map=\"${MH_SOURCE_ROOT}\"=/build/mh-client")
set(VCPKG_CXX_FLAGS "${VCPKG_C_FLAGS}")
list(APPEND VCPKG_HASH_ADDITIONAL_FILES "${CMAKE_CURRENT_LIST_FILE}")
