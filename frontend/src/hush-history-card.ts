/**
 * Hush Notification History Card
 *
 * A Lovelace card that displays recent notifications with smart grouping.
 */

import { LitElement, html, css, PropertyValues } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type {
  HomeAssistant,
  LovelaceCardConfig,
  NotificationRecord,
  TodayStats,
  Category,
} from "./types";
import { CATEGORY_ICONS, CATEGORY_COLORS } from "./types";

interface HushHistoryCardConfig extends LovelaceCardConfig {
  title?: string;
  limit?: number;
}

@customElement("hush-history-card")
export class HushHistoryCard extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;
  @state() private _config?: HushHistoryCardConfig;
  @state() private _notifications: NotificationRecord[] = [];
  @state() private _stats: TodayStats = {
    total: 0,
    safety_count: 0,
    delivered_count: 0,
  };
  @state() private _loading = true;
  @state() private _error?: string;

  private _unsubscribe?: () => void;

  static styles = css`
    :host {
      display: block;
    }

    ha-card {
      padding: 16px;
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }

    .card-title {
      font-size: 1.2em;
      font-weight: 500;
    }

    .notification-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .notification-item {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 8px;
      border-radius: 8px;
      background: var(--secondary-background-color);
    }

    .notification-icon {
      font-size: 1.4em;
      flex-shrink: 0;
      width: 28px;
      text-align: center;
    }

    .notification-content {
      flex: 1;
      min-width: 0;
    }

    .notification-message {
      word-break: break-word;
    }

    .notification-meta {
      display: flex;
      gap: 8px;
      margin-top: 4px;
      font-size: 0.85em;
      color: var(--secondary-text-color);
    }

    .collapsed-badge {
      background: var(--primary-color);
      color: var(--text-primary-color);
      padding: 2px 6px;
      border-radius: 10px;
      font-size: 0.75em;
      font-weight: 500;
    }

    .no-delivered {
      color: var(--secondary-text-color);
      font-style: italic;
    }

    .footer {
      margin-top: 16px;
      padding-top: 12px;
      border-top: 1px solid var(--divider-color);
      font-size: 0.9em;
      color: var(--secondary-text-color);
    }

    .safety-status {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .safety-ok {
      color: var(--success-color, #4caf50);
    }

    .safety-alert {
      color: var(--error-color, #f44336);
    }

    .loading {
      text-align: center;
      padding: 20px;
      color: var(--secondary-text-color);
    }

    .error {
      color: var(--error-color);
      padding: 16px;
      text-align: center;
    }

    .empty-state {
      text-align: center;
      padding: 32px 16px;
      color: var(--secondary-text-color);
    }

    .empty-icon {
      font-size: 3em;
      margin-bottom: 16px;
      opacity: 0.5;
    }
  `;

  setConfig(config: HushHistoryCardConfig): void {
    this._config = {
      title: "Recent Notifications",
      limit: 10,
      ...config,
    };
  }

  protected updated(changedProps: PropertyValues): void {
    super.updated(changedProps);

    if (changedProps.has("hass") && this.hass && !this._unsubscribe) {
      this._loadNotifications();
    }
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this._unsubscribe) {
      this._unsubscribe();
      this._unsubscribe = undefined;
    }
  }

  private async _loadNotifications(): Promise<void> {
    if (!this.hass) return;

    this._loading = true;
    this._error = undefined;

    try {
      // Call the hush websocket API to get notifications
      const response = await this.hass.callWS<{
        notifications: NotificationRecord[];
        stats: TodayStats;
      }>({
        type: "hush/get_notifications",
        limit: this._config?.limit ?? 10,
      });

      this._notifications = response.notifications;
      this._stats = response.stats;
    } catch (err) {
      console.error("Failed to load Hush notifications:", err);
      this._error = "Failed to load notifications";
    } finally {
      this._loading = false;
    }
  }

  private _formatTime(timestamp: string): string {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
  }

  private _getCategoryIcon(category: Category): string {
    return CATEGORY_ICONS[category] || "ℹ️";
  }

  private _getCategoryColor(category: Category): string {
    return CATEGORY_COLORS[category] || "#9e9e9e";
  }

  protected render() {
    if (!this._config) {
      return html``;
    }

    return html`
      <ha-card>
        <div class="card-header">
          <span class="card-title">${this._config.title}</span>
        </div>

        ${this._loading
          ? html`<div class="loading">Loading...</div>`
          : this._error
            ? html`<div class="error">${this._error}</div>`
            : this._renderContent()}
      </ha-card>
    `;
  }

  private _renderContent() {
    if (this._notifications.length === 0) {
      return html`
        <div class="empty-state">
          <div class="empty-icon">🔔</div>
          <div>No notifications yet</div>
        </div>
      `;
    }

    return html`
      <div class="notification-list">
        ${this._notifications.map((n) => this._renderNotification(n))}
      </div>
      ${this._renderFooter()}
    `;
  }

  private _renderNotification(notification: NotificationRecord) {
    const icon = this._getCategoryIcon(notification.category);
    const color = this._getCategoryColor(notification.category);

    return html`
      <div
        class="notification-item"
        style="border-left: 3px solid ${color}"
      >
        <span class="notification-icon">${icon}</span>
        <div class="notification-content">
          <div class="notification-message">
            ${notification.message}
            ${notification.collapsed_count > 1
              ? html`<span class="collapsed-badge"
                  >×${notification.collapsed_count}</span
                >`
              : ""}
          </div>
          <div class="notification-meta">
            <span>${this._formatTime(notification.timestamp)}</span>
            ${!notification.delivered
              ? html`<span class="no-delivered">(not delivered)</span>`
              : ""}
          </div>
        </div>
      </div>
    `;
  }

  private _renderFooter() {
    const hasSafetyAlerts = this._stats.safety_count > 0;

    return html`
      <div class="footer">
        <div class="safety-status">
          ${hasSafetyAlerts
            ? html`<span class="safety-alert"
                >⚠️ ${this._stats.safety_count} safety
                alert${this._stats.safety_count > 1 ? "s" : ""} today</span
              >`
            : html`<span class="safety-ok">✓ No safety alerts today</span>`}
        </div>
        <div>
          Today: ${this._stats.total} notification${this._stats.total !== 1
            ? "s"
            : ""}
          (${this._stats.delivered_count} delivered)
        </div>
      </div>
    `;
  }

  static getConfigElement() {
    return document.createElement("hush-history-card-editor");
  }

  static getStubConfig() {
    return {
      type: "custom:hush-history-card",
      title: "Recent Notifications",
      limit: 10,
    };
  }
}

// Card editor (minimal)
@customElement("hush-history-card-editor")
export class HushHistoryCardEditor extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;
  @state() private _config?: HushHistoryCardConfig;

  static styles = css`
    .form-row {
      margin-bottom: 16px;
    }

    label {
      display: block;
      margin-bottom: 4px;
      font-weight: 500;
    }

    input {
      width: 100%;
      padding: 8px;
      border: 1px solid var(--divider-color);
      border-radius: 4px;
      background: var(--card-background-color);
      color: var(--primary-text-color);
    }
  `;

  setConfig(config: HushHistoryCardConfig): void {
    this._config = config;
  }

  protected render() {
    if (!this._config) {
      return html``;
    }

    return html`
      <div class="form-row">
        <label>Title</label>
        <input
          type="text"
          .value=${this._config.title || ""}
          @input=${this._onTitleChange}
        />
      </div>
      <div class="form-row">
        <label>Limit</label>
        <input
          type="number"
          min="1"
          max="50"
          .value=${String(this._config.limit || 10)}
          @input=${this._onLimitChange}
        />
      </div>
    `;
  }

  private _onTitleChange(ev: Event): void {
    const target = ev.target as HTMLInputElement;
    this._updateConfig({ title: target.value });
  }

  private _onLimitChange(ev: Event): void {
    const target = ev.target as HTMLInputElement;
    this._updateConfig({ limit: parseInt(target.value, 10) || 10 });
  }

  private _updateConfig(update: Partial<HushHistoryCardConfig>): void {
    this._config = { ...this._config!, ...update };
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      })
    );
  }
}

// Register with Home Assistant
declare global {
  interface HTMLElementTagNameMap {
    "hush-history-card": HushHistoryCard;
    "hush-history-card-editor": HushHistoryCardEditor;
  }
}

// Register card with HA
(window as unknown as { customCards?: unknown[] }).customCards =
  (window as unknown as { customCards?: unknown[] }).customCards || [];
(window as unknown as { customCards: unknown[] }).customCards.push({
  type: "hush-history-card",
  name: "Hush History Card",
  description: "Display recent smart notifications from Hush",
  preview: true,
});
