// Briefing detail screen (TASK-152)

import React from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from "react-native";
import { useBriefing } from "../hooks/useBriefings";

interface Props {
  briefingId: string;
}

export function BriefingDetailScreen({ briefingId }: Props) {
  const { data: briefing, isLoading, error } = useBriefing(briefingId);

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#4f46e5" />
      </View>
    );
  }

  if (error || !briefing) {
    return (
      <View style={styles.center}>
        <Text style={styles.error}>Briefing nicht gefunden.</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>{briefing.title}</Text>
      <Text style={styles.meta}>
        {new Date(briefing.created_at).toLocaleDateString("de-DE", {
          weekday: "long",
          day: "2-digit",
          month: "long",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        })}
        {" \u00b7 "}
        {briefing.word_count} Woerter
      </Text>

      <Text style={styles.bodyText}>{briefing.content}</Text>

      {briefing.sources.length > 0 && (
        <View style={styles.sourcesSection}>
          <Text style={styles.sourcesTitle}>Quellen</Text>
          {briefing.sources.map((src, idx) => (
            <View key={idx} style={styles.sourceItem}>
              <Text style={styles.sourceLabel}>
                [{idx + 1}] {src.title}
              </Text>
              <Text style={styles.sourceType}>{src.source_type}</Text>
              {src.snippet ? (
                <Text style={styles.sourceSnippet} numberOfLines={2}>
                  {src.snippet}
                </Text>
              ) : null}
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#fff",
  },
  content: {
    padding: 20,
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  error: {
    color: "#ef4444",
    fontSize: 15,
  },
  title: {
    fontSize: 22,
    fontWeight: "800",
    color: "#111827",
    marginBottom: 8,
  },
  meta: {
    fontSize: 13,
    color: "#6b7280",
    marginBottom: 20,
  },
  bodyText: {
    fontSize: 16,
    color: "#1f2937",
    lineHeight: 26,
    marginBottom: 24,
  },
  sourcesSection: {
    borderTopWidth: 1,
    borderTopColor: "#e5e7eb",
    paddingTop: 16,
  },
  sourcesTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#111827",
    marginBottom: 12,
  },
  sourceItem: {
    marginBottom: 12,
    paddingLeft: 12,
    borderLeftWidth: 2,
    borderLeftColor: "#4f46e5",
  },
  sourceLabel: {
    fontSize: 14,
    fontWeight: "600",
    color: "#1f2937",
  },
  sourceType: {
    fontSize: 12,
    color: "#9ca3af",
    marginTop: 2,
  },
  sourceSnippet: {
    fontSize: 13,
    color: "#6b7280",
    marginTop: 4,
    fontStyle: "italic",
  },
});
