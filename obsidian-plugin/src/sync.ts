import JSZip from "jszip";
import { Vault, TFile, Notice } from "obsidian";
import { PwbsAPI, type UploadResponse } from "./api";

const EXCLUDED_DIRS = [".obsidian", ".git", ".trash", "node_modules"];
const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB per file

export class VaultSync {
  constructor(
    private vault: Vault,
    private api: PwbsAPI,
    private excludedFolders: string[],
  ) {}

  updateExcludedFolders(folders: string[]): void {
    this.excludedFolders = folders;
  }

  async sync(): Promise<UploadResponse> {
    if (!this.api.isConfigured) {
      throw new Error(
        "PWBS ist nicht konfiguriert. Bitte API-URL und Token in den Einstellungen setzen.",
      );
    }

    new Notice("PWBS: Vault wird synchronisiert…");

    const zip = await this.buildZip();
    const zipData = await zip.generateAsync({ type: "arraybuffer" });

    const result = await this.api.uploadVault(zipData);

    new Notice(
      `PWBS: ${result.documents_count} Docs synced` +
        (result.deleted_count > 0 ? `, ${result.deleted_count} entfernt` : ""),
    );

    return result;
  }

  private async buildZip(): Promise<JSZip> {
    const zip = new JSZip();
    const files = this.vault.getMarkdownFiles();
    let included = 0;

    for (const file of files) {
      if (this.isExcluded(file)) continue;

      if (file.stat.size > MAX_FILE_SIZE) continue;

      const content = await this.vault.cachedRead(file);
      zip.file(file.path, content);
      included++;
    }

    if (included === 0) {
      throw new Error(
        "Keine Markdown-Dateien zum Synchronisieren gefunden. Prüfe die Ausschluss-Einstellungen.",
      );
    }

    return zip;
  }

  private isExcluded(file: TFile): boolean {
    const pathParts = file.path.split("/");

    for (const part of pathParts) {
      if (EXCLUDED_DIRS.includes(part)) return true;
      if (this.excludedFolders.includes(part)) return true;
    }

    return false;
  }
}
