import { App, PluginSettingTab, Setting } from "obsidian";
import type PwbsPlugin from "./main";

export interface PwbsSettings {
  apiUrl: string;
  apiToken: string;
  excludedFolders: string;
  autoSyncMinutes: number;
}

export const DEFAULT_SETTINGS: PwbsSettings = {
  apiUrl: "https://api.pwbs.app",
  apiToken: "",
  excludedFolders: "",
  autoSyncMinutes: 0,
};

export class PwbsSettingTab extends PluginSettingTab {
  plugin: PwbsPlugin;

  constructor(app: App, plugin: PwbsPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();

    // Connection section
    new Setting(containerEl).setName("Verbindung").setHeading();

    new Setting(containerEl)
      .setName("API URL")
      .setDesc("Die URL deiner PWBS-Instanz")
      .addText((text) =>
        text
          .setPlaceholder("https://api.pwbs.app")
          .setValue(this.plugin.settings.apiUrl)
          .onChange(async (value) => {
            this.plugin.settings.apiUrl = value;
            await this.plugin.saveSettings();
          }),
      );

    new Setting(containerEl)
      .setName("API Token")
      .setDesc(
        "Dein persönlicher API-Token. Findest du unter pwbs.app → Einstellungen → API.",
      )
      .addText((text) => {
        text
          .setPlaceholder("pwbs_xxxxxxxxxxxxxxxx")
          .setValue(this.plugin.settings.apiToken)
          .onChange(async (value) => {
            this.plugin.settings.apiToken = value;
            await this.plugin.saveSettings();
          });
        text.inputEl.type = "password";
      });

    const testBtn = new Setting(containerEl)
      .setName("Verbindung testen")
      .setDesc("Prüft ob API-URL und Token korrekt sind");

    testBtn.addButton((btn) =>
      btn.setButtonText("Testen").onClick(async () => {
        btn.setDisabled(true);
        btn.setButtonText("Teste…");
        try {
          const user = await this.plugin.api.getMe();
          testBtn.setDesc(`✅ Verbunden als ${user.display_name}`);
        } catch (e) {
          testBtn.setDesc(
            `❌ ${e instanceof Error ? e.message : "Verbindungsfehler"}`,
          );
        } finally {
          btn.setDisabled(false);
          btn.setButtonText("Testen");
        }
      }),
    );

    // Sync section
    new Setting(containerEl).setName("Synchronisation").setHeading();

    new Setting(containerEl)
      .setName("Ausgeschlossene Ordner")
      .setDesc(
        "Komma-getrennte Liste von Ordnern die nicht synchronisiert werden (z.B. private,archiv)",
      )
      .addText((text) =>
        text
          .setPlaceholder("private,archiv,templates")
          .setValue(this.plugin.settings.excludedFolders)
          .onChange(async (value) => {
            this.plugin.settings.excludedFolders = value;
            await this.plugin.saveSettings();
          }),
      );

    new Setting(containerEl)
      .setName("Auto-Sync (Minuten)")
      .setDesc("Automatische Synchronisation alle X Minuten. 0 = deaktiviert.")
      .addSlider((slider) =>
        slider
          .setLimits(0, 120, 15)
          .setValue(this.plugin.settings.autoSyncMinutes)
          .setDynamicTooltip()
          .onChange(async (value) => {
            this.plugin.settings.autoSyncMinutes = value;
            await this.plugin.saveSettings();
            this.plugin.restartAutoSync();
          }),
      );

    // Info section
    new Setting(containerEl).setName("Info").setHeading();
    containerEl.createEl("p", {
      text: "PWBS verwandelt dein Wissen in kontextbezogene Briefings – morgens, vor Meetings oder für Projekte.",
      cls: "setting-item-description",
    });
    containerEl.createEl("a", {
      text: "→ Mehr erfahren auf pwbs.app",
      href: "https://pwbs.app",
    });
  }
}
