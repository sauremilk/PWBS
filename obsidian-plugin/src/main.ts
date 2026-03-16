import { Plugin, Notice } from "obsidian";
import { PwbsAPI, PwbsAuthError } from "./api";
import { VaultSync } from "./sync";
import { BriefingView, BRIEFING_VIEW_TYPE } from "./briefing-view";
import {
  PwbsSettingTab,
  DEFAULT_SETTINGS,
  type PwbsSettings,
} from "./settings";

export default class PwbsPlugin extends Plugin {
  settings: PwbsSettings = DEFAULT_SETTINGS;
  api: PwbsAPI = new PwbsAPI("", "");
  private sync: VaultSync | null = null;
  private autoSyncInterval: number | null = null;

  async onload(): Promise<void> {
    await this.loadSettings();

    this.api = new PwbsAPI(this.settings.apiUrl, this.settings.apiToken);

    this.sync = new VaultSync(
      this.app.vault,
      this.api,
      this.getExcludedFolders(),
    );

    // Register the briefing sidebar view
    this.registerView(
      BRIEFING_VIEW_TYPE,
      (leaf) => new BriefingView(leaf, this.api),
    );

    // Command: Sync vault
    this.addCommand({
      id: "sync-vault",
      name: "Vault synchronisieren",
      callback: () => this.runSync(),
    });

    // Command: Open briefing
    this.addCommand({
      id: "open-briefing",
      name: "Briefing anzeigen",
      callback: () => this.activateBriefingView(),
    });

    // Command: Refresh briefing
    this.addCommand({
      id: "refresh-briefing",
      name: "Briefing aktualisieren",
      callback: () => this.refreshBriefing(),
    });

    // Settings tab
    this.addSettingTab(new PwbsSettingTab(this.app, this));

    // Ribbon icon for quick sync
    this.addRibbonIcon("zap", "PWBS: Vault synchronisieren", () =>
      this.runSync(),
    );

    // Auto-sync
    this.restartAutoSync();

    // Open briefing view on startup if configured
    if (this.api.isConfigured) {
      this.app.workspace.onLayoutReady(() => {
        this.activateBriefingView();
      });
    }
  }

  onunload(): void {
    this.stopAutoSync();
  }

  async loadSettings(): Promise<void> {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings(): Promise<void> {
    await this.saveData(this.settings);
    this.api.updateConfig(this.settings.apiUrl, this.settings.apiToken);
    this.sync?.updateExcludedFolders(this.getExcludedFolders());
  }

  private getExcludedFolders(): string[] {
    return this.settings.excludedFolders
      .split(",")
      .map((f) => f.trim())
      .filter((f) => f.length > 0);
  }

  private async runSync(): Promise<void> {
    if (!this.sync) return;

    if (!this.api.isConfigured) {
      new Notice(
        "PWBS: Bitte zuerst API-URL und Token in den Einstellungen konfigurieren.",
      );
      return;
    }

    try {
      await this.sync.sync();
    } catch (e) {
      if (e instanceof PwbsAuthError) {
        new Notice(
          "PWBS: API-Token ungültig. Bitte in den Einstellungen prüfen.",
        );
      } else {
        new Notice(
          `PWBS: Sync fehlgeschlagen – ${e instanceof Error ? e.message : "Unbekannter Fehler"}`,
        );
      }
    }
  }

  async activateBriefingView(): Promise<void> {
    const existing = this.app.workspace.getLeavesOfType(BRIEFING_VIEW_TYPE);

    if (existing.length > 0) {
      this.app.workspace.revealLeaf(existing[0]);
      return;
    }

    const leaf = this.app.workspace.getRightLeaf(false);
    if (leaf) {
      await leaf.setViewState({
        type: BRIEFING_VIEW_TYPE,
        active: true,
      });
      this.app.workspace.revealLeaf(leaf);
    }
  }

  private async refreshBriefing(): Promise<void> {
    const leaves = this.app.workspace.getLeavesOfType(BRIEFING_VIEW_TYPE);
    for (const leaf of leaves) {
      const view = leaf.view;
      if (view instanceof BriefingView) {
        await view.refresh();
      }
    }
  }

  restartAutoSync(): void {
    this.stopAutoSync();

    const minutes = this.settings.autoSyncMinutes;
    if (minutes <= 0) return;

    this.autoSyncInterval = window.setInterval(
      () => this.runSync(),
      minutes * 60 * 1000,
    );
    this.registerInterval(this.autoSyncInterval);
  }

  private stopAutoSync(): void {
    if (this.autoSyncInterval !== null) {
      window.clearInterval(this.autoSyncInterval);
      this.autoSyncInterval = null;
    }
  }
}
