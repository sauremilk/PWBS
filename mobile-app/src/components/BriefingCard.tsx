// BriefingCard component (TASK-152)

import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import type { Briefing } from "../types";

const TYPE_LABELS: Record<Briefing["briefing_type"], string> = {
  morning: "Morgen-Briefing",
  meeting: "Meeting-Briefing",
  project: "Projekt-Briefing",
  weekly: "Wochen-Briefing",
};

const TYPE_COLORS: Record<Briefing["briefing_type"], string> = {
  morning: "#f59e0b",
  meeting: "#3b82f6",
  project: "#10b981",
  weekly: "#8b5cf6",
};

interface Props {
  briefing: Briefing;
  onPress: () => void;
}

export function BriefingCard({ briefing, onPress }: Props) {
  const color = TYPE_COLORS[briefing.briefing_type];
  const label = TYPE_LABELS[briefing.briefing_type];
  const date = new Date(briefing.created_at).toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <TouchableOpacity style={styles.card} onPress={onPress} activeOpacity={0.7}>
      <View style={styles.header}>
        <View style={[styles.badge, { backgroundColor: color + "20" }]}>
          <Text style={[styles.badgeText, { color }]}>{label}</Text>
        </View>
        <Text style={styles.date}>{date}</Text>
      </View>
      <Text style={styles.title} numberOfLines={2}>
        {briefing.title}
      </Text>
      <Text style={styles.preview} numberOfLines={3}>
        {briefing.content.slice(0, 200)}
      </Text>
      <Text style={styles.sources}>
        {briefing.sources.length} Quelle{briefing.sources.length !== 1 ? "n" : ""}
      </Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
    marginHorizontal: 16,
    marginVertical: 6,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 2,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  badgeText: {
    fontSize: 12,
    fontWeight: "600",
  },
  date: {
    fontSize: 12,
    color: "#6b7280",
  },
  title: {
    fontSize: 16,
    fontWeight: "700",
    color: "#111827",
    marginBottom: 4,
  },
  preview: {
    fontSize: 14,
    color: "#4b5563",
    lineHeight: 20,
    marginBottom: 8,
  },
  sources: {
    fontSize: 12,
    color: "#9ca3af",
  },
});
