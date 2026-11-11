//! MH desktop product behavior shared by Windows and macOS.
//! Keep OS integration in `platform`; this module owns branding and controller policy.

use hbb_common::{
    config::{self, Config},
    log,
};

mod relay;

pub(crate) fn relay_server(advertised: String) -> String {
    let selected = relay::select_relay(
        advertised.clone(),
        Config::get_option("relay-server"),
        option_env!("MH_CONTROLLER_PROFILE").is_some() && config::use_ws(),
    );
    if selected != advertised {
        log::info!("MH controller relay endpoint: {}", selected);
    }
    selected
}

pub(crate) fn init() {
    // Keep the established Windows names and configuration precedence on both platforms.
    *config::APP_NAME.write().unwrap() = "MH".to_owned();
    if let Some(profile) = option_env!("MH_CONTROLLER_PROFILE") {
        *config::APP_NAME.write().unwrap() = "MH Test".to_owned();
        match serde_json::from_str::<std::collections::HashMap<String, String>>(profile) {
            Ok(settings) => config::DEFAULT_SETTINGS.write().unwrap().extend(settings),
            Err(err) => log::error!("Invalid controller build profile: {}", err),
        }
        let mut settings = config::HARD_SETTINGS.write().unwrap();
        settings.insert("conn-type".to_owned(), "outgoing".to_owned());
        settings.insert("disable-tcp-listen".to_owned(), "Y".to_owned());
    }
}
