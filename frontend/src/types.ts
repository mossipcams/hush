/**
 * Shared types for Hush frontend components.
 */

export interface NotificationRecord {
  id: string;
  timestamp: string;
  message: string;
  title: string | null;
  category: Category;
  entity_id: string | null;
  delivered: boolean;
  collapsed_count: number;
}

export type Category = "safety" | "security" | "device" | "motion" | "info";

export interface TodayStats {
  total: number;
  safety_count: number;
  delivered_count: number;
}

export interface HushConfig {
  delivery_target: string;
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
  category_behaviors: Partial<Record<Category, CategoryBehavior>>;
}

export type CategoryBehavior =
  | "always_notify"
  | "notify_respect_quiet"
  | "notify_once_per_hour"
  | "log_only"
  | "notify_with_dedup";

export const CATEGORY_ICONS: Record<Category, string> = {
  safety: "🚨",
  security: "🚪",
  device: "📱",
  motion: "👤",
  info: "ℹ️",
};

export const CATEGORY_COLORS: Record<Category, string> = {
  safety: "#f44336",
  security: "#ff9800",
  device: "#2196f3",
  motion: "#9e9e9e",
  info: "#4caf50",
};

export const CATEGORY_NAMES: Record<Category, string> = {
  safety: "Safety",
  security: "Security",
  device: "Device",
  motion: "Motion",
  info: "Other",
};

// Home Assistant types (minimal subset)
export interface HomeAssistant {
  callWS<T>(msg: { type: string; [key: string]: unknown }): Promise<T>;
  callService(
    domain: string,
    service: string,
    data?: Record<string, unknown>
  ): Promise<void>;
  connection: {
    subscribeMessage<T>(
      callback: (msg: T) => void,
      subscribeMessage: { type: string; [key: string]: unknown }
    ): Promise<() => void>;
  };
}

export interface LovelaceCardConfig {
  type: string;
  title?: string;
  [key: string]: unknown;
}
