pub(super) fn select_relay(advertised: String, configured: String, controller_ws: bool) -> String {
    if controller_ws && !configured.is_empty() {
        configured
    } else {
        advertised
    }
}

#[cfg(test)]
mod tests {
    use super::select_relay;

    #[test]
    fn controller_ws_uses_its_public_entry_instead_of_peer_lan_address() {
        assert_eq!(select_relay("192.0.2.10".into(), "relay.example.com".into(), true), "relay.example.com");
    }

    #[test]
    fn other_clients_and_empty_overrides_keep_the_advertised_relay() {
        for (configured, enabled) in [("relay.example.com", false), ("", true)] {
            assert_eq!(select_relay("192.0.2.10".into(), configured.into(), enabled), "192.0.2.10");
        }
    }
}
