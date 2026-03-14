use tauri::{
    menu::{Menu, MenuEvent, MenuItem, PredefinedMenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    App, AppHandle, Manager,
};

pub fn create_tray(app: &mut App) -> Result<(), Box<dyn std::error::Error>> {
    let dashboard =
        MenuItem::with_id(app, "dashboard", "Dashboard \u{00f6}ffnen", true, None::<&str>)?;
    let search = MenuItem::with_id(app, "search", "Suche", true, None::<&str>)?;
    let briefing =
        MenuItem::with_id(app, "briefing", "Heutiges Briefing", true, None::<&str>)?;
    let separator = PredefinedMenuItem::separator(app)?;
    let quit = MenuItem::with_id(app, "quit", "Beenden", true, None::<&str>)?;

    let menu = Menu::with_items(app, &[&dashboard, &search, &briefing, &separator, &quit])?;

    let _tray = TrayIconBuilder::new()
        .icon(app.default_window_icon().unwrap().clone())
        .menu(&menu)
        .show_menu_on_left_click(false)
        .tooltip("PWBS")
        .on_menu_event(handle_menu_event)
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                let app = tray.app_handle();
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
        })
        .build(app)?;

    Ok(())
}

fn handle_menu_event(app: &AppHandle, event: MenuEvent) {
    let navigate = |path: &str| {
        if let Some(window) = app.get_webview_window("main") {
            let js = format!("window.location.href = '{}'", path);
            let _ = window.eval(&js);
            let _ = window.show();
            let _ = window.set_focus();
        }
    };

    match event.id.as_ref() {
        "dashboard" => navigate("/"),
        "search" => navigate("/search"),
        "briefing" => navigate("/briefings"),
        "quit" => app.exit(0),
        _ => {}
    }
}
