import { describe, it, expect } from "vitest";
import {
  CATEGORY_ICONS,
  CATEGORY_COLORS,
  CATEGORY_NAMES,
  type Category,
  type CategoryBehavior,
  type NotificationRecord,
  type TodayStats,
  type HushConfig,
} from "./types";

describe("types", () => {
  describe("CATEGORY_ICONS", () => {
    it("should have icons for all categories", () => {
      const categories: Category[] = [
        "safety",
        "security",
        "device",
        "motion",
        "info",
      ];

      categories.forEach((cat) => {
        expect(CATEGORY_ICONS[cat]).toBeDefined();
        expect(typeof CATEGORY_ICONS[cat]).toBe("string");
        expect(CATEGORY_ICONS[cat].length).toBeGreaterThan(0);
      });
    });

    it("should have correct icons", () => {
      expect(CATEGORY_ICONS.safety).toBe("🚨");
      expect(CATEGORY_ICONS.security).toBe("🚪");
      expect(CATEGORY_ICONS.device).toBe("📱");
      expect(CATEGORY_ICONS.motion).toBe("👤");
      expect(CATEGORY_ICONS.info).toBe("ℹ️");
    });
  });

  describe("CATEGORY_COLORS", () => {
    it("should have colors for all categories", () => {
      const categories: Category[] = [
        "safety",
        "security",
        "device",
        "motion",
        "info",
      ];

      categories.forEach((cat) => {
        expect(CATEGORY_COLORS[cat]).toBeDefined();
        expect(CATEGORY_COLORS[cat]).toMatch(/^#[0-9a-fA-F]{6}$/);
      });
    });

    it("should have safety as red", () => {
      expect(CATEGORY_COLORS.safety).toBe("#f44336");
    });
  });

  describe("CATEGORY_NAMES", () => {
    it("should have names for all categories", () => {
      const categories: Category[] = [
        "safety",
        "security",
        "device",
        "motion",
        "info",
      ];

      categories.forEach((cat) => {
        expect(CATEGORY_NAMES[cat]).toBeDefined();
        expect(typeof CATEGORY_NAMES[cat]).toBe("string");
      });
    });

    it("should have correct names", () => {
      expect(CATEGORY_NAMES.safety).toBe("Safety");
      expect(CATEGORY_NAMES.security).toBe("Security");
      expect(CATEGORY_NAMES.device).toBe("Device");
      expect(CATEGORY_NAMES.motion).toBe("Motion");
      expect(CATEGORY_NAMES.info).toBe("Other");
    });
  });
});

describe("type definitions", () => {
  it("NotificationRecord should have correct shape", () => {
    const record: NotificationRecord = {
      id: "test-id",
      timestamp: "2024-01-01T00:00:00Z",
      message: "Test message",
      title: "Test title",
      category: "safety",
      entity_id: "binary_sensor.smoke",
      delivered: true,
      collapsed_count: 1,
    };

    expect(record.id).toBe("test-id");
    expect(record.message).toBe("Test message");
    expect(record.category).toBe("safety");
  });

  it("NotificationRecord can have null title and entity_id", () => {
    const record: NotificationRecord = {
      id: "test-id",
      timestamp: "2024-01-01T00:00:00Z",
      message: "Test message",
      title: null,
      category: "info",
      entity_id: null,
      delivered: false,
      collapsed_count: 3,
    };

    expect(record.title).toBeNull();
    expect(record.entity_id).toBeNull();
  });

  it("TodayStats should have correct shape", () => {
    const stats: TodayStats = {
      total: 10,
      safety_count: 1,
      delivered_count: 8,
    };

    expect(stats.total).toBe(10);
    expect(stats.safety_count).toBe(1);
    expect(stats.delivered_count).toBe(8);
  });

  it("HushConfig should have correct shape", () => {
    const config: HushConfig = {
      delivery_target: "notify.mobile_app_test",
      quiet_hours_enabled: true,
      quiet_hours_start: "22:00",
      quiet_hours_end: "07:00",
      category_behaviors: {
        safety: "always_notify",
        security: "notify_respect_quiet",
        device: "notify_once_per_hour",
        motion: "log_only",
        info: "notify_with_dedup",
      },
    };

    expect(config.delivery_target).toBe("notify.mobile_app_test");
    expect(config.quiet_hours_enabled).toBe(true);
    expect(config.category_behaviors.safety).toBe("always_notify");
  });

  it("CategoryBehavior should accept valid values", () => {
    const behaviors: CategoryBehavior[] = [
      "always_notify",
      "notify_respect_quiet",
      "notify_once_per_hour",
      "log_only",
      "notify_with_dedup",
    ];

    behaviors.forEach((behavior) => {
      expect(typeof behavior).toBe("string");
    });
  });
});
