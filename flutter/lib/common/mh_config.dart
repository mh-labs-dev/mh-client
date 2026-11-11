/// Product switches shared by the Windows and macOS desktop builds.
/// MH_WINDOWS remains an alias for existing Windows build commands.
const bool isMhDesktop =
    bool.fromEnvironment('MH_DESKTOP') || bool.fromEnvironment('MH_WINDOWS');

/// A controller build uses the same login and device list on either desktop OS.
/// Its native library must enable MH_CONTROLLER (or provide MH_CONTROLLER_PROFILE).
const bool isMhController =
    isMhDesktop && bool.fromEnvironment('MH_CONTROLLER');

/// Unconfigured previews keep the controller UI but must not send credentials.
/// Existing Windows builds already provide a profile and retain their behavior.
const bool isMhControllerConfigured =
    bool.fromEnvironment('MH_CONTROLLER_CONFIGURED', defaultValue: true);
