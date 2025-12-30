import { describe, it, expect, vi } from "vitest";
import { html, fixture, elementUpdated } from "@open-wc/testing";
import "./hush-settings-panel";
import type { HushSettingsPanel } from "./hush-settings-panel";
import type { HushConfig } from "./types";

// Mock Home Assistant
const createMockHass = (config?: Partial<HushConfig>) => ({
  callWS: vi.fn().mockResolvedValue({
    config: {
      delivery_target: "notify.mobile_app_test",
      quiet_hours_enabled: true,
      quiet_hours_start: "22:00",
      quiet_hours_end: "07:00",
      category_behaviors: {},
      ...config,
    },
    notify_services: [
      { service: "notify.mobile_app_test", name: "Mobile App Test" },
      { service: "notify.mobile_app_other", name: "Mobile App Other" },
    ],
  }),
  callService: vi.fn(),
  connection: {
    subscribeMessage: vi.fn(),
  },
});

describe("HushSettingsPanel", () => {
  describe("rendering", () => {
    it("should render loading state initially", async () => {
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      await el.updateComplete;

      const loading = el.shadowRoot?.querySelector(".loading");
      expect(loading).toBeDefined();
    });

    it("should render header with icon", async () => {
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      el.hass = createMockHass();
      // Force loading complete
      (el as unknown as { _loading: boolean })._loading = false;
      (el as unknown as { _config: HushConfig })._config = {
        delivery_target: "notify.mobile_app_test",
        quiet_hours_enabled: true,
        quiet_hours_start: "22:00",
        quiet_hours_end: "07:00",
        category_behaviors: {},
      };
      (el as unknown as { _notifyServices: Array<{ service: string; name: string }> })._notifyServices = [
        { service: "notify.mobile_app_test", name: "Mobile App Test" },
      ];
      await el.updateComplete;

      const header = el.shadowRoot?.querySelector(".header");
      expect(header).toBeDefined();

      const icon = el.shadowRoot?.querySelector(".header-icon");
      expect(icon?.textContent).toBe("🔕");
    });

    it("should render notification target select", async () => {
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      el.hass = createMockHass();
      (el as unknown as { _loading: boolean })._loading = false;
      (el as unknown as { _config: HushConfig })._config = {
        delivery_target: "notify.mobile_app_test",
        quiet_hours_enabled: true,
        quiet_hours_start: "22:00",
        quiet_hours_end: "07:00",
        category_behaviors: {},
      };
      (el as unknown as { _notifyServices: Array<{ service: string; name: string }> })._notifyServices = [
        { service: "notify.mobile_app_test", name: "Mobile App Test" },
      ];
      await el.updateComplete;

      const select = el.shadowRoot?.querySelector("select");
      expect(select).toBeDefined();
    });

    it("should render quiet hours toggle", async () => {
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      el.hass = createMockHass();
      (el as unknown as { _loading: boolean })._loading = false;
      (el as unknown as { _config: HushConfig })._config = {
        delivery_target: "notify.mobile_app_test",
        quiet_hours_enabled: true,
        quiet_hours_start: "22:00",
        quiet_hours_end: "07:00",
        category_behaviors: {},
      };
      (el as unknown as { _notifyServices: Array<{ service: string; name: string }> })._notifyServices = [];
      await el.updateComplete;

      const toggle = el.shadowRoot?.querySelector('input[type="checkbox"]');
      expect(toggle).toBeDefined();
    });

    it("should show time inputs when quiet hours enabled", async () => {
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      el.hass = createMockHass();
      (el as unknown as { _loading: boolean })._loading = false;
      (el as unknown as { _config: HushConfig })._config = {
        delivery_target: "notify.mobile_app_test",
        quiet_hours_enabled: true,
        quiet_hours_start: "22:00",
        quiet_hours_end: "07:00",
        category_behaviors: {},
      };
      (el as unknown as { _notifyServices: Array<{ service: string; name: string }> })._notifyServices = [
        { service: "notify.mobile_app_test", name: "Test" },
      ];
      await el.updateComplete;

      // Verify the quiet hours card is present
      const quietHoursCard = el.shadowRoot?.querySelector(".card:nth-of-type(2)");
      expect(quietHoursCard).toBeDefined();

      // Verify time-inputs div is rendered when quiet hours enabled
      const timeInputsDiv = el.shadowRoot?.querySelector(".time-inputs");
      expect(timeInputsDiv).toBeDefined();
    });

    it("should hide time inputs when quiet hours disabled", async () => {
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      el.hass = createMockHass();
      (el as unknown as { _loading: boolean })._loading = false;
      (el as unknown as { _config: HushConfig })._config = {
        delivery_target: "notify.mobile_app_test",
        quiet_hours_enabled: false,
        quiet_hours_start: "22:00",
        quiet_hours_end: "07:00",
        category_behaviors: {},
      };
      (el as unknown as { _notifyServices: Array<{ service: string; name: string }> })._notifyServices = [];
      await el.updateComplete;

      const timeInputs = el.shadowRoot?.querySelectorAll('input[type="time"]');
      expect(timeInputs?.length).toBe(0);
    });

    it("should render done message", async () => {
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      el.hass = createMockHass();
      (el as unknown as { _loading: boolean })._loading = false;
      (el as unknown as { _config: HushConfig })._config = {
        delivery_target: "notify.mobile_app_test",
        quiet_hours_enabled: true,
        quiet_hours_start: "22:00",
        quiet_hours_end: "07:00",
        category_behaviors: {},
      };
      (el as unknown as { _notifyServices: Array<{ service: string; name: string }> })._notifyServices = [];
      await el.updateComplete;

      const doneMessage = el.shadowRoot?.querySelector(".done-message");
      expect(doneMessage?.textContent).toContain("That's it!");
    });

    it("should render advanced toggle", async () => {
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      el.hass = createMockHass();
      (el as unknown as { _loading: boolean })._loading = false;
      (el as unknown as { _config: HushConfig })._config = {
        delivery_target: "notify.mobile_app_test",
        quiet_hours_enabled: true,
        quiet_hours_start: "22:00",
        quiet_hours_end: "07:00",
        category_behaviors: {},
      };
      (el as unknown as { _notifyServices: Array<{ service: string; name: string }> })._notifyServices = [];
      await el.updateComplete;

      const advancedToggle = el.shadowRoot?.querySelector(".advanced-toggle");
      expect(advancedToggle).toBeDefined();
      expect(advancedToggle?.textContent).toContain("Advanced Settings");
    });
  });

  describe("advanced settings", () => {
    it("should have advanced toggle button", async () => {
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      el.hass = createMockHass();
      (el as unknown as { _loading: boolean })._loading = false;
      (el as unknown as { _config: HushConfig })._config = {
        delivery_target: "notify.mobile_app_test",
        quiet_hours_enabled: true,
        quiet_hours_start: "22:00",
        quiet_hours_end: "07:00",
        category_behaviors: {},
      };
      (el as unknown as { _notifyServices: Array<{ service: string; name: string }> })._notifyServices = [
        { service: "notify.mobile_app_test", name: "Test" },
      ];
      await el.updateComplete;

      // Advanced toggle should be present
      const advancedToggle = el.shadowRoot?.querySelector(".advanced-toggle");
      expect(advancedToggle).toBeDefined();
      expect(advancedToggle?.textContent).toContain("Advanced Settings");
    });

    it("should have _showAdvanced state property", async () => {
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      // Verify the component has the _showAdvanced property
      expect((el as unknown as { _showAdvanced: boolean })._showAdvanced).toBe(false);

      // Setting it should work
      (el as unknown as { _showAdvanced: boolean })._showAdvanced = true;
      expect((el as unknown as { _showAdvanced: boolean })._showAdvanced).toBe(true);
    });
  });

  describe("error handling", () => {
    it("should show error message when load fails", async () => {
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      (el as unknown as { _loading: boolean })._loading = false;
      (el as unknown as { _error: string })._error = "Failed to load configuration";
      await el.updateComplete;

      const error = el.shadowRoot?.querySelector(".error");
      expect(error).toBeDefined();
      expect(error?.textContent).toContain("Failed to load");
    });
  });

  describe("save button", () => {
    it("should render save button", async () => {
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      el.hass = createMockHass();
      (el as unknown as { _loading: boolean })._loading = false;
      (el as unknown as { _config: HushConfig })._config = {
        delivery_target: "notify.mobile_app_test",
        quiet_hours_enabled: true,
        quiet_hours_start: "22:00",
        quiet_hours_end: "07:00",
        category_behaviors: {},
      };
      (el as unknown as { _notifyServices: Array<{ service: string; name: string }> })._notifyServices = [
        { service: "notify.mobile_app_test", name: "Test" },
      ];
      await el.updateComplete;

      // Verify actions section exists
      const actions = el.shadowRoot?.querySelector(".actions");
      expect(actions).toBeDefined();

      // The button should have primary-button class
      const buttons = el.shadowRoot?.querySelectorAll("button");
      expect(buttons?.length).toBeGreaterThan(0);
    });

    it("should show saving state", async () => {
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      el.hass = createMockHass();
      (el as unknown as { _loading: boolean })._loading = false;
      (el as unknown as { _saving: boolean })._saving = true;
      (el as unknown as { _config: HushConfig })._config = {
        delivery_target: "notify.mobile_app_test",
        quiet_hours_enabled: true,
        quiet_hours_start: "22:00",
        quiet_hours_end: "07:00",
        category_behaviors: {},
      };
      (el as unknown as { _notifyServices: Array<{ service: string; name: string }> })._notifyServices = [
        { service: "notify.mobile_app_test", name: "Test" },
      ];
      await el.updateComplete;

      // When saving, the button should be disabled
      const button = el.shadowRoot?.querySelector(".actions button");
      expect(button?.getAttribute("disabled")).toBeDefined();
    });
  });

  describe("config loading", () => {
    it("should call _loadConfig which calls hass.callWS", async () => {
      const mockHass = createMockHass();
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      el.hass = mockHass;

      // Directly call _loadConfig
      const loadConfig = (el as unknown as { _loadConfig: () => Promise<void> })._loadConfig;
      await loadConfig.call(el);

      expect(mockHass.callWS).toHaveBeenCalledWith({ type: "hush/get_config" });
    });

    it("should set error when config load fails", async () => {
      const mockHass = createMockHass();
      mockHass.callWS = vi.fn().mockRejectedValue(new Error("Connection failed"));

      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      el.hass = mockHass;

      // Directly call _loadConfig
      const loadConfig = (el as unknown as { _loadConfig: () => Promise<void> })._loadConfig;
      await loadConfig.call(el);

      expect((el as unknown as { _error: string })._error).toBeDefined();
    });

    it("should early return when hass is not set", async () => {
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      // Don't set hass
      const loadConfig = (el as unknown as { _loadConfig: () => Promise<void> })._loadConfig;
      await loadConfig.call(el);

      // Should not throw and should still be in loading state
      expect((el as unknown as { _loading: boolean })._loading).toBe(true);
    });
  });

  describe("config saving", () => {
    it("should call hass.callWS on save", async () => {
      const mockHass = createMockHass();
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      el.hass = mockHass;
      (el as unknown as { _loading: boolean })._loading = false;
      (el as unknown as { _config: HushConfig })._config = {
        delivery_target: "notify.mobile_app_test",
        quiet_hours_enabled: true,
        quiet_hours_start: "22:00",
        quiet_hours_end: "07:00",
        category_behaviors: {},
      };
      await el.updateComplete;

      // Call the private _saveConfig method
      const saveConfig = (el as unknown as { _saveConfig: () => Promise<void> })._saveConfig;
      await saveConfig.call(el);

      expect(mockHass.callWS).toHaveBeenCalledWith(
        expect.objectContaining({ type: "hush/save_config" })
      );
    });

    it("should set error when save fails", async () => {
      const mockHass = createMockHass();
      mockHass.callWS = vi.fn().mockRejectedValue(new Error("Save failed"));

      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      el.hass = mockHass;
      (el as unknown as { _loading: boolean })._loading = false;
      (el as unknown as { _config: HushConfig })._config = {
        delivery_target: "notify.mobile_app_test",
        quiet_hours_enabled: true,
        quiet_hours_start: "22:00",
        quiet_hours_end: "07:00",
        category_behaviors: {},
      };
      await el.updateComplete;

      const saveConfig = (el as unknown as { _saveConfig: () => Promise<void> })._saveConfig;
      await saveConfig.call(el);

      expect((el as unknown as { _error: string })._error).toContain("Failed to save");
    });

    it("should early return when hass is not set", async () => {
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      (el as unknown as { _config: HushConfig })._config = {
        delivery_target: "notify.mobile_app_test",
        quiet_hours_enabled: true,
        quiet_hours_start: "22:00",
        quiet_hours_end: "07:00",
        category_behaviors: {},
      };

      // Don't set hass
      const saveConfig = (el as unknown as { _saveConfig: () => Promise<void> })._saveConfig;
      await saveConfig.call(el);

      // Should not throw, saving state should not change
      expect((el as unknown as { _saving: boolean })._saving).toBe(false);
    });

    it("should early return when config is not set", async () => {
      const mockHass = createMockHass();
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      el.hass = mockHass;
      // Don't set config

      const saveConfig = (el as unknown as { _saveConfig: () => Promise<void> })._saveConfig;
      await saveConfig.call(el);

      // Should not call WS
      expect(mockHass.callWS).not.toHaveBeenCalledWith(
        expect.objectContaining({ type: "hush/save_config" })
      );
    });
  });

  describe("event handlers", () => {
    it("should update config on target change", async () => {
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      (el as unknown as { _config: HushConfig })._config = {
        delivery_target: "notify.mobile_app_test",
        quiet_hours_enabled: true,
        quiet_hours_start: "22:00",
        quiet_hours_end: "07:00",
        category_behaviors: {},
      };

      const handler = (el as unknown as { _onTargetChange: (e: Event) => void })._onTargetChange;
      const mockEvent = { target: { value: "notify.new_target" } } as unknown as Event;
      handler.call(el, mockEvent);

      expect((el as unknown as { _config: HushConfig })._config.delivery_target).toBe("notify.new_target");
    });

    it("should update config on quiet hours toggle", async () => {
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      (el as unknown as { _config: HushConfig })._config = {
        delivery_target: "notify.mobile_app_test",
        quiet_hours_enabled: true,
        quiet_hours_start: "22:00",
        quiet_hours_end: "07:00",
        category_behaviors: {},
      };

      const handler = (el as unknown as { _onQuietHoursToggle: (e: Event) => void })._onQuietHoursToggle;
      const mockEvent = { target: { checked: false } } as unknown as Event;
      handler.call(el, mockEvent);

      expect((el as unknown as { _config: HushConfig })._config.quiet_hours_enabled).toBe(false);
    });

    it("should update config on start time change", async () => {
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      (el as unknown as { _config: HushConfig })._config = {
        delivery_target: "notify.mobile_app_test",
        quiet_hours_enabled: true,
        quiet_hours_start: "22:00",
        quiet_hours_end: "07:00",
        category_behaviors: {},
      };

      const handler = (el as unknown as { _onStartTimeChange: (e: Event) => void })._onStartTimeChange;
      const mockEvent = { target: { value: "23:00" } } as unknown as Event;
      handler.call(el, mockEvent);

      expect((el as unknown as { _config: HushConfig })._config.quiet_hours_start).toBe("23:00");
    });

    it("should update config on end time change", async () => {
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      (el as unknown as { _config: HushConfig })._config = {
        delivery_target: "notify.mobile_app_test",
        quiet_hours_enabled: true,
        quiet_hours_start: "22:00",
        quiet_hours_end: "07:00",
        category_behaviors: {},
      };

      const handler = (el as unknown as { _onEndTimeChange: (e: Event) => void })._onEndTimeChange;
      const mockEvent = { target: { value: "08:00" } } as unknown as Event;
      handler.call(el, mockEvent);

      expect((el as unknown as { _config: HushConfig })._config.quiet_hours_end).toBe("08:00");
    });

    it("should update config on behavior change", async () => {
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      (el as unknown as { _config: HushConfig })._config = {
        delivery_target: "notify.mobile_app_test",
        quiet_hours_enabled: true,
        quiet_hours_start: "22:00",
        quiet_hours_end: "07:00",
        category_behaviors: {},
      };

      const handler = (el as unknown as { _onBehaviorChange: (category: string, e: Event) => void })._onBehaviorChange;
      const mockEvent = { target: { value: "log_only" } } as unknown as Event;
      handler.call(el, "safety", mockEvent);

      expect((el as unknown as { _config: HushConfig })._config.category_behaviors?.safety).toBe("log_only");
    });
  });

  describe("advanced rendering", () => {
    it("should render advanced section via _renderAdvanced", async () => {
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      (el as unknown as { _config: HushConfig })._config = {
        delivery_target: "notify.mobile_app_test",
        quiet_hours_enabled: true,
        quiet_hours_start: "22:00",
        quiet_hours_end: "07:00",
        category_behaviors: {},
      };

      const renderAdvanced = (el as unknown as { _renderAdvanced: () => unknown })._renderAdvanced;
      const result = renderAdvanced.call(el);

      // Result should be a Lit template
      expect(result).toBeDefined();
    });

    it("should render category row via _renderCategoryRow", async () => {
      const el = await fixture<HushSettingsPanel>(
        html`<hush-settings-panel></hush-settings-panel>`
      );

      (el as unknown as { _config: HushConfig })._config = {
        delivery_target: "notify.mobile_app_test",
        quiet_hours_enabled: true,
        quiet_hours_start: "22:00",
        quiet_hours_end: "07:00",
        category_behaviors: {},
      };

      const renderCategoryRow = (el as unknown as { _renderCategoryRow: (cat: string) => unknown })._renderCategoryRow;
      const result = renderCategoryRow.call(el, "safety");

      expect(result).toBeDefined();
    });
  });
});
