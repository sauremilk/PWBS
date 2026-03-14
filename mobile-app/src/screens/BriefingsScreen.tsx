// Briefings list screen (TASK-152)

import React from "react";
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from "react-native";
import { BriefingCard } from "../components/BriefingCard";
import { useBriefings } from "../hooks/useBriefings";
import type { Briefing } from "../types";

interface Props {
  onSelectBriefing: (id: string) => void;
}

export function BriefingsScreen({ onSelectBriefing }: Props) {
  const { data: briefings, isLoading, error, refetch } = useBriefings();

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#4f46e5" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.error}>Briefings konnten nicht geladen werden.</Text>
      </View>
    );
  }

  if (!briefings?.length) {
    return (
      <View style={styles.center}>
        <Text style={styles.empty}>Noch keine Briefings vorhanden.</Text>
      </View>
    );
  }

  return (
    <FlatList<Briefing>
      data={briefings}
      keyExtractor={(item) => item.id}
      renderItem={({ item }) => (
        <BriefingCard briefing={item} onPress={() => onSelectBriefing(item.id)} />
      )}
      contentContainerStyle={styles.list}
      onRefresh={refetch}
      refreshing={isLoading}
    />
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },
  error: {
    color: "#ef4444",
    fontSize: 15,
    textAlign: "center",
  },
  empty: {
    color: "#9ca3af",
    fontSize: 15,
    textAlign: "center",
  },
  list: {
    paddingVertical: 8,
  },
});
