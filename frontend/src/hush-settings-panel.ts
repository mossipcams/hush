/**
 * Hush Settings Panel
 *
 * A custom panel for configuring Hush notification settings.
 */

import { LitElement, html, css, PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type {
  HomeAssistant,
  HushConfig,
  Category,
  CategoryBehavior,
} from "./types";
import { CATEGORY_ICONS, CATEGORY_NAMES } from "./types";

interface NotifyService {
  service: string;
  name: string;
}

const BEHAVIOR_OPTIONS: { value: CategoryBehavior; label: string }[] = [
  { value: "always_notify", label: "Always notify immediately" },
  { value: "notify_respect_quiet", label: "Notify, respect quiet hours" },
  { value: "notify_once_per_hour", label: "Notify once per hour" },
  { value: "log_only", label: "Log only, don't notify" },
  { value: "notify_with_dedup", label: "Notify with deduplication" },
];

const DEFAULT_BEHAVIORS: Record<Category, CategoryBehavior> = {
  safety: "always_notify",
  security: "notify_respect_quiet",
  device: "notify_once_per_hour",
  motion: "log_only",
  info: "notify_with_dedup",
};

@customElement("hush-settings-panel")
export class HushSettingsPanel extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;
  @property({ type: Boolean }) public narrow = false;

  @state() private _config?: HushConfig;
  @state() private _notifyServices: NotifyService[] = [];
  @state() private _loading = true;
  @state() private _saving = false;
  @state() private _error?: string;
  @state() private _showAdvanced = false;

  static styles = css`
    :host {
      display: block;
      padding: 16px;
      max-width: 600px;
      margin: 0 auto;
    }

    .header {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 24px;
    }

    .header-icon {
      font-size: 2.5em;
    }

    h1 {
      margin: 0;
      font-size: 1.5em;
      font-weight: 500;
    }

    .subtitle {
      color: var(--secondary-text-color);
      margin-top: 4px;
    }

    .card {
      background: var(--card-background-color);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 16px;
      box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0, 0, 0, 0.1));
    }

    .card-title {
      font-size: 1.1em;
      font-weight: 500;
      margin-bottom: 16px;
    }

    .form-row {
      margin-bottom: 20px;
    }

    .form-row:last-child {
      margin-bottom: 0;
    }

    label {
      display: block;
      margin-bottom: 8px;
      font-weight: 500;
    }

    .help-text {
      font-size: 0.85em;
      color: var(--secondary-text-color);
      margin-top: 4px;
    }

    select,
    input[type="time"] {
      width: 100%;
      padding: 12px;
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      background: var(--primary-background-color);
      color: var(--primary-text-color);
      font-size: 1em;
    }

    select:focus,
    input:focus {
      outline: none;
      border-color: var(--primary-color);
    }

    .toggle-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .toggle-label {
      flex: 1;
    }

    .toggle-switch {
      position: relative;
      width: 50px;
      height: 28px;
    }

    .toggle-switch input {
      opacity: 0;
      width: 0;
      height: 0;
    }

    .toggle-slider {
      position: absolute;
      cursor: pointer;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: var(--divider-color);
      transition: 0.3s;
      border-radius: 28px;
    }

    .toggle-slider:before {
      position: absolute;
      content: "";
      height: 22px;
      width: 22px;
      left: 3px;
      bottom: 3px;
      background-color: white;
      transition: 0.3s;
      border-radius: 50%;
    }

    input:checked + .toggle-slider {
      background-color: var(--primary-color);
    }

    input:checked + .toggle-slider:before {
      transform: translateX(22px);
    }

    .time-inputs {
      display: flex;
      gap: 16px;
      align-items: center;
    }

    .time-inputs input {
      flex: 1;
    }

    .time-separator {
      color: var(--secondary-text-color);
    }

    .done-message {
      text-align: center;
      padding: 16px;
      background: var(--success-color, #4caf50);
      color: white;
      border-radius: 8px;
      margin-bottom: 16px;
    }

    .advanced-toggle {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      color: var(--primary-color);
      font-weight: 500;
      margin-top: 8px;
    }

    .advanced-toggle:hover {
      text-decoration: underline;
    }

    .category-row {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
    }

    .category-icon {
      font-size: 1.4em;
      width: 32px;
      text-align: center;
    }

    .category-info {
      flex: 1;
    }

    .category-name {
      font-weight: 500;
    }

    .category-select {
      width: 200px;
    }

    .actions {
      display: flex;
      gap: 12px;
      margin-top: 24px;
    }

    button {
      padding: 12px 24px;
      border: none;
      border-radius: 8px;
      font-size: 1em;
      cursor: pointer;
      transition: opacity 0.2s;
    }

    button:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }

    .primary-button {
      background: var(--primary-color);
      color: var(--text-primary-color, white);
    }

    .secondary-button {
      background: var(--secondary-background-color);
      color: var(--primary-text-color);
    }

    .loading {
      text-align: center;
      padding: 48px;
      color: var(--secondary-text-color);
    }

    .error {
      background: var(--error-color);
      color: white;
      padding: 16px;
      border-radius: 8px;
      margin-bottom: 16px;
    }
  `;

  protected async firstUpdated(_changedProps: PropertyValues): Promise<void> {
    await this._loadConfig();
  }

  private async _loadConfig(): Promise<void> {
    if (!this.hass) return;

    this._loading = true;
    this._error = undefined;

    try {
      // Load current config
      const response = await this.hass.callWS<{
        config: HushConfig;
        notify_services: NotifyService[];
      }>({
        type: "hush/get_config",
      });

      this._config = response.config;
      this._notifyServices = response.notify_services;
    } catch (err) {
      console.error("Failed to load Hush config:", err);
      this._error = "Failed to load configuration. Is Hush configured?";
    } finally {
      this._loading = false;
    }
  }

  private async _saveConfig(): Promise<void> {
    if (!this.hass || !this._config) return;

    this._saving = true;
    this._error = undefined;

    try {
      await this.hass.callWS({
        type: "hush/save_config",
        config: this._config,
      });
    } catch (err) {
      console.error("Failed to save Hush config:", err);
      this._error = "Failed to save configuration";
    } finally {
      this._saving = false;
    }
  }

  protected render() {
    if (this._loading) {
      return html`<div class="loading">Loading...</div>`;
    }

    if (this._error && !this._config) {
      return html`
        <div class="error">${this._error}</div>
        <button class="primary-button" @click=${this._loadConfig}>
          Retry
        </button>
      `;
    }

    return html`
      <div class="header">
        <span class="header-icon">🔕</span>
        <div>
          <h1>Hush Settings</h1>
          <div class="subtitle">Smart notification management</div>
        </div>
      </div>

      ${this._error ? html`<div class="error">${this._error}</div>` : ""}

      <div class="card">
        <div class="card-title">Notification Target</div>
        <div class="form-row">
          <label>Send notifications to</label>
          <select
            .value=${this._config?.delivery_target || ""}
            @change=${this._onTargetChange}
          >
            ${this._notifyServices.map(
              (svc) => html`
                <option value=${svc.service}>${svc.name}</option>
              `
            )}
          </select>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Quiet Hours</div>
        <div class="form-row">
          <div class="toggle-row">
            <div class="toggle-label">
              <label>Enable quiet hours</label>
              <div class="help-text">
                Safety alerts always come through
              </div>
            </div>
            <label class="toggle-switch">
              <input
                type="checkbox"
                .checked=${this._config?.quiet_hours_enabled ?? true}
                @change=${this._onQuietHoursToggle}
              />
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>

        ${this._config?.quiet_hours_enabled
          ? html`
              <div class="form-row">
                <label>Quiet hours window</label>
                <div class="time-inputs">
                  <input
                    type="time"
                    .value=${this._config?.quiet_hours_start || "22:00"}
                    @change=${this._onStartTimeChange}
                  />
                  <span class="time-separator">to</span>
                  <input
                    type="time"
                    .value=${this._config?.quiet_hours_end || "07:00"}
                    @change=${this._onEndTimeChange}
                  />
                </div>
              </div>
            `
          : ""}
      </div>

      <div class="done-message">
        That's it! Smart defaults handle the rest.
      </div>

      <div
        class="advanced-toggle"
        @click=${() => (this._showAdvanced = !this._showAdvanced)}
      >
        <span>${this._showAdvanced ? "▼" : "▶"}</span>
        <span>Advanced Settings</span>
      </div>

      ${this._showAdvanced ? this._renderAdvanced() : ""}

      <div class="actions">
        <button
          class="primary-button"
          @click=${this._saveConfig}
          ?disabled=${this._saving}
        >
          ${this._saving ? "Saving..." : "Save Changes"}
        </button>
      </div>
    `;
  }

  private _renderAdvanced() {
    const categories: Category[] = [
      "safety",
      "security",
      "device",
      "motion",
      "info",
    ];

    return html`
      <div class="card" style="margin-top: 16px">
        <div class="card-title">Category Behavior</div>
        ${categories.map((cat) => this._renderCategoryRow(cat))}
      </div>
    `;
  }

  private _renderCategoryRow(category: Category) {
    const icon = CATEGORY_ICONS[category];
    const name = CATEGORY_NAMES[category];
    const currentBehavior =
      this._config?.category_behaviors?.[category] ||
      DEFAULT_BEHAVIORS[category];

    return html`
      <div class="category-row">
        <span class="category-icon">${icon}</span>
        <div class="category-info">
          <div class="category-name">${name}</div>
        </div>
        <select
          class="category-select"
          .value=${currentBehavior}
          @change=${(e: Event) => this._onBehaviorChange(category, e)}
        >
          ${BEHAVIOR_OPTIONS.map(
            (opt) => html`
              <option value=${opt.value}>${opt.label}</option>
            `
          )}
        </select>
      </div>
    `;
  }

  private _onTargetChange(e: Event): void {
    const target = e.target as HTMLSelectElement;
    this._config = {
      ...this._config!,
      delivery_target: target.value,
    };
  }

  private _onQuietHoursToggle(e: Event): void {
    const target = e.target as HTMLInputElement;
    this._config = {
      ...this._config!,
      quiet_hours_enabled: target.checked,
    };
  }

  private _onStartTimeChange(e: Event): void {
    const target = e.target as HTMLInputElement;
    this._config = {
      ...this._config!,
      quiet_hours_start: target.value,
    };
  }

  private _onEndTimeChange(e: Event): void {
    const target = e.target as HTMLInputElement;
    this._config = {
      ...this._config!,
      quiet_hours_end: target.value,
    };
  }

  private _onBehaviorChange(category: Category, e: Event): void {
    const target = e.target as HTMLSelectElement;
    this._config = {
      ...this._config!,
      category_behaviors: {
        ...this._config!.category_behaviors,
        [category]: target.value as CategoryBehavior,
      },
    };
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "hush-settings-panel": HushSettingsPanel;
  }
}
