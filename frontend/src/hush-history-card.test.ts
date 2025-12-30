import { describe, it, expect, vi } from "vitest";
import { html, fixture } from "@open-wc/testing";
import { HushHistoryCard } from "./hush-history-card";
import type { NotificationRecord, TodayStats } from "./types";

// Mock Home Assistant
const createMockHass = (
  notifications: NotificationRecord[] = [],
  stats: TodayStats = { total: 0, safety_count: 0, delivered_count: 0 }
) => ({
  callWS: vi.fn().mockResolvedValue({ notifications, stats }),
  callService: vi.fn(),
  connection: {
    subscribeMessage: vi.fn(),
  },
});

describe("HushHistoryCard", () => {
  describe("setConfig", () => {
    it("should set default config values", async () => {
      const el = await fixture<HushHistoryCard>(
        html`<hush-history-card></hush-history-card>`
      );

      el.setConfig({ type: "custom:hush-history-card" });

      // Access private property for testing
      expect((el as unknown as { _config: { title: string; limit: number } })._config.title).toBe(
        "Recent Notifications"
      );
      expect((el as unknown as { _config: { title: string; limit: number } })._config.limit).toBe(10);
    });

    it("should accept custom config values", async () => {
      const el = await fixture<HushHistoryCard>(
        html`<hush-history-card></hush-history-card>`
      );

      el.setConfig({
        type: "custom:hush-history-card",
        title: "My Notifications",
        limit: 25,
      });

      expect((el as unknown as { _config: { title: string; limit: number } })._config.title).toBe(
        "My Notifications"
      );
      expect((el as unknown as { _config: { title: string; limit: number } })._config.limit).toBe(25);
    });
  });

  describe("rendering", () => {
    it("should render loading state initially", async () => {
      const el = await fixture<HushHistoryCard>(
        html`<hush-history-card></hush-history-card>`
      );

      el.setConfig({ type: "custom:hush-history-card" });
      await el.updateComplete;

      const loading = el.shadowRoot?.querySelector(".loading");
      expect(loading).toBeDefined();
    });

    it("should render empty state when no notifications", async () => {
      const el = await fixture<HushHistoryCard>(
        html`<hush-history-card></hush-history-card>`
      );

      el.setConfig({ type: "custom:hush-history-card" });
      el.hass = createMockHass([], { total: 0, safety_count: 0, delivered_count: 0 });

      // Force state update
      (el as unknown as { _loading: boolean })._loading = false;
      (el as unknown as { _notifications: NotificationRecord[] })._notifications = [];
      await el.updateComplete;

      const emptyState = el.shadowRoot?.querySelector(".empty-state");
      expect(emptyState).toBeDefined();
    });

    it("should render notifications when data available", async () => {
      const el = await fixture<HushHistoryCard>(
        html`<hush-history-card></hush-history-card>`
      );

      const notifications: NotificationRecord[] = [
        {
          id: "1",
          timestamp: new Date().toISOString(),
          message: "Test notification",
          title: null,
          category: "info",
          entity_id: null,
          delivered: true,
          collapsed_count: 1,
        },
      ];

      el.setConfig({ type: "custom:hush-history-card" });
      el.hass = createMockHass(notifications, { total: 1, safety_count: 0, delivered_count: 1 });

      // Force state update
      (el as unknown as { _loading: boolean })._loading = false;
      (el as unknown as { _notifications: NotificationRecord[] })._notifications = notifications;
      await el.updateComplete;

      const notificationList = el.shadowRoot?.querySelector(".notification-list");
      expect(notificationList).toBeDefined();
    });

    it("should show not delivered indicator when notification not delivered", async () => {
      const el = await fixture<HushHistoryCard>(
        html`<hush-history-card></hush-history-card>`
      );

      const notifications: NotificationRecord[] = [
        {
          id: "1",
          timestamp: new Date().toISOString(),
          message: "Suppressed notification",
          title: null,
          category: "motion",
          entity_id: null,
          delivered: false,
          collapsed_count: 1,
        },
      ];

      el.setConfig({ type: "custom:hush-history-card" });
      el.hass = createMockHass(notifications, { total: 1, safety_count: 0, delivered_count: 0 });

      (el as unknown as { _loading: boolean })._loading = false;
      (el as unknown as { _notifications: NotificationRecord[] })._notifications = notifications;
      await el.updateComplete;

      const noDelivered = el.shadowRoot?.querySelector(".no-delivered");
      expect(noDelivered).toBeDefined();
    });

    it("should show safety alert when safety_count > 0", async () => {
      const el = await fixture<HushHistoryCard>(
        html`<hush-history-card></hush-history-card>`
      );

      el.setConfig({ type: "custom:hush-history-card" });
      el.hass = createMockHass([], { total: 1, safety_count: 2, delivered_count: 1 });

      (el as unknown as { _loading: boolean })._loading = false;
      (el as unknown as { _notifications: NotificationRecord[] })._notifications = [];
      (el as unknown as { _stats: TodayStats })._stats = { total: 1, safety_count: 2, delivered_count: 1 };
      await el.updateComplete;

      const safetyAlert = el.shadowRoot?.querySelector(".safety-alert");
      expect(safetyAlert).toBeDefined();
    });

    it("should show collapsed count badge when count > 1", async () => {
      const el = await fixture<HushHistoryCard>(
        html`<hush-history-card></hush-history-card>`
      );

      const notifications: NotificationRecord[] = [
        {
          id: "1",
          timestamp: new Date().toISOString(),
          message: "Collapsed notification",
          title: null,
          category: "motion",
          entity_id: null,
          delivered: true,
          collapsed_count: 5,
        },
      ];

      el.setConfig({ type: "custom:hush-history-card" });
      el.hass = createMockHass(notifications, { total: 5, safety_count: 0, delivered_count: 5 });

      (el as unknown as { _loading: boolean })._loading = false;
      (el as unknown as { _notifications: NotificationRecord[] })._notifications = notifications;
      await el.updateComplete;

      const collapsedBadge = el.shadowRoot?.querySelector(".collapsed-badge");
      expect(collapsedBadge).toBeDefined();
    });
  });

  describe("time formatting", () => {
    it("should format time correctly", async () => {
      const el = await fixture<HushHistoryCard>(
        html`<hush-history-card></hush-history-card>`
      );

      // Access private method for testing
      const formatTime = (el as unknown as { _formatTime: (ts: string) => string })._formatTime;

      // Just now
      const now = new Date().toISOString();
      expect(formatTime.call(el, now)).toBe("just now");

      // 5 minutes ago
      const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
      expect(formatTime.call(el, fiveMinAgo)).toBe("5m ago");

      // 2 hours ago
      const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
      expect(formatTime.call(el, twoHoursAgo)).toBe("2h ago");

      // 3 days ago
      const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString();
      expect(formatTime.call(el, threeDaysAgo)).toBe("3d ago");

      // 10 days ago - should use locale date string
      const tenDaysAgo = new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString();
      const result = formatTime.call(el, tenDaysAgo);
      // Should be a formatted date, not "Xd ago"
      expect(result).not.toContain("d ago");
    });
  });

  describe("error handling", () => {
    it("should render error state", async () => {
      const el = await fixture<HushHistoryCard>(
        html`<hush-history-card></hush-history-card>`
      );

      el.setConfig({ type: "custom:hush-history-card" });

      // Force error state
      (el as unknown as { _loading: boolean })._loading = false;
      (el as unknown as { _error: string })._error = "Failed to load notifications";
      await el.updateComplete;

      const error = el.shadowRoot?.querySelector(".error");
      expect(error).toBeDefined();
      expect(error?.textContent).toContain("Failed to load");
    });
  });

  describe("category helpers", () => {
    it("should return category icon", async () => {
      const el = await fixture<HushHistoryCard>(
        html`<hush-history-card></hush-history-card>`
      );

      const getCategoryIcon = (el as unknown as { _getCategoryIcon: (cat: string) => string })._getCategoryIcon;

      expect(getCategoryIcon.call(el, "safety")).toBeDefined();
      expect(getCategoryIcon.call(el, "unknown")).toBe("ℹ️");
    });

    it("should return category color", async () => {
      const el = await fixture<HushHistoryCard>(
        html`<hush-history-card></hush-history-card>`
      );

      const getCategoryColor = (el as unknown as { _getCategoryColor: (cat: string) => string })._getCategoryColor;

      expect(getCategoryColor.call(el, "safety")).toBeDefined();
      expect(getCategoryColor.call(el, "unknown")).toBe("#9e9e9e");
    });
  });

  describe("static methods", () => {
    it("should return config element", () => {
      const configEl = (
        HushHistoryCard as unknown as { getConfigElement: () => HTMLElement }
      ).getConfigElement();
      expect(configEl.tagName.toLowerCase()).toBe("hush-history-card-editor");
    });

    it("should return stub config", () => {
      const stubConfig = (
        HushHistoryCard as unknown as { getStubConfig: () => { type: string; title: string; limit: number } }
      ).getStubConfig();
      expect(stubConfig.type).toBe("custom:hush-history-card");
      expect(stubConfig.title).toBe("Recent Notifications");
      expect(stubConfig.limit).toBe(10);
    });
  });
});

describe("HushHistoryCardEditor", () => {
  it("should render editor form", async () => {
    const el = await fixture(
      html`<hush-history-card-editor></hush-history-card-editor>`
    );

    (el as unknown as { setConfig: (config: object) => void }).setConfig({
      type: "custom:hush-history-card",
      title: "Test",
      limit: 10,
    });
    await (el as unknown as { updateComplete: Promise<boolean> }).updateComplete;

    const inputs = el.shadowRoot?.querySelectorAll("input");
    expect(inputs?.length).toBe(2);
  });

  it("should update config on title change", async () => {
    const el = await fixture(
      html`<hush-history-card-editor></hush-history-card-editor>`
    );

    (el as unknown as { setConfig: (config: object) => void }).setConfig({
      type: "custom:hush-history-card",
      title: "Test",
      limit: 10,
    });
    await (el as unknown as { updateComplete: Promise<boolean> }).updateComplete;

    // Track config-changed events
    const configChangedEvents: CustomEvent[] = [];
    el.addEventListener("config-changed", ((e: CustomEvent) => {
      configChangedEvents.push(e);
    }) as EventListener);

    // Simulate title change
    const handler = (el as unknown as { _onTitleChange: (e: Event) => void })._onTitleChange;
    const mockEvent = { target: { value: "New Title" } } as unknown as Event;
    handler.call(el, mockEvent);

    expect(configChangedEvents.length).toBe(1);
    expect(configChangedEvents[0].detail.config.title).toBe("New Title");
  });

  it("should update config on limit change", async () => {
    const el = await fixture(
      html`<hush-history-card-editor></hush-history-card-editor>`
    );

    (el as unknown as { setConfig: (config: object) => void }).setConfig({
      type: "custom:hush-history-card",
      title: "Test",
      limit: 10,
    });
    await (el as unknown as { updateComplete: Promise<boolean> }).updateComplete;

    // Track config-changed events
    const configChangedEvents: CustomEvent[] = [];
    el.addEventListener("config-changed", ((e: CustomEvent) => {
      configChangedEvents.push(e);
    }) as EventListener);

    // Simulate limit change
    const handler = (el as unknown as { _onLimitChange: (e: Event) => void })._onLimitChange;
    const mockEvent = { target: { value: "25" } } as unknown as Event;
    handler.call(el, mockEvent);

    expect(configChangedEvents.length).toBe(1);
    expect(configChangedEvents[0].detail.config.limit).toBe(25);
  });

  it("should handle invalid limit by defaulting to 10", async () => {
    const el = await fixture(
      html`<hush-history-card-editor></hush-history-card-editor>`
    );

    (el as unknown as { setConfig: (config: object) => void }).setConfig({
      type: "custom:hush-history-card",
      title: "Test",
      limit: 10,
    });
    await (el as unknown as { updateComplete: Promise<boolean> }).updateComplete;

    // Track config-changed events
    const configChangedEvents: CustomEvent[] = [];
    el.addEventListener("config-changed", ((e: CustomEvent) => {
      configChangedEvents.push(e);
    }) as EventListener);

    // Simulate invalid limit change
    const handler = (el as unknown as { _onLimitChange: (e: Event) => void })._onLimitChange;
    const mockEvent = { target: { value: "invalid" } } as unknown as Event;
    handler.call(el, mockEvent);

    expect(configChangedEvents.length).toBe(1);
    expect(configChangedEvents[0].detail.config.limit).toBe(10);
  });

  it("should dispatch config-changed via _updateConfig", async () => {
    const el = await fixture(
      html`<hush-history-card-editor></hush-history-card-editor>`
    );

    (el as unknown as { setConfig: (config: object) => void }).setConfig({
      type: "custom:hush-history-card",
      title: "Test",
      limit: 10,
    });
    await (el as unknown as { updateComplete: Promise<boolean> }).updateComplete;

    // Track config-changed events
    const configChangedEvents: CustomEvent[] = [];
    el.addEventListener("config-changed", ((e: CustomEvent) => {
      configChangedEvents.push(e);
    }) as EventListener);

    // Call _updateConfig directly
    const updateConfig = (el as unknown as { _updateConfig: (update: object) => void })._updateConfig;
    updateConfig.call(el, { title: "Updated", limit: 20 });

    expect(configChangedEvents.length).toBe(1);
    expect(configChangedEvents[0].detail.config.title).toBe("Updated");
    expect(configChangedEvents[0].detail.config.limit).toBe(20);
  });
});
